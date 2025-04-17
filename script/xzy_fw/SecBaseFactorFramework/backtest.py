import matplotlib.pyplot as plt
import torch

from .global_config import DateConfig2D, DateConfig2DMatch
from .base_data_config import Base_data_dict
# from . import torch_operators as op
from .fac_exp_exec import exec_fac_exp
from .util_function import *
import pandas as pd
import numpy as np
import os
from tqdm import tqdm
import time


# 从base_data形状的数据中截取需要的因子
def get_output_data_from_base_data(base_data, idx):
    assert len(idx) > 0
    res = base_data[idx]
    return res


def adjust_fac_invalid_value(fac_data):
    fac_data[~torch.isfinite(fac_data)] = torch.nan
    return fac_data


def save_mmap_data():
    raise NotImplementedError


class BtSupport:
    trade_time_loc_dict = GlobalConfig.trade_time_loc_dict
    trade_date_loc_dict = GlobalConfig.trade_date_loc_dict
    trade_code_loc_dict = GlobalConfig.trade_code_loc_dict
    trade_date_list = GlobalConfig.trade_date_list
    trade_code_list = GlobalConfig.trade_code_list
    backtest_group_num = GlobalConfig.backtest_group_num
    backtest_head_num_list = GlobalConfig.backtest_head_num_list
    backtest_tail_num_list = GlobalConfig.backtest_tail_num_list
    # start_date = GlobalConfig.backtest_start_date
    # end_date = GlobalConfig.backtest_end_date
    eval_start_date = None
    eval_end_date = None


