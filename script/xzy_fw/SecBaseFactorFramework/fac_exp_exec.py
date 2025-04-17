import numpy as np
import os
import warnings
import math
import torch
from typing import List
from .base_data_config import Base_data_dict
from .global_config import GlobalConfig, DateConfig2DMatch
from .torch_operators import *
import gc
import sys
import traceback

os.environ['KMP_DUPLICATE_LIB_OK'] = 'True'
warnings.filterwarnings("ignore")


def get_base_data_name_used_in_fac_exp(fac_exp: str):
    name_list = [name for name in Base_data_dict if name in fac_exp]
    return name_list


# # 解析并执行因子表达式
# # 由于显存限制，每次只计算一定量的时间步
# def exec_fac_exp(fac_exp: str,
#                  date_config_match: DateConfig2DMatch,
#                  time_step_left_for_nan: int = None,
#                  time_step_each_loop_try_list: List[int] = None,
#                  ):
#     use_device = GlobalConfig.use_device
#     if time_step_left_for_nan is None:
#         raise NotImplementedError
#     if time_step_each_loop_try_list is None:
#         time_step_each_loop_try_list = GlobalConfig.time_step_each_loop_try_list
#     intraday_data_only = date_config_match.base_data_date_config.intraday_data_only
#     assert intraday_data_only is not None
#
#     try:
#         base_config = date_config_match.base_data_date_config
#         output_config = date_config_match.output_data_date_config
#         target_data_shape = output_config.output_shape
#         fac_res = torch.full(size=target_data_shape, fill_value=torch.nan, device='cpu')
#
#         base_data_name_list = get_base_data_name_used_in_fac_exp(fac_exp)
#         local_var_dict = locals()
#         for temp_data_name, temp_data in GlobalConfig.temp_data_dict.items():
#             local_var_dict[temp_data_name] = temp_data
#
#         for time_step_each_loop in time_step_each_loop_try_list:
#             try:
#                 base_data_slice_list, output_data_slice_list = date_config_match.get_calc_slice(
#                     time_step_each_loop=time_step_each_loop,
#                     time_step_left_for_nan=time_step_left_for_nan)
#
#                 for base_data_slice, result_data_slice in zip(base_data_slice_list, output_data_slice_list):
#
#                     # 如果有非法切片 跳过
#                     if base_data_slice.start < 0:
#                         continue
#
#                     for base_data_name in base_data_name_list:
#                         try:
#                             local_var_dict[rf"{base_data_name}"] = torch.from_numpy(
#                                 Base_data_dict[base_data_name][base_data_slice]).to(
#                                 device=use_device)
#                         except:
#                             local_var_dict[rf"{base_data_name}"] = Base_data_dict[base_data_name][base_data_slice].to(
#                                 device=use_device)
#                         if intraday_data_only == True:
#                             local_var_dict[rf"{base_data_name}"][:time_step_left_for_nan] = torch.nan
#                     valid_step = result_data_slice.stop - result_data_slice.start
#
#                     if ';' in fac_exp:
#                         exp_list = fac_exp.split(';')
#                         for exp in exp_list[:-1]:
#                             exec(exp.strip())
#                         exec(rf'temp = ' + exp_list[-1].strip())
#                     else:
#                         exec(rf'temp = ' + fac_exp.strip())
#                     exec(rf'fac_res[result_data_slice] = temp[-valid_step:]')
#                 gc.collect()
#                 torch.cuda.empty_cache()
#                 return fac_res
#
#             except Exception as e:
#                 if time_step_each_loop == time_step_each_loop_try_list[-1]:
#                     print("An error occurred:", e)
#                     traceback_info = traceback.extract_tb(sys.exc_info()[2])
#                     filename, line_number, function_name, text = traceback_info[-1]
#                     print("Exception occurred in file:", filename)
#                     print("On line number:", line_number)
#                     print("In function:", function_name)
#                     print("Exception line:", text)
#                     del traceback_info
#                     gc.collect()
#                     torch.cuda.empty_cache()
#
#     except Exception as e:
#         print("An error occurred:", e)
#         traceback_info = traceback.extract_tb(sys.exc_info()[2])
#         filename, line_number, function_name, text = traceback_info[-1]
#         print("Exception occurred in file:", filename)
#         print("On line number:", line_number)
#         print("In function:", function_name)
#         print("Exception line:", text)
#         del traceback_info
#         gc.collect()
#         torch.cuda.empty_cache()
#         return

