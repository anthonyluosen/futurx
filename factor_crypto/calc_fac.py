import pandas as pd
from factor_crypto.write_mmap import *
from factor_crypto.torch_operators import *

time_step_left_for_nan = time_step_num * 1
time_step_fac = time_step_num * 60 * 3

# 计算因子并保存至mmap
def calc_fac_byloc(fac_exp_dict, time_loc, code_loc):
    var_dict = locals()
    for base_name in base_name_list:
        exec(
            rf'var_dict["{base_name}"] = torch.from_numpy(mmap_dict["{base_name}"][{time_loc}-{time_step_left_for_nan}-{time_step_fac}+1:{time_loc}+1, [{code_loc}]])')

    for fac_name, fac_exp in fac_exp_dict.items():
        if ';' in fac_exp:
            exp_list = fac_exp.split(';')
            for exp in exp_list[:-1]:
                exec(exp.strip(), globals(), var_dict)
            exec(rf'temp = ' + exp_list[-1].strip(), globals(), var_dict)
        else:
            exec(rf'temp = ' + fac_exp.strip(), globals(), var_dict)
        fac = eval('temp')
        mmap_dict[fac_name][time_loc - time_step_fac + 1:time_loc + 1, code_loc] = fac[time_step_left_for_nan:,0].numpy()


def ts_rolling_quantile_pd(fea, q, window_size, min_periods):
    return fea.rolling(window=window_size, min_periods=min_periods).quantile(q)


def ts_rolling_mean_pd(fea, window_size, min_periods):
    return fea.rolling(window=window_size, min_periods=min_periods).mean()


def ts_rolling_std_pd(fea, window_size, min_periods):
    return fea.rolling(window=window_size, min_periods=min_periods).std()


def ts_zscore_fea_pd(fea, window_size, min_periods, fillna=True):
    fea_mean = ts_rolling_mean_pd(fea, window_size, min_periods)
    fea_std = ts_rolling_std_pd(fea, window_size, min_periods)
    if fillna:
        return ((fea - fea_mean) / fea_std).fillna(0)
    else:
        return (fea - fea_mean) / fea_std


def ts_dext_fea_pd(fea_in, d, dext_q):
    assert 0 <= dext_q <= 1, dext_q
    fea = fea_in.copy()
    fea = fea.replace([-np.inf, np.inf, np.nan], np.nan)

    fea_uq = ts_rolling_quantile_pd(fea, 1 - dext_q, d, d // 3)
    fea_dq = ts_rolling_quantile_pd(fea, dext_q, d, d // 3)

    fea_clip = fea.copy()
    for col in fea.columns:
        fea_clip[col] = np.clip(fea[col], fea_dq[col], fea_uq[col])
    return fea_clip


# 计算仓位
def calc_posi(fac_exp_dict, fac_sign_dict, time_loc, code_loc):
    preproc_d = 96 * 60
    fac_df = dict()
    for fac_name, fac_exp in fac_exp_dict.items():
        fac = mmap_dict[fac_name][time_loc - preproc_d * 3 + 1:time_loc + 1, code_loc]
        fac_df[fac_name] = pd.Series(fac) * fac_sign_dict[fac_name]
    fac_df = pd.DataFrame(fac_df)
    fea_dext_pd = ts_dext_fea_pd(fac_df, preproc_d, 0.01)
    fea_zscore_pd = ts_zscore_fea_pd(fea_dext_pd, preproc_d, preproc_d // 3, fillna=True)
    return fea_zscore_pd.iloc[-1].clip(-2, 2)

# if __name__ == '__main__':
#     roll_d = 48 * 1
#     calc_fac_byloc(fac_exp_dict,
#                               get_mmap_time_loc('2025-05-07 20:30:00'), get_mmap_code_loc('BTCUSDT'))
#     print(mmap_dict['test_fac'][get_mmap_time_loc('2025-05-07 20:30:00'), get_mmap_code_loc('BTCUSDT')])