# 评价因子：计算ic 分组收益 头部收益
def eval_fac(fac_data, fac_name, label_config, date_config_match,
             backtest_group_num, backtest_head_num_list, backtest_tail_num_list):
    # print('align label valid_mask')
    # print('date_config_match.trade_date_list', date_config_match.base_data_date_config.trade_date_list)
    # print('date_config_match.calc_date_list', date_config_match.base_data_date_config.calc_date_list)
    # print('date_config_match.time_step_1d', date_config_match.base_data_date_config.time_step_1d)

    # 旧：限制time_step_each_loop_try_list
    # time_step_1d = date_config_match.base_data_date_config.time_step_1d
    # time_step_each_loop_try_list = [x for x in GlobalConfig.time_step_each_loop_try_list if x < time_step_1d]
    # if len(time_step_each_loop_try_list) == 0:
    #     time_step_each_loop_try_list = [time_step_1d]
    # start_time = time.time()

    ori_calc_mode = date_config_match.output_data_date_config.calc_mode
    date_config_match.calc_mode = 'cont'
    date_config_match.base_data_date_config.calc_mode = 'cont'
    date_config_match.output_data_date_config.calc_mode = 'cont'
    time_step_each_loop_try_list = GlobalConfig.time_step_each_loop_try_list

    # 将label和calc_date_list对齐
    valid_mask_name_all = label_config.valid_mask_name
    label_name_all = label_config.label_name
    valid_mask_currennt = exec_fac_exp(rf'{valid_mask_name_all}',
                                       date_config_match,
                                       0,
                                       time_step_each_loop_try_list)

    # valid_mask需要转换类型
    valid_mask_currennt = valid_mask_currennt.to(torch.bool)
    valid_mask_name = rf'{valid_mask_name_all}_current'
    Base_data_dict[valid_mask_name] = valid_mask_currennt

    label_currennt = exec_fac_exp(rf'{label_name_all}',
                                  date_config_match,
                                  0,
                                  time_step_each_loop_try_list)
    label_name = rf'{label_name_all}_current'
    Base_data_dict[label_name] = label_currennt
    # print('valid_mask_currennt.shape', valid_mask_currennt.shape)
    # print('label_currennt.shape', label_currennt.shape)
    # print('convert label & valid_mask', time.time() - start_time)

    # 对齐过后强制令trade_date_list = calc_date_list
    date_config_match.trade_date_list = date_config_match.calc_date_list
    date_config_match.base_data_date_config.trade_date_list = date_config_match.calc_date_list
    date_config_match.output_data_date_config.trade_date_list = date_config_match.calc_date_list

    assert fac_name not in Base_data_dict
    Base_data_dict[fac_name] = fac_data
    # print('fac_data count ', torch.isfinite(fac_data).sum(1))

    # 截面空值填均值
    fac_fillna = exec_fac_exp(rf'cs_fillna_mean({fac_name}, {valid_mask_name})',
                              date_config_match,
                              0,
                              time_step_each_loop_try_list)
    Base_data_dict[fac_name] = fac_fillna
    # print('fac_fillna count ', torch.isfinite(fac_fillna).sum(1))
    # print('fac_fillna', time.time() - start_time)

    # ic
    date_config_match.output_data_date_config.reset_output_shape(code_num=0)
    # print('date_config_match.output_data_date_config.output_shape',
    #       date_config_match.output_data_date_config.output_shape)

    ic = exec_fac_exp(rf'cs_corr({fac_name}, {label_name})',
                      date_config_match,
                      0,
                      time_step_each_loop_try_list)
    # print('ic', time.time() - start_time)

    # rank_ic
    date_config_match.output_data_date_config.reset_output_shape(code_num=0)
    rank_ic = exec_fac_exp(
        rf'fac_rank=cs_rank({fac_name}, {valid_mask_name}); label_rank=cs_rank({label_name}, {valid_mask_name}); cs_corr(fac_rank, label_rank)',
        date_config_match,
        0,
        time_step_each_loop_try_list)
    # print('rank_ic', time.time() - start_time)

    # 分组收益
    temp_dict = GlobalConfig.temp_data_dict
    temp_dict['backtest_group_num'] = backtest_group_num
    temp_dict['backtest_head_num_list'] = backtest_head_num_list
    temp_dict['backtest_tail_num_list'] = backtest_tail_num_list
    if backtest_group_num is None:
        ret_group = None
    else:
        date_config_match.output_data_date_config.reset_output_shape(code_num=backtest_group_num)
        ret_group = exec_fac_exp(rf'cs_group_mean({fac_name}, {label_name}, {valid_mask_name}, backtest_group_num)',
                                 date_config_match,
                                 0,
                                 time_step_each_loop_try_list)
    if backtest_head_num_list is None and backtest_tail_num_list is None:
        ret_head = None
    else:
        date_config_match.output_data_date_config.reset_output_shape(
            code_num=len(backtest_head_num_list) + len(backtest_tail_num_list))
        ret_head = exec_fac_exp(
            rf'cs_head_mean({fac_name}, {label_name}, {valid_mask_name}, backtest_head_num_list, backtest_tail_num_list)',
            date_config_match,
            0,
            time_step_each_loop_try_list)
    del temp_dict['backtest_group_num']
    del temp_dict['backtest_head_num_list']
    del temp_dict['backtest_tail_num_list']
    # print('ret_group', time.time() - start_time)

    # nan值占比
    date_config_match.output_data_date_config.reset_output_shape(code_num=0)
    nan_proportion = exec_fac_exp(rf'cs_nan_proportion({fac_name}, {valid_mask_name})',
                                  date_config_match,
                                  0,
                                  time_step_each_loop_try_list)

    # 0值占比
    date_config_match.output_data_date_config.reset_output_shape(code_num=0)
    zero_proportion = exec_fac_exp(rf'cs_certain_value_proportion({fac_name}, {valid_mask_name}, 0)',
                                   date_config_match,
                                   0,
                                   time_step_each_loop_try_list)
    # print('nan_proportion&zero_proportion', time.time() - start_time)

    del Base_data_dict[fac_name]
    res_dict = dict()
    res_dict['ic'] = ic
    res_dict['rank_ic'] = rank_ic
    res_dict['ret_group'] = ret_group
    res_dict['ret_head'] = ret_head
    res_dict['nan_proportion'] = nan_proportion
    res_dict['zero_proportion'] = zero_proportion

    date_config_match.calc_mode = ori_calc_mode
    date_config_match.base_data_date_config.calc_mode = ori_calc_mode
    date_config_match.output_data_date_config.calc_mode = ori_calc_mode

    return res_dict


def get_dataframe_from_output(data, trade_date_list, trade_code_list):
    res = pd.DataFrame(data, index=trade_date_list, columns=trade_code_list)
    return res


