from . import base_data_config
from . import fac_exp_exec
from . import global_config
from . import backtest
from . import util_function
import os

# os.environ['CUDA_VISIBLE_DEVICES'] = '3'
output_config_dict = global_config.output_config_dict
label_config_dict = global_config.label_config_dict


# 新增：对backtest的函数进一步封装，写死日期
def fac_backtest(fac_exp, fac_name, calc_mode, intraday_data_only, check_fac_name_duplicate, save_fac_data):
    # backtest.fac_backtest(fac_exp=fac_exp,
    #                       fac_name=fac_name, output_config_dict=output_config_dict, label_config_dict=label_config_dict,
    #                       calc_start='20210104', calc_end='20221230', calc_date_list=None,
    #                       calc_mode=calc_mode, intraday_data_only=intraday_data_only,
    #                       eval_start='20210104', eval_end='20221230',
    #                       check_fac_name_duplicate=check_fac_name_duplicate, do_backtest=True,
    #                       save_fac_data=save_fac_data)
    backtest.fac_backtest(fac_exp=fac_exp,
                          fac_name=fac_name, output_config_dict=output_config_dict, label_config_dict=label_config_dict,
                          calc_start='20210104', calc_end='20221230', calc_date_list=None,
                          calc_mode=calc_mode, intraday_data_only=intraday_data_only,
                          eval_start='20210104', eval_end='20221230',
                          check_fac_name_duplicate=check_fac_name_duplicate, do_backtest=True,
                          save_fac_data=save_fac_data)


def get_all_backtest_result(fac_name, label_name_list=None, print_tabel=True, print_figure=True):
    for label_name, label_config in label_config_dict.items():
        if label_name_list is not None:
            if label_name not in label_name_list:
                continue
        util_function.get_fac_backtest_result(fac_name, label_config, print_tabel=print_tabel,
                                              print_figure=print_figure)


def set_gpu_device(device):
    global_config.GlobalConfig.use_device = device