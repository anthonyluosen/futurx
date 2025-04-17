import pandas as pd
import numpy as np
import os
import pickle
# from copy import deepcopy
# from datetime import datetime, timedelta
# from joblib import Parallel, delayed
# import random
# import torch
# from tqdm import *
import warnings
import matplotlib.pyplot as plt
from .global_config import GlobalConfig, output_config_dict, label_config_dict


warnings.filterwarnings("ignore")


# print('load util function')

def load_pickle(path):
    with open(path, 'rb') as f:
        return pickle.load(f)


def dump_pickle(path, data):
    directory = os.path.dirname(path)
    if not os.path.exists(directory):
        os.makedirs(directory)
    with open(path, 'wb') as f:
        pickle.dump(data, f)


def format_xticks(raw_xticks, target_num):
    locs = np.linspace(0, len(raw_xticks) - 1, target_num + 1)
    locs = [int(loc) for loc in locs]
    xs = [raw_xticks[loc] for loc in locs]
    return locs, xs


def plot_return_data(return_data, title=None, fig_sava_path=None):
    plot_df = pd.DataFrame()
    for col, ser in return_data.iteritems():
        net_value = ser.cumsum()
        annual_ret = ser.mean() * 365 * 100
        annual_vol = ser.std() * np.sqrt(365) * 100
        drawdown = net_value.cummax() - net_value
        max_drawdown = drawdown.max() * 100
        sharpe = annual_ret / annual_vol

        col_ = "%s, %.2f%%, %.2f%%, %.2f" % (col, annual_ret, max_drawdown, sharpe)
        plot_df[col_] = net_value

    plot_df_last = plot_df.iloc[-1, :]
    plot_df_pos = plot_df_last.loc[plot_df_last > 0]
    plot_df_neg = plot_df_last.loc[plot_df_last < 0]
    if len(plot_df_pos) > 0 and len(plot_df_neg) > 0:
        pos_abs_max = plot_df_pos.abs().max()
        neg_abs_max = plot_df_neg.abs().max()
        ratio = pos_abs_max / neg_abs_max
        if ratio < 0.8:
            plot_df[plot_df_neg.index] *= ratio

    figsize = (12, 6)
    fontsize = 10
    locs, xs = format_xticks(plot_df.index, 20)

    plot_df.plot(figsize=figsize)
    plt.legend(loc="upper left", bbox_to_anchor=(1.02, 1), borderaxespad=0.)
    plt.xlabel("Date", fontsize=fontsize)
    plt.ylabel("Net Value", fontsize=fontsize)
    plt.xticks(locs, xs, rotation=45)
    plt.title(title, fontsize=fontsize)

    if fig_sava_path is not None:
        if os.path.exists(fig_sava_path):
            os.remove(fig_sava_path)

        plt.savefig(fig_sava_path)
    plt.show()
    plt.close()


def get_fac_backtest_result(fac_name, label_config, print_tabel=True, print_figure=True, print_start_date=None,
                            print_end_date=None):
    pd.set_option('display.width', None)
    pd.set_option('display.max_rows', None)
    pd.set_option('display.max_columns', None)
    pd.set_option('display.max_colwidth', -1)
    pd.set_option('display.expand_frame_repr', False)
    label_name = label_config.label_name
    valid_mask_name = label_config.valid_mask_name

    label_output_path = label_config.label_output_path
    fac_name_ser = fac_name.split('_')[0]
    result_save_path = rf'{label_output_path}/{fac_name_ser}/{fac_name}'

    res_data_eval_mean = load_pickle(rf'{result_save_path}/res_data_eval_mean_{valid_mask_name}_{label_name}.pkl')
    ret_ser = load_pickle(rf'{result_save_path}/ret_ser_{valid_mask_name}_{label_name}.pkl')
    res_data_eval_mean_format = res_data_eval_mean.copy()
    res_data_eval_mean_format.iloc[:, 1:] = (res_data_eval_mean_format.iloc[:, 1:] * 100).round(1)
    if print_tabel or print_figure:
        print(rf'fac_name: {fac_name}')
        print(rf'label_name: {label_name}')
    if print_tabel:
        # cols = ['period_name', 'ic', 'rank_ic', 'group1', 'group20', 'tail50',
        #         'tail100', 'head50', 'head100', 'nan_proportion',
        #         'zero_proportion']
        # # print(res_data_eval_mean_format[[x for x in res_data_eval_mean_format.columns if '200' not in x]])
        # print(res_data_eval_mean_format[cols])
        print(res_data_eval_mean_format)
    if print_figure:
        if print_start_date is None and print_end_date is None:
            plot_return_data(ret_ser[[x for x in ret_ser.columns if 'group' in x]], title=rf'{fac_name} | {label_name}')
        else:
            print('\n please note: print_start_date and print_end_date are only valid for figure but not tabel now')
            plot_return_data(ret_ser.loc[print_start_date:print_end_date, [x for x in ret_ser.columns if 'group' in x]],
                             title=fac_name)


def get_fac_backtest_data(fac_name, label_config):
    label_name = label_config.label_name
    valid_mask_name = label_config.valid_mask_name

    factor_output_path = label_config.output_config.factor_output_path
    fac_name_ser = fac_name.split('_')[0]
    factor_save_path = rf'{factor_output_path}/{fac_name_ser}/{fac_name}'

    fac_info = load_pickle(rf'{factor_save_path}/fac_info.pkl')
    output_date_config = fac_info['output_date_config']
    fac_data = np.memmap(rf'{factor_save_path}/fac_data.Mmap', dtype='float32', mode='r',
                         shape=output_date_config.output_shape)

    label_output_path = label_config.label_output_path
    fac_name_ser = fac_name.split('_')[0]
    result_save_path = rf'{label_output_path}/{fac_name_ser}/{fac_name}'

    res = load_pickle(rf'{result_save_path}/res_{valid_mask_name}_{label_name}.pkl')
    res_data = load_pickle(rf'{result_save_path}/res_data_{valid_mask_name}_{label_name}.pkl')
    res_data_eval_mean = load_pickle(rf'{result_save_path}/res_data_eval_mean_{valid_mask_name}_{label_name}.pkl')
    ret_ser = load_pickle(rf'{result_save_path}/ret_ser_{valid_mask_name}_{label_name}.pkl')
    res_data_eval_mean_format = res_data_eval_mean.copy()
    res_data_eval_mean_format.iloc[:, 1:] = (res_data_eval_mean_format.iloc[:, 1:] * 100).round(1)

    return fac_data, output_date_config, res, res_data, res_data_eval_mean, ret_ser, res_data_eval_mean_format


def get_factor_names():
    return [x.split('.')[0] for x in os.listdir(rf'{GlobalConfig.base_data_root_path}/Base')]