def merge_backtest_result_all_period(res, period_num, trade_date_list, backtest_group_num,
                                     backtest_head_num_list, backtest_tail_num_list):
    res_data = dict()
    for period_idx in range(period_num):
        period_name = rf'period{period_idx + 1}'

        ic_period = res['ic'][period_idx::period_num]
        ic_period = get_dataframe_from_output(ic_period.unsqueeze(1), trade_date_list,
                                              ['ic'])
        rank_ic_period = res['rank_ic'][period_idx::period_num]
        rank_ic_period = get_dataframe_from_output(rank_ic_period.unsqueeze(1), trade_date_list,
                                                   ['rank_ic'])

        rank_ic_period_mean = rank_ic_period['rank_ic'].mean()
        # sign_ic = int(np.sign(rank_ic_period_mean))
        sign_ic = 1

        ret_group_cols = [rf'group{x}' for x in range(1, backtest_group_num + 1)]
        ret_group_cols_use = ret_group_cols[::sign_ic]
        ret_group_period = res['ret_group'][period_idx::period_num]
        ret_group_period = get_dataframe_from_output(ret_group_period, trade_date_list,
                                                     ret_group_cols_use)
        ret_group_period = ret_group_period.reindex(columns=ret_group_cols)

        ret_head_cols = [rf'tail{x}' for x in backtest_tail_num_list] + [rf'head{x}' for x in backtest_head_num_list]
        if sign_ic > 0:
            ret_head_cols_use = ret_head_cols
        else:
            ret_head_cols_use = [rf'head{x}' for x in backtest_head_num_list] + [rf'tail{x}' for x in
                                                                                 backtest_tail_num_list]

        ret_head_period = res['ret_head'][period_idx::period_num]
        ret_head_period = get_dataframe_from_output(ret_head_period, trade_date_list,
                                                    ret_head_cols_use)
        ret_head_period = ret_head_period.reindex(columns=ret_head_cols)

        nan_proportion_period = res['nan_proportion'][period_idx::period_num]
        nan_proportion_period = get_dataframe_from_output(nan_proportion_period.unsqueeze(1), trade_date_list,
                                                          ['nan_proportion'])

        zero_proportion_period = res['zero_proportion'][period_idx::period_num]
        zero_proportion_period = get_dataframe_from_output(zero_proportion_period.unsqueeze(1), trade_date_list,
                                                           ['zero_proportion'])

        res_data_period = pd.concat(
            [ic_period, rank_ic_period, ret_group_period, ret_head_period, nan_proportion_period,
             zero_proportion_period],
            axis=1)
        res_data_period['period_name'] = period_name
        res_data[period_name] = res_data_period

    res_data = pd.concat(res_data.values())
    res_data['date'] = res_data.index
    res_data = res_data.reset_index(drop=True)
    return res_data


def format_backtest_result_all_period(res_data, cols=None):
    eval_start_date = BtSupport.eval_start_date
    eval_end_date = BtSupport.eval_end_date
    if eval_start_date is not None and eval_end_date is not None:
        res_data_eval = res_data.loc[res_data['date'].between(eval_start_date, eval_end_date)]
    else:
        res_data_eval = res_data
    res_data_eval_mean = res_data_eval.groupby(['period_name'], as_index=False).mean()
    if cols is None:
        # cols = ['period_name', 'ic', 'rank_ic', 'group1', 'group20', 'tail50',
        #         'tail100', 'tail200', 'head50', 'head100', 'head200', 'nan_proportion',
        #         'zero_proportion']
        cols = [x for x in res_data_eval_mean if 'date' not in x]
    res_data_eval_mean = res_data_eval_mean.loc[:, cols]
    cond = res_data_eval_mean.columns.str.contains('group|tail|head')

    res_data_eval_mean.loc[:, cond] *= 365 * 24
    all_period_mean = res_data_eval_mean.mean()
    all_period_mean['period_name'] = 'all_period_mean'
    res_data_eval_mean = res_data_eval_mean.append(all_period_mean, ignore_index=True)

    ret_ser = res_data_eval.loc[:, ['date'] + cols].groupby(['date']).mean() * 24
    cond = ret_ser.columns.str.contains('group|tail|head')
    ret_ser = ret_ser.loc[:, cond]

    return res_data_eval_mean, ret_ser


def backtest_m1(fac_data_output, fac_name, save_path, label_config, date_config_match):
    valid_mask_name = label_config.valid_mask_name
    period_num = label_config.output_config.output_data_time_step_1d
    label_name = label_config.label_name

    res = eval_fac(fac_data_output, fac_name, label_config, date_config_match,
                   BtSupport.backtest_group_num, BtSupport.backtest_head_num_list, BtSupport.backtest_tail_num_list)

    res_data = merge_backtest_result_all_period(res, period_num,
                                                date_config_match.calc_date_list,
                                                BtSupport.backtest_group_num,
                                                BtSupport.backtest_head_num_list,
                                                BtSupport.backtest_tail_num_list)
    res_data_eval_mean, ret_ser = format_backtest_result_all_period(res_data)
    dump_pickle(rf'{save_path}/res_{valid_mask_name}_{label_name}.pkl', res)
    dump_pickle(rf'{save_path}/res_data_{valid_mask_name}_{label_name}.pkl', res_data)
    dump_pickle(rf'{save_path}/res_data_eval_mean_{valid_mask_name}_{label_name}.pkl',
                res_data_eval_mean)
    dump_pickle(rf'{save_path}/ret_ser_{valid_mask_name}_{label_name}.pkl', ret_ser)


