import sys
from factor_crypto.utils import *


def display_ls(ls, name):
    print(name, ls[:3], ls[-3:], len(ls))


def get_all_support_data_dict():
    trade_time_loc_dict = load_pickle(rf'{config_data_path}/trade_time_loc_dict.pkl')
    trade_code_loc_dict = load_pickle(rf'{config_data_path}/trade_code_loc_dict.pkl')
    trade_date_loc_dict = load_pickle(rf'{config_data_path}/trade_date_loc_dict.pkl')
    trade_time_cont = load_pickle(rf'{config_data_path}/trade_time_cont.pkl')

    trade_time_list = list(trade_time_loc_dict.keys())
    trade_time_list.sort()
    trade_date_list = sorted(trade_date_loc_dict, key=lambda k: trade_date_loc_dict[k])
    trade_code_list = sorted(trade_code_loc_dict, key=lambda k: trade_code_loc_dict[k])

    for name in ['trade_time_list', 'trade_code_list', 'trade_date_list', 'trade_time_cont']:
        ls = eval(name)
        display_ls(ls, name)

    return (trade_date_list, trade_code_list, trade_time_list, trade_time_cont,
            trade_date_loc_dict, trade_code_loc_dict, trade_time_loc_dict)


# 字段频率
base_itvl = "15min"
# 框架总目录
base_dir = os.path.dirname(os.path.dirname(__file__))
base_dir = os.path.join(os.path.dirname(base_dir),"data")

facfmk_root_path = rf'{base_dir}/facfmk/{base_itvl}'
static_config_data_path = rf'{base_dir}/facfmk/support_data'
config_data_path = rf'{facfmk_root_path}/support_data'
base_data_fea_root_path = rf'{facfmk_root_path}/BaseData/Feather'
base_data_mmap_root_path = rf'{facfmk_root_path}/BaseData/Mmap'
os.makedirs(static_config_data_path, exist_ok=True)
os.makedirs(config_data_path, exist_ok=True)
os.makedirs(base_data_fea_root_path, exist_ok=True)
os.makedirs(base_data_mmap_root_path, exist_ok=True)

fmk_start_date = '2022-01-01'
fmk_end_date = '2026-12-31'

(trade_date_list, trade_code_list, trade_time_list, trade_time_cont,
 trade_date_loc_dict, trade_code_loc_dict, trade_time_loc_dict) = get_all_support_data_dict()

date_num = len(list(trade_date_loc_dict.keys()))
code_num = len(list(trade_code_loc_dict.keys()))
time_step_num = len(list(trade_time_loc_dict.keys()))


def get_mmap_time_loc(tm):
    return trade_time_cont.index(tm)


def get_mmap_code_loc(code):
    return trade_code_loc_dict[code]


if __name__ == '__main__':
    all_date_range = pd.date_range(start=fmk_start_date, end=fmk_end_date)
    all_date_list = [date.strftime('%Y-%m-%d') for date in all_date_range]
    fill_date_list = [x for x in all_date_list if x not in trade_date_list]
    display_ls(fill_date_list, 'date to be filled')

    if len(fill_date_list) > 0:
        for date in fill_date_list:
            trade_date_list.append(date)
            time_td = [rf'{date} {time}' for time in trade_time_list]
            trade_time_cont.extend(time_td)
        assert trade_date_list == all_date_list
        assert len(trade_date_list) * len(trade_time_list) == len(trade_time_cont)
        for name in ['trade_time_list', 'trade_code_list', 'trade_date_list', 'trade_time_cont']:
            ls = eval(name)
            display_ls(ls, name)

        trade_date_loc_dict = dict(zip(trade_date_list, range(len(trade_date_list))))
        dump_pickle(rf'{config_data_path}/trade_date_loc_dict.pkl', trade_date_loc_dict)
        dump_pickle(rf'{config_data_path}/trade_time_cont.pkl', trade_time_cont)
