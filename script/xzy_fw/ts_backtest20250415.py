import torch
import matplotlib.pyplot as plt
from torch.utils.data import Dataset, DataLoader
import SecBaseFactorFramework as ff
from SecBaseFactorFramework.util_function import *
from SecBaseFactorFramework.global_config import label_config_dict, output_config_dict, valid_mask_config_dict, \
    label_data_path, tsbt_support_path
from polars_func import *

trade_date_list = ff.global_config.GlobalConfig.trade_date_list
trade_code_list = ff.global_config.GlobalConfig.trade_code_list
valid_date_slice = slice(None)
valid_trade_date_list = trade_date_list[valid_date_slice]

ff.global_config.GlobalConfig.use_device = 'cuda:0'
calc_start = '2023-01-01'
calc_end = '2025-03-20'
eval_start = calc_start
eval_end = calc_end
date_num, code_num, base_data_time_step_1d = GlobalConfig.date_num, GlobalConfig.code_num, GlobalConfig.base_data_time_step_1d

label_1h = torch.load(rf'{label_data_path}/label_1h.pt')
valid_mask_daily_ls1 = load_pickle(rf'{tsbt_support_path}/valid_mask_daily_ls1.pkl')


def fea_preproc(fac_data, d):
    # 回看时间
    # d = 1400 * 5
    # 信号转pl
    fea = replace_nan_pl(pl.DataFrame(fac_data))
    # 去极值
    fea_dext = ts_dext_fea_pl(fea, d, 0.01)
    # zscore仓位
    fea_zscore = ts_zscore_fea_pl(fea_dext, d, d // 3)
    # 分位数0-1仓位
    # fea_qsig = ts_qsig_fea_pl(fea_dext, d, 0.95, 0.05)
    # 测zscore仓位
    posi_pl = fillna_pl(replace_nan_pl(fea_zscore), 0)
    return posi_pl


def fea_justfillna(fac_data):
    fea = replace_nan_pl(pl.DataFrame(fac_data))
    posi_pl = fillna_pl(fea, 0)
    return posi_pl


# 回测函数
# 输入fac_exp则根据表达式计算然后回测，输入score则直接用打分回测
def ts_backtest(fac_exp=None, score=None, preproc=True, d=None, device=None):
    ff.global_config.GlobalConfig.use_device = device
    assert fac_exp is None or score is None
    if fac_exp is not None:
        fac_data = ff.backtest.fac_backtest(fac_exp,
                                            fac_name='dev_fac', output_config_dict=output_config_dict,
                                            label_config_dict=label_config_dict,
                                            calc_start=calc_start, calc_end=calc_end, calc_date_list=None,
                                            calc_mode='cont', intraday_data_only=False,
                                            eval_start=eval_start, eval_end=eval_end,
                                            check_fac_name_duplicate=False, do_backtest=True, save_fac_data=False,
                                            just_return_fac_data=True)

    elif score is not None:
        fac_data = score.clone()
    else:
        raise NotImplementedError

    # 因子预处理后直接做仓位posi_pl
    if preproc:
        posi_pl = fea_preproc(fac_data.numpy(), d)
    else:
        posi_pl = fea_justfillna(fac_data.numpy())

    # 标签转pl
    ret_pl = replace_nan_pl(pl.DataFrame(label_1h.numpy()))

    # 标签是以下一分钟的vwap为交易价格，未来60分钟的收益
    # posi_pl和ret_pl都是二维矩阵，0轴是时间，从第一天的第一分钟到最后一天的最后一分钟连续排列。1轴是标的
    # 以下为回测

    # 分钟频收益，每单位绝对值持仓收益，多空比
    ret_mean, ret_std, sharpe = ts_ret_stat_pl(posi_pl, ret_pl, return_pandas=True)
    ret_mean_pabs = ts_ret_pabs_pl(posi_pl, ret_pl, return_pandas=True)
    long_ratio, short_ratio = ts_posi_ls_ratio_pl(posi_pl, return_pandas=True)

    # 统计量
    ic = ts_corr_pl(posi_pl, ret_pl).to_pandas()
    ric = ts_rankcorr_pl(posi_pl, ret_pl).to_pandas()
    sign = np.sign(ret_mean.mean(1))

    cost = 1.8 / 10000
    # 无手续费的曲线
    pnl_itvl_daily, ret_yearly, sharpe_yearly, ret_1trd = get_pnl_itvl_daily(posi_pl, ret_pl, 60, 1440, sign, 0,
                                                                             trade_date_list, valid_trade_date_list,
                                                                             trade_code_list, valid_mask_daily_ls1, 365)
    # 计算手续费的曲线
    pnl_itvl_daily_wc, ret_yearly_wc, sharpe_yearly_wc, ret_1trd_wc = get_pnl_itvl_daily(posi_pl, ret_pl, 60, 1440,
                                                                                         sign, cost,
                                                                                         trade_date_list,
                                                                                         valid_trade_date_list,
                                                                                         trade_code_list,
                                                                                         valid_mask_daily_ls1, 365)
    return fac_data, pnl_itvl_daily_wc
