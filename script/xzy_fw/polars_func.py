import polars as pl
import numpy as np
import pandas as pd
import math
import matplotlib.pyplot as plt


# polars版

def replace_nan_pl(fea):
    return (fea.lazy().select([pl.col(col).replace([-np.inf, np.inf, np.nan], None) for col in fea.columns])).collect()


def fillna_pl(fea, value):
    return fea.lazy().select([pl.col(col).replace(None, value).alias(col) for col in fea.columns]).collect()


# 时序分位数，均值，标准差，zscore
def ts_rolling_quantile_pl(fea, q, window_size, min_periods):
    fea_q = fea.lazy().select([
        pl.col(col).rolling_quantile(quantile=q, interpolation="linear", window_size=window_size,
                                     min_periods=min_periods).alias(col)
        for col in fea.columns
    ])
    return fea_q.collect()


def ts_rolling_mean_pl(fea, window_size, min_periods):
    fea_mean = fea.lazy().select([
        pl.col(col).rolling_mean(window_size=window_size, min_periods=min_periods).alias(col)
        for col in fea.columns
    ])
    return fea_mean.collect()


def ts_rolling_std_pl(fea, window_size, min_periods):
    fea_std = fea.lazy().select([
        pl.col(col).rolling_std(window_size=window_size, min_periods=min_periods).alias(col)
        for col in fea.columns
    ])
    return fea_std.collect()


def ts_zscore_fea_pl(fea, window_size, min_periods, fillna=True):
    fea_mean = ts_rolling_mean_pl(fea, window_size, min_periods)
    fea_std = ts_rolling_std_pl(fea, window_size, min_periods)
    if fillna:
        fea_zscore = fea.lazy().select([
            ((pl.col(col) - fea_mean[col]) / fea_std[col]).replace(None, 0).alias(col)
            for col in fea.columns
        ])
    else:
        fea_zscore = fea.lazy().select([
            ((pl.col(col) - fea_mean[col]) / fea_std[col]).alias(col)
            for col in fea.columns
        ])
    return fea_zscore.collect()