# # 解析并执行因子表达式
# # 由于显存限制，每次只计算一定量的时间步
def exec_fac_exp(fac_exp: str,
                 date_config_match: DateConfig2DMatch,
                 time_step_left_for_nan: int = None,
                 time_step_each_loop_try_list: List[int] = None,
                 ):
    use_device = GlobalConfig.use_device
    if time_step_left_for_nan is None:
        raise NotImplementedError
    if time_step_each_loop_try_list is None:
        time_step_each_loop_try_list = GlobalConfig.time_step_each_loop_try_list
    intraday_data_only = date_config_match.base_data_date_config.intraday_data_only
    assert intraday_data_only is not None

    try:
        base_config = date_config_match.base_data_date_config
        output_config = date_config_match.output_data_date_config
        target_data_shape = output_config.output_shape
        fac_res = torch.full(size=target_data_shape, fill_value=torch.nan, device='cpu')
        # print('fac_exp_exec')
        # print('target_data_shape', target_data_shape)
        # print('GlobalConfig.code_num', GlobalConfig.code_num)

        base_data_name_list = get_base_data_name_used_in_fac_exp(fac_exp)
        local_var_dict = locals()
        for temp_data_name, temp_data in GlobalConfig.temp_data_dict.items():
            local_var_dict[temp_data_name] = temp_data

        for time_step_each_loop in time_step_each_loop_try_list:
            try:
                base_data_slice_list, output_data_slice_list = date_config_match.get_calc_slice(
                    time_step_each_loop=time_step_each_loop,
                    time_step_left_for_nan=time_step_left_for_nan)

                for base_data_slice, result_data_slice in zip(base_data_slice_list, output_data_slice_list):

                    # 如果有非法切片 跳过
                    if base_data_slice.start < 0:
                        continue

                    for base_data_name in base_data_name_list:

                        if GlobalConfig.sel_code_list is None:
                            try:
                                local_var_dict[rf"{base_data_name}"] = torch.from_numpy(
                                    Base_data_dict[base_data_name][base_data_slice]).to(
                                    device=use_device)
                            except:
                                local_var_dict[rf"{base_data_name}"] = Base_data_dict[base_data_name][
                                    base_data_slice].to(
                                    device=use_device)

                        else:
                            try:
                                local_var_dict[rf"{base_data_name}"] = torch.from_numpy(
                                    Base_data_dict[base_data_name][base_data_slice, GlobalConfig.sel_code_list]).to(
                                    device=use_device)
                            except:
                                local_var_dict[rf"{base_data_name}"] = Base_data_dict[base_data_name][
                                    base_data_slice, GlobalConfig.sel_code_list].to(
                                    device=use_device)

                        if intraday_data_only == True:
                            local_var_dict[rf"{base_data_name}"][:time_step_left_for_nan] = torch.nan

                    valid_step = result_data_slice.stop - result_data_slice.start
                    if ';' in fac_exp:
                        exp_list = fac_exp.split(';')
                        for exp in exp_list[:-1]:
                            exec(exp.strip(), globals(), local_var_dict)
                        exec(rf'temp = ' + exp_list[-1].strip(), globals(), local_var_dict)
                    else:
                        exec(rf'temp = ' + fac_exp.strip(), globals(), local_var_dict)

                    local_var_dict['valid_step'] = valid_step
                    local_var_dict['result_data_slice'] = result_data_slice
                    exec(rf'fac_res[result_data_slice] = temp[-valid_step:]', globals(), local_var_dict)
                gc.collect()
                torch.cuda.empty_cache()
                return fac_res
            except Exception as e:
                if time_step_each_loop == time_step_each_loop_try_list[-1]:
                    print("An error occurred:", e)
                    traceback_info = traceback.extract_tb(sys.exc_info()[2])
                    filename, line_number, function_name, text = traceback_info[-1]
                    print("Exception occurred in file:", filename)
                    print("On line number:", line_number)
                    print("In function:", function_name)
                    print("Exception line:", text)
                    del traceback_info
                    gc.collect()
                    torch.cuda.empty_cache()

    except Exception as e:
        print("An error occurred:", e)
        traceback_info = traceback.extract_tb(sys.exc_info()[2])
        filename, line_number, function_name, text = traceback_info[-1]
        print("Exception occurred in file:", filename)
        print("On line number:", line_number)
        print("In function:", function_name)
        print("Exception line:", text)
        del traceback_info
        gc.collect()
        torch.cuda.empty_cache()
        return


def unit_test():
    raise NotImplementedError


if __name__ == '__main__':
    unit_test()