# 计算因子并回测 全历史计算 不考虑已有结果
def fac_backtest(fac_exp, fac_name, output_config_dict, label_config_dict,
                 calc_start=None, calc_end=None,
                 calc_date_list=None,
                 calc_mode=None,
                 intraday_data_only=None,
                 eval_start=None, eval_end=None,
                 check_fac_name_duplicate=False, do_backtest=True, save_fac_data=False,
                 just_return_fac_data=False):
    # if (not calc_start) and (not calc_end) and calc_date_list:
    #     calc_mode = 'daily'
    # elif calc_start and calc_end and (not calc_date_list):
    #     calc_mode = 'cont'
    # else:
    #     raise NotImplementedError
    BtSupport.eval_start_date = eval_start
    BtSupport.eval_end_date = eval_end

    assert calc_mode in ['daily', 'cont']

    trade_date_list = GlobalConfig.trade_date_list
    base_data_time_step_1d = GlobalConfig.base_data_time_step_1d
    base_date_config = DateConfig2D(base_data_time_step_1d, trade_date_list, calc_date_list,
                                    calc_start, calc_end, calc_mode, intraday_data_only=intraday_data_only)

    # fac_data的输入和输出都与base_data相同
    base_date_match = DateConfig2DMatch(base_date_config, base_date_config)
    fac_data = exec_fac_exp(fac_exp,
                            base_date_match,
                            GlobalConfig.time_step_left_for_nan,
                            GlobalConfig.time_step_each_loop_try_list)
    # print('fac_data.shape', fac_data.shape)
    if just_return_fac_data:
        return fac_data

    # 因子输出结果
    fac_data_output_dict = dict()
    # for output_name, output_config in tqdm(output_config_dict.items(), desc='calc_output'):
    for output_name, output_config in output_config_dict.items():
        output_data_time_step_1d = output_config.output_data_time_step_1d
        # 强制令trade_date_list=计算用的calc_date_list
        output_date_config = DateConfig2D(output_data_time_step_1d, base_date_config.calc_date_list, calc_date_list,
                                          calc_start, calc_end, calc_mode, intraday_data_only=intraday_data_only)
        output_data_time_loc_in_base_data = output_date_config.get_output_data_time_loc_in_base_data(
            base_data_time_step_1d, output_config.output_data_time_loc_list)
        fac_data_output = get_output_data_from_base_data(fac_data, output_data_time_loc_in_base_data)
        fac_data_output = adjust_fac_invalid_value(fac_data_output)
        assert fac_data_output.shape == output_date_config.output_shape, (
            fac_data_output, output_date_config.output_shape)
        # print('fac_data_output.shape', fac_data_output.shape)
        fac_data_output_dict[output_name] = fac_data_output

        # 因子保存路径
        assert '_' in fac_name, rf'invalid fac_name (no "_") : {fac_name}'
        factor_output_path = output_config.factor_output_path
        fac_name_ser = fac_name.split('_')[0]
        factor_save_path = rf'{factor_output_path}/{fac_name_ser}/{fac_name}'

        # 是否要保存因子信息
        save = 'y'
        if check_fac_name_duplicate:
            if not os.path.exists(factor_save_path):
                os.makedirs(factor_save_path)
            else:
                if len(os.listdir(factor_save_path)) > 0:
                    if fac_name == 'dev_fac':
                        pass
                    else:
                        save = input(rf'{fac_name} already exists, replace the old one? [y/n]')
        else:
            if not os.path.exists(factor_save_path):
                os.makedirs(factor_save_path)

        # 保存因子信息
        if 'y' in save:
            # 保存因子表达式信息
            fac_info = {'fac_exp': fac_exp,
                        'output_date_config': output_date_config}
            dump_pickle(rf'{factor_save_path}/fac_info.pkl', fac_info)
            # 保存因子值
            if save_fac_data:
                fac_data_save = np.memmap(rf'{factor_save_path}/fac_data.Mmap', dtype='float32', mode='w+',
                                          shape=output_date_config.output_shape)
                fac_data_save[:] = fac_data_output
                fac_data_save.flush()

    if do_backtest:
        # for label_name, label_config in tqdm(label_config_dict.items(), desc = 'backtest'):
        for label_name, label_config in label_config_dict.items():
            output_name = label_config.output_config.factor_output_name
            fac_data_output = fac_data_output_dict[output_name]
            label_output_path = label_config.label_output_path
            fac_name_ser = fac_name.split('_')[0]
            result_save_path = rf'{label_output_path}/{fac_name_ser}/{fac_name}'

            # 回测的输入和输出都与label的output_data信息相同
            label_data_time_step_1d = label_config.output_config.output_data_time_step_1d
            label_date_config = DateConfig2D(label_data_time_step_1d, trade_date_list, calc_date_list,
                                             calc_start, calc_end, calc_mode, intraday_data_only=intraday_data_only)

            label_date_match = DateConfig2DMatch(label_date_config, label_date_config)
            backtest_m1(fac_data_output, fac_name, result_save_path, label_config, label_date_match)


def unit_test():
    raise NotImplementedError
