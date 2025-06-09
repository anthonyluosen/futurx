from factor_crypto.facfmk_config import *

base_data_name = rf'Base'
this_base_fea_path = rf'{base_data_fea_root_path}/{base_data_name}'
this_base_mmap_path = rf'{base_data_mmap_root_path}/{base_data_name}'
os.makedirs(this_base_fea_path, exist_ok=True)
os.makedirs(this_base_mmap_path, exist_ok=True)

base_name_list = ['Open', 'High', 'Low', 'Close', 'Volume', 'Amt']
fac_info_path = rf'{facfmk_root_path}/fac_info'
fac_exp_dict = load_pickle(rf'{fac_info_path}/fac_exp_dict.pkl')
fac_sign_dict = load_pickle(rf'{fac_info_path}/fac_sign_dict.pkl')
fac_name_list = list(fac_exp_dict.keys())
mmap_name_list = base_name_list + fac_name_list

# 初始化mmap
for base_name in tqdm(mmap_name_list, desc='create mmap'):
    mmap_path = rf"{this_base_mmap_path}/{base_name}.Mmap"
    if os.path.exists(mmap_path):
        pass
    else:
        base_data = return_rw_mmap(mmap_path, dtype='float32', shape=(date_num * time_step_num, code_num))
        base_data[:] = np.nan
        base_data.flush()
        del base_data

# 读取mmap
mmap_dict = dict()
for base_name in tqdm(mmap_name_list, desc='load mmap'):
    mmap_path = rf"{this_base_mmap_path}/{base_name}.Mmap"
    assert base_name not in mmap_dict
    mmap_dict[base_name] = return_rw_mmap(mmap_path, dtype='float32', shape=(date_num * time_step_num, code_num))


def read_mmap(time: str, code: str, mmap_name: str):
    """
    给定字符形式的time和code，返回mmap_name数值
    """
    time_loc = get_mmap_time_loc(time)
    code_loc = get_mmap_code_loc(code)
    return mmap_dict[mmap_name][time_loc, code_loc]


def read_cont_mmap(time_start: str, time_end: str, code: str, mmap_name: str):
    """
    给定字符形式的time_start, time_end和code，返回time_start至time_end的mmap_name数值
    注意是 time_start <= t <= time_end 的左闭右闭区间的数据
    """
    start_loc = get_mmap_time_loc(time_start)
    end_loc = get_mmap_time_loc(time_end)
    code_loc = get_mmap_code_loc(code)
    return np.array(mmap_dict[mmap_name][start_loc:end_loc + 1, code_loc])


def write_mmap(time: str, code: str, mmap_name: str, data: float):
    """
    给定字符形式的time和code，将data写入mmap_name字段
    """
    time_loc = get_mmap_time_loc(time)
    code_loc = get_mmap_code_loc(code)
    mmap_dict[mmap_name][time_loc, code_loc] = data


def write_cont_mmap(time_start: str, time_end: str, code: str, mmap_name: str, data: float):
    """
    给定字符形式的time_start, time_end和code，将data写入time_start至time_end的mmap_name字段
    注意是 time_start <= t <= time_end 的左闭右闭区间的数据
    """
    start_loc = get_mmap_time_loc(time_start)
    end_loc = get_mmap_time_loc(time_end)
    code_loc = get_mmap_code_loc(code)
    mmap_dict[mmap_name][start_loc:end_loc + 1, code_loc] = data


def write_mmap_byloc(time_loc, code_loc, mmap_name, data):
    """
    给定mmap索引位置的time和code，将data写入字段
    """
    mmap_dict[mmap_name][time_loc, code_loc] = data


def get_last_mmap_update_time(code, mmap_name_list):
    code_loc = get_mmap_code_loc(code)
    now_time = dt_to_second_str(datetime.now(tz=timezone.utc))
    tmls = [x for x in trade_time_cont if x <= now_time][::-1]
    for tm in tmls:
        time_loc = get_mmap_time_loc(tm)
        cnt = 0
        for name in mmap_name_list:
            if np.isfinite(mmap_dict[name][time_loc, code_loc]):
                cnt += 1
        if cnt >= len(mmap_name_list) / 2:
            return tm
    return tm


def get_mmap_time_delta(tm1, tm2):
    return trade_time_cont.index(tm1) - trade_time_cont.index(tm2)


def now_time_to_trade_time():
    now_time = dt_to_second_str(datetime.now(tz=timezone.utc))
    tm = max([x for x in trade_time_cont if x <= now_time])
    lc_tm = trade_time_cont[trade_time_cont.index(tm) - 1]
    return tm, lc_tm