def ts_dext_fea_pl(fea_in, d, dext_q):
    assert 0 <= dext_q <= 1, dext_q
    fea = fea_in.clone()
    # 替换inf和nan
    fea = replace_nan_pl(fea)

    # 超过dext_q的分位数认为是极值，做替换
    fea_uq = ts_rolling_quantile_pl(fea, 1 - dext_q, d, d // 3)
    fea_dq = ts_rolling_quantile_pl(fea, dext_q, d, d // 3)

    fea_clip = fea
    for col in fea.columns:
        fea_clip = fea_clip.lazy().with_columns(
            pl.when(pl.col(col) > fea_uq[col])
            .then(fea_uq[col])
            .when(pl.col(col) < fea_dq[col])
            .then(fea_dq[col])
            .otherwise(pl.col(col))
            .alias(col)
        )
    fea_clip = fea_clip.collect()
    return fea_clip


def ts_qsig_fea_pl(fea_clip, d, long_q, short_q):
    long_sig = ts_rolling_quantile_pl(fea_clip, long_q, d, d // 3)
    short_sig = ts_rolling_quantile_pl(fea_clip, short_q, d, d // 3)

    sig = fea_clip.clone()
    for col in sig.columns:
        sig = sig.lazy().with_columns(
            pl.when(pl.col(col) > long_sig[col])
            .then(1)
            .when(pl.col(col) < short_sig[col])
            .then(-1)
            .otherwise(0)
            .alias(col)
        )
    return sig.collect()


# 仓位+label算收益率均值，标准差，夏普
# label可以是不同频率
def ts_ret_stat_pl(posi, label, return_pandas=False):
    ret = posi * label
    ret_mean = ret.select([
        pl.col(col).mean().alias(col)
        for col in ret.columns
    ])
    ret_std = ret.select([
        pl.col(col).std().alias(col)
        for col in ret.columns
    ])
    sharpe = ret_mean / ret_std
    if return_pandas:
        return ret_mean.to_pandas(), ret_std.to_pandas(), sharpe.to_pandas()
    else:
        return ret_mean, ret_std, sharpe


# 每单位仓位变动对应的收益率
def ts_ret_pchg_pl(posi, label):
    raise NotImplementedError
    ret_mean, ret_std, sharpe = ts_ret_stat_pl(posi, label)
    pchg_mean = posi.select([
        pl.col(col).diff().abs().mean().alias(col)
        for col in posi.columns
    ])
    ret_mean_pchg = ret_mean / pchg_mean
    return ret_mean_pchg


# 每单位仓位绝对值对应的收益率
def ts_ret_pabs_pl(posi, label, return_pandas=False):
    ret = posi * label
    ret_sum = ret.select([
        pl.col(col).sum().alias(col)
        for col in ret.columns
    ])
    pabs_sum = posi.select([
        pl.col(col).abs().sum().alias(col)
        for col in posi.columns
    ])
    ret_sum_pabs = ret_sum / pabs_sum
    if return_pandas:
        return ret_sum_pabs.to_pandas()
    else:
        return ret_sum_pabs


# 仓位的多头空头比例
def ts_posi_ls_ratio_pl(posi, return_pandas=False):
    long_posi_sum = (posi.lazy().select([
        pl.when(pl.col(col) > 1e-9).then(pl.col(col)).otherwise(None).sum()
        for col in posi.columns
    ])).collect()
    short_posi_sum = (posi.lazy().select([
        pl.when(pl.col(col) < -1e-9).then(pl.col(col)).otherwise(None).abs().sum()
        for col in posi.columns
    ])).collect()
    posi_sum = long_posi_sum + short_posi_sum
    long_ratio = long_posi_sum / posi_sum
    short_ratio = short_posi_sum / posi_sum
    if return_pandas:
        return long_ratio.to_pandas(), short_ratio.to_pandas()
    else:
        return long_ratio, short_ratio


# 时序ic
def ts_corr_pl(x, y):
    return (x.lazy().select([
        pl.corr(x[col], y[col])
        for col in x.columns
    ])).collect()


# 时序ric
def ts_rankcorr_pl(x, y):
    return (x.lazy().select([
        pl.corr(x[col], y[col], method="spearman")
        for col in x.columns
    ])).collect()


# 全通道固定间隔调一次仓 可以考虑成本
def get_pnl_itvl_daily(posi_pl, ret_pl, itvl, daily_time_step_count, sign, cost, trade_date_list, valid_trade_date_list,
                       trade_code_list, valid_mask, days_multi=365):
    num_col = [str(x) for x in range(posi_pl.shape[1])]
    posi_col = [rf'posi_{x}' for x in num_col]
    ret_col = [rf'ret_{x}' for x in num_col]
    _posi_pl = posi_pl.clone()
    _ret_pl = ret_pl.clone()
    _posi_pl.columns = posi_col
    _ret_pl.columns = ret_col

    temp = _posi_pl.hstack(_ret_pl)
    temp.columns = posi_col + ret_col
    temp = temp.with_columns(
        (pl.arange(0, temp.height) % itvl).alias("itvl_id"),
        (pl.arange(0, temp.height) // daily_time_step_count).alias("date_id")
    )
    pnl_itvl = temp.group_by(['date_id', 'itvl_id'], maintain_order=True).agg([
        ((pl.col(rf'posi_{x}') * pl.col(rf'ret_{x}')).sum() * sign - cost * pl.col(
            rf'posi_{x}').diff().abs().sum()).alias(x) for x in num_col
    ])
    pnl_itvl /= itvl

    # 全品种日度pnl曲线
    pnl_itvl_daily = pnl_itvl.to_pandas().groupby('date_id').sum().reset_index().loc[:, '0':]
    pnl_itvl_daily.index = trade_date_list
    pnl_itvl_daily.columns = trade_code_list
    assert pnl_itvl_daily.shape == valid_mask.shape
    pnl_itvl_daily = pnl_itvl_daily[valid_mask]
    pnl_itvl_daily = pnl_itvl_daily.loc[valid_trade_date_list]
    ret_yearly = pnl_itvl_daily.mean() * days_multi
    vol_yearly = pnl_itvl_daily.std() * days_multi ** 0.5
    sharpe_yearly = ret_yearly / vol_yearly
    ret_1trd = ret_yearly / days_multi / daily_time_step_count * itvl

    ret_yearly.index = trade_code_list
    sharpe_yearly.index = trade_code_list
    ret_1trd.index = trade_code_list

    return pnl_itvl_daily, ret_yearly, sharpe_yearly, ret_1trd


# 以下为其他函数
def format_xticks(raw_xticks, target_num):
    locs = np.linspace(0, len(raw_xticks) - 1, target_num + 1)
    locs = [int(loc) for loc in locs]
    xs = [raw_xticks[loc] for loc in locs]
    return locs, xs


def plot_ret(ret_list, ret_name_list, title_name, ax, reinvest_type='cumsum'):
    max_drawdown_ser_list = []
    color_list = ['C0', 'C1', 'C4', 'C2', 'C3', 'C4', 'C5']
    for idx, (ret, ret_name) in enumerate(zip(ret_list, ret_name_list)):
        ret_ser = ret
        if reinvest_type == 'cumprod':
            net_value_ser = (ret_ser + 1).cumprod()
        else:
            net_value_ser = ret_ser.cumsum()
        annual_ret = ret_ser.mean() * 365
        annual_ret_percent = annual_ret * 100
        annual_vol = ret_ser.std() * math.sqrt(365)
        sharp_ratio = annual_ret / annual_vol
        Max_NV = pd.Series(index=net_value_ser.index, dtype='float')
        for i, date in enumerate(Max_NV.index):
            Max_NV.loc[date] = net_value_ser.iloc[:i + 1].max()
        max_drawdown_ser = Max_NV - net_value_ser
        max_drawdown_ser_list.append(max_drawdown_ser)
        max_dd = max_drawdown_ser.max() * 100
        ax.plot(net_value_ser,
                label=f"{ret_name}, Return: %.2f" % annual_ret_percent + r'%' + '; Sharpe: %.2f' % sharp_ratio
                      + '; mdd: %.2f' % max_dd + r'%', color=color_list[idx])
    ax.legend(loc="upper center", fontsize=16)
    locs, xs = format_xticks(net_value_ser.index, 20)
    ax.set_xticks(locs)
    ax.set_xticklabels(xs, rotation=45)
    max_dd = max_drawdown_ser.max() * 100

    _ax = ax.twinx()
    _ax.stackplot(max_drawdown_ser.index, max_drawdown_ser, labels=["mdd_ls: %.4f" % max_dd + r'%'],
                  alpha=0.5,
                  color="blue")
    _ax.legend(loc="center left", fontsize=16)
    _ax.set_ylim(0, max_drawdown_ser.max() * 2)
    _ax.set_xticks(locs)
    _ax.set_xticklabels(xs, rotation=45)
    plt.title(title_name, fontsize=20)
