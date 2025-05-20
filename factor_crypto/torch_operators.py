import logging
from typing import List
import torch
import torch.nn.functional as F

EPS = 1e-12


def get_nan_tensor(shape, device, dtype):
    return torch.full(shape, torch.nan, dtype=dtype, device=device)


def add(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
    return torch.add(x, y)


def sub(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
    return torch.sub(x, y)


def mul(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
    return torch.mul(x, y)


def div(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
    return torch.where(torch.abs(y) > EPS, torch.divide(x, y), torch.nan)


def max(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
    return torch.maximum(x, y)


def min(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
    return torch.minimum(x, y)


def abs(x: torch.Tensor) -> torch.Tensor:
    return torch.abs(x)


def neg(x: torch.Tensor) -> torch.Tensor:
    return torch.negative(x)


def sqrt(x: torch.Tensor) -> torch.Tensor:
    return torch.sqrt(torch.abs(x))


def log(x: torch.Tensor) -> torch.Tensor:
    return torch.where(torch.abs(x) > EPS, torch.log(torch.abs(x)), torch.nan)


def pow(x: torch.Tensor, e: float) -> torch.Tensor:
    if e <= 1:
        return torch.pow(x.abs(), e)
    else:
        return torch.pow(x, e)


def inv(x: torch.Tensor) -> torch.Tensor:
    return torch.where(torch.abs(x) > EPS, torch.divide(1., x), torch.nan)


def sigmoid(x: torch.Tensor) -> torch.Tensor:
    return F.sigmoid(x)


def sign(x: torch.Tensor) -> torch.Tensor:
    return torch.sign(x)


def sign_square(x: torch.Tensor) -> torch.Tensor:
    return torch.sign(x) * torch.pow(torch.abs(x), 2)


# 返回x是否大于value的bool矩阵
def is_gt(x: torch.Tensor, value: any) -> torch.Tensor:
    return x > value


# 返回x是否小于value的bool矩阵
def is_lt(x: torch.Tensor, value: any) -> torch.Tensor:
    return x < value


# 取2个bool矩阵的交集
def bool_and2(x1: torch.Tensor, x2: torch.Tensor) -> torch.Tensor:
    return x1 & x2


# 只保留x中cond为True的部分，其余置为空值
def filt_cond(x: torch.Tensor, cond: torch.Tensor) -> torch.Tensor:
    return torch.where(cond, x, torch.nan)


# 返回展开的滑动窗口 2D -> 3D
def _unfold(x: torch.Tensor, d: int) -> torch.Tensor:
    res = get_nan_tensor(x.shape + (d,), device=x.device, dtype=x.dtype)
    res[d - 1:] = x.unfold(0, d, 1)
    return res


# 最后一个维度上求统计量
def _sum(x: torch.Tensor) -> torch.Tensor:
    return x.nansum(dim=-1)


def _mean(x: torch.Tensor) -> torch.Tensor:
    return x.nanmean(dim=-1)


def _stddev(x: torch.Tensor) -> torch.Tensor:
    x_demean = x - x.nanmean(dim=-1, keepdim=True)
    x_std = torch.sqrt(torch.nanmean(torch.pow(x_demean, 2), dim=-1))
    return x_std


def _skew(x: torch.Tensor):
    x_demeaned = x - x.nanmean(dim=-1, keepdim=True)
    x_std = torch.sqrt(torch.nanmean(torch.pow(x_demeaned, 2), dim=-1, keepdim=True))
    zscore = torch.pow(div(x_demeaned, x_std), 3)
    return _mean(zscore)


def _kurt(x: torch.Tensor):
    x_demeaned = x - x.nanmean(dim=-1, keepdim=True)
    x_var = torch.nanmean(torch.pow(x_demeaned, 2), dim=-1, keepdim=True)
    x_4 = torch.pow(x_demeaned, 4)
    return div(_mean(x_4), torch.pow(_mean(x_var), 2)) - 3


def _qua(x: torch.Tensor, q: float):
    return div(x.nanquantile(q, dim=-1), x.nanmean(dim=-1))


# 数值归一化后的熵
def _ent(x: torch.Tensor) -> torch.Tensor:
    x_norm = div(x, x.nansum(dim=-1, keepdim=True))
    res = - (x_norm * torch.log(x_norm)).nansum(dim=-1)
    res[res.abs() < EPS] = torch.nan
    return res


# 数值归一化后的交叉熵
def _cross_ent(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
    x_norm = div(x, x.nansum(dim=-1, keepdim=True))
    y_norm = div(y, y.nansum(dim=-1, keepdim=True))
    res = - (x_norm * torch.log(y_norm)).nansum(dim=-1)
    res[res.abs() < EPS] = torch.nan
    return res


def ts_ent(x: torch.Tensor, d: int) -> torch.Tensor:
    x_unfold = _unfold(x, d)
    return _ent(x_unfold)


def ts_cross_ent(x: torch.Tensor, y: torch.Tensor, d: int) -> torch.Tensor:
    x_unfold = _unfold(x, d)
    y_unfold = _unfold(y, d)
    return _cross_ent(x_unfold, y_unfold)


# 集中度
def _conc(x: torch.Tensor, q: any) -> torch.Tensor:
    if q <= 1:
        return div(_sum(torch.pow(x.abs(), q)), torch.pow(_sum(x.abs()), q))
    else:
        return div(_sum(torch.pow(x, q)), torch.pow(_sum(x), q))


def ts_conc(x: torch.Tensor, d: int, q: any) -> torch.Tensor:
    x_unfold = _unfold(x, d)
    return _conc(x_unfold, q)


# 位移路程比
def ts_diff_abs_sum(x: torch.Tensor, d: int) -> torch.Tensor:
    diff = ts_delta(x, 1)
    return div(ts_sum(diff, d), ts_sum(diff.abs(), d))


def ts_mean_selq(x: torch.Tensor, cond_var: torch.Tensor, d: int, low_q: float, high_q: float) -> torch.Tensor:
    x_unfold = _unfold(x, d)
    cond_unfold = _unfold(cond_var, d)
    low_value = torch.nanquantile(cond_unfold, low_q, dim=-1, keepdim=True)
    high_value = torch.nanquantile(cond_unfold, high_q, dim=-1, keepdim=True)
    cond = (cond_unfold >= low_value) & (cond_unfold <= high_value)
    x_unfold[~cond] = torch.nan
    return _mean(x_unfold)


def ts_stddev_selq(x: torch.Tensor, cond_var: torch.Tensor, d: int, low_q: float, high_q: float) -> torch.Tensor:
    x_unfold = _unfold(x, d)
    cond_unfold = _unfold(cond_var, d)
    low_value = torch.nanquantile(cond_unfold, low_q, dim=-1, keepdim=True)
    high_value = torch.nanquantile(cond_unfold, high_q, dim=-1, keepdim=True)
    cond = (cond_unfold >= low_value) & (cond_unfold <= high_value)
    x_unfold[~cond] = torch.nan
    return _stddev(x_unfold)


def ts_skew_selq(x: torch.Tensor, cond_var: torch.Tensor, d: int, low_q: float, high_q: float) -> torch.Tensor:
    x_unfold = _unfold(x, d)
    cond_unfold = _unfold(cond_var, d)
    low_value = torch.nanquantile(cond_unfold, low_q, dim=-1, keepdim=True)
    high_value = torch.nanquantile(cond_unfold, high_q, dim=-1, keepdim=True)
    cond = (cond_unfold >= low_value) & (cond_unfold <= high_value)
    x_unfold[~cond] = torch.nan
    return _skew(x_unfold)


def ts_kurt_selq(x: torch.Tensor, cond_var: torch.Tensor, d: int, low_q: float, high_q: float) -> torch.Tensor:
    x_unfold = _unfold(x, d)
    cond_unfold = _unfold(cond_var, d)
    low_value = torch.nanquantile(cond_unfold, low_q, dim=-1, keepdim=True)
    high_value = torch.nanquantile(cond_unfold, high_q, dim=-1, keepdim=True)
    cond = (cond_unfold >= low_value) & (cond_unfold <= high_value)
    x_unfold[~cond] = torch.nan
    return _kurt(x_unfold)


def ts_qua_selq(x: torch.Tensor, cond_var: torch.Tensor, d: int, q: float, low_q: float, high_q: float) -> torch.Tensor:
    x_unfold = _unfold(x, d)
    cond_unfold = _unfold(cond_var, d)
    low_value = torch.nanquantile(cond_unfold, low_q, dim=-1, keepdim=True)
    high_value = torch.nanquantile(cond_unfold, high_q, dim=-1, keepdim=True)
    cond = (cond_unfold >= low_value) & (cond_unfold <= high_value)
    x_unfold[~cond] = torch.nan
    return _qua(x_unfold, q)


def ts_delay(x: torch.Tensor, d: int) -> torch.Tensor:
    res = get_nan_tensor(shape=x.shape, device=x.device, dtype=x.dtype)
    res[d:] = x[:-d]
    return res


def ts_delta(x: torch.Tensor, d: int) -> torch.Tensor:
    res = get_nan_tensor(shape=x.shape, device=x.device, dtype=x.dtype)
    res[d:] = x[d:] - x[: -d]
    return res


def ts_corr(x: torch.Tensor, y: torch.Tensor, d: int) -> torch.Tensor:
    res = get_nan_tensor(shape=x.shape, device=x.device, dtype=x.dtype)
    x_unfold = x.unfold(0, d, 1)
    y_unfold = y.unfold(0, d, 1)

    x_demean = x_unfold - x_unfold.nanmean(dim=-1, keepdim=True)
    y_demean = y_unfold - y_unfold.nanmean(dim=-1, keepdim=True)

    x_std = torch.sqrt(torch.nansum(torch.pow(x_demean, 2), dim=-1))
    y_std = torch.sqrt(torch.nansum(torch.pow(y_demean, 2), dim=-1))

    numerator = (x_demean * y_demean).nansum(dim=-1)
    denominator = x_std * y_std
    res[d - 1:] = numerator / denominator

    res[d - 1:][(x_std < EPS) | (y_std < EPS)] = torch.nan
    return res


def ts_rankcorr(x: torch.Tensor, y: torch.Tensor, d: int) -> torch.Tensor:
    res = get_nan_tensor(shape=x.shape, device=x.device, dtype=x.dtype)
    x_unfold = _nanrank(x.unfold(0, d, 1), pct=False)
    y_unfold = _nanrank(y.unfold(0, d, 1), pct=False)

    x_demean = x_unfold - x_unfold.nanmean(dim=-1, keepdim=True)
    y_demean = y_unfold - y_unfold.nanmean(dim=-1, keepdim=True)

    x_std = torch.sqrt(torch.nansum(torch.pow(x_demean, 2), dim=-1))
    y_std = torch.sqrt(torch.nansum(torch.pow(y_demean, 2), dim=-1))

    numerator = (x_demean * y_demean).nansum(dim=-1)
    denominator = x_std * y_std
    res[d - 1:] = numerator / denominator

    res[d - 1:][(x_std < EPS) | (y_std < EPS)] = torch.nan
    return res


def ts_cov(x: torch.Tensor, y: torch.Tensor, d: int) -> torch.Tensor:
    res = get_nan_tensor(shape=x.shape, device=x.device, dtype=x.dtype)
    x_windows = x.unfold(0, d, 1)
    y_windows = y.unfold(0, d, 1)

    x_mean = x_windows.nanmean(dim=-1, keepdim=True)
    y_mean = y_windows.nanmean(dim=-1, keepdim=True)
    x_demeaned = x_windows - x_mean
    y_demeaned = y_windows - y_mean

    res[d - 1:] = (x_demeaned * y_demeaned).nansum(dim=-1) / d
    return res


def ts_autocorr(x: torch.Tensor, d: int, shift: int) -> torch.Tensor:
    res = get_nan_tensor(shape=x.shape, device=x.device, dtype=x.dtype)
    res[shift:] = ts_corr(x[shift:], x[:-shift], d)
    return res


def ts_decay_linear(x: torch.Tensor, d: int) -> torch.Tensor:
    w = torch.arange(1, d + 1, dtype=torch.float32, device=x.device)
    w = w / w.sum()
    x_unfolded = x.unfold(dimension=0, size=d, step=1)
    w = w.view(1, 1, -1)
    res = torch.nansum(x_unfolded * w, dim=-1)
    result = get_nan_tensor(shape=x.shape, device=x.device, dtype=x.dtype)
    result[d - 1:] = res
    return result


# 对最后一个维度排序 跳过空值 排名从1开始 支持将非valid_mask的元素置为空值 pct返回比例
def _nanrank(x: torch.Tensor, valid_mask: torch.Tensor = None, pct: bool = True) -> torch.Tensor:
    ranks = x.clone()
    if valid_mask is None:
        valid_mask = torch.isfinite(x)
    ranks[~valid_mask] = torch.finfo(x.dtype).max
    ranks = torch.argsort(torch.argsort(ranks, dim=-1), dim=-1)
    ranks = ranks.to(dtype=x.dtype) + 1
    if pct:
        valid_counts = valid_mask.sum(dim=-1, keepdim=True)
        ranks = ranks / valid_counts
    ranks[~valid_mask] = torch.nan
    return ranks


def ts_rank(x: torch.Tensor, d: int, pct: bool = True) -> torch.Tensor:
    res = get_nan_tensor(shape=x.shape, device=x.device, dtype=x.dtype)
    res[d - 1:] = _nanrank(x.unfold(0, d, 1), pct=pct)[..., -1]
    return res


# 求最后一个维度的最小值 跳过空值 支持将非valid_mask的元素置为空值
def _nanmin(x: torch.Tensor, valid_mask: torch.Tensor = None) -> torch.Tensor:
    xc = x.clone()
    if valid_mask is None:
        valid_mask = torch.isfinite(x)
    xc[~valid_mask] = torch.finfo(x.dtype).max
    res = xc.min(dim=-1).values
    res[valid_mask.sum(dim=-1) == 0] = torch.nan
    return res


# 求最后一个维度的最大值 跳过空值 支持将非valid_mask的元素置为空值
def _nanmax(x: torch.Tensor, valid_mask: torch.Tensor = None) -> torch.Tensor:
    xc = x.clone()
    if valid_mask is None:
        valid_mask = torch.isfinite(x)
    xc[~valid_mask] = torch.finfo(x.dtype).min
    res = xc.max(dim=-1).values
    res[valid_mask.sum(dim=-1) == 0] = torch.nan
    return res


def ts_min(x: torch.Tensor, d: int) -> torch.Tensor:
    res = get_nan_tensor(shape=x.shape, device=x.device, dtype=x.dtype)
    res[d - 1:] = _nanmin(x.unfold(0, d, 1))
    return res


def ts_max(x: torch.Tensor, d: int) -> torch.Tensor:
    res = get_nan_tensor(shape=x.shape, device=x.device, dtype=x.dtype)
    res[d - 1:] = _nanmax(x.unfold(0, d, 1))
    return res


# 求最后一个维度的最小值位置 跳过空值 支持将非valid_mask的元素置为空值
def _nanargmin(x: torch.Tensor, valid_mask: torch.Tensor = None) -> torch.Tensor:
    xc = x.clone()
    if valid_mask is None:
        valid_mask = torch.isfinite(x)
    xc[~valid_mask] = torch.finfo(x.dtype).max
    res = xc.argmin(dim=-1).to(dtype=x.dtype)
    res[valid_mask.sum(dim=-1) == 0] = torch.nan
    return res


# 求最后一个维度的最大值位置 跳过空值 支持将非valid_mask的元素置为空值
def _nanargmax(x: torch.Tensor, valid_mask: torch.Tensor = None) -> torch.Tensor:
    xc = x.clone()
    if valid_mask is None:
        valid_mask = torch.isfinite(x)
    xc[~valid_mask] = torch.finfo(x.dtype).min
    res = xc.argmax(dim=-1).to(dtype=x.dtype)
    res[valid_mask.sum(dim=-1) == 0] = torch.nan
    return res


def ts_argmin(x: torch.Tensor, d: int, pct: bool = True) -> torch.Tensor:
    res = get_nan_tensor(shape=x.shape, device=x.device, dtype=x.dtype)
    res[d - 1:] = d - 1 - _nanargmin(x.unfold(0, d, 1))
    if pct:
        res = (res + 1) / d
    return res


def ts_argmax(x: torch.Tensor, d: int, pct: bool = True) -> torch.Tensor:
    res = get_nan_tensor(shape=x.shape, device=x.device, dtype=x.dtype)
    res[d - 1:] = d - 1 - _nanargmax(x.unfold(0, d, 1))
    if pct:
        res = (res + 1) / d
    return res


def ts_sum(x: torch.Tensor, d: int) -> torch.Tensor:
    res = get_nan_tensor(shape=x.shape, device=x.device, dtype=x.dtype)
    unfolded = x.unfold(dimension=0, size=d, step=1)
    res[d - 1:] = unfolded.nansum(dim=-1, keepdim=False)
    return res


def ts_mean(x: torch.Tensor, d: int) -> torch.Tensor:
    res = get_nan_tensor(shape=x.shape, device=x.device, dtype=x.dtype)
    unfolded = x.unfold(dimension=0, size=d, step=1)
    res[d - 1:] = unfolded.nanmean(dim=-1)
    return res


def ts_quantile(x: torch.Tensor, q: float, d: int) -> torch.Tensor:
    res = get_nan_tensor(shape=x.shape, device=x.device, dtype=x.dtype)
    res[d - 1:] = torch.nanquantile(x.unfold(0, d, 1), q, dim=-1)
    return res


def ts_qua(x: torch.Tensor, q: float, d: int) -> torch.Tensor:
    return ts_quantile(x, q, d) / ts_mean(x, d)


def ts_return(x: torch.Tensor, d: int) -> torch.Tensor:
    numerator = ts_delta(x, d)
    denominator = ts_delay(x, d)
    res = div(numerator, denominator)
    return res


def ts_mean_return(x: torch.Tensor, d: int) -> torch.Tensor:
    return ts_mean(ts_return(x, 1), d)


def ts_product(x: torch.Tensor, d: int) -> torch.Tensor:
    res = get_nan_tensor(shape=x.shape, device=x.device, dtype=x.dtype)
    unfolded = x.unfold(0, d, 1)
    res[d - 1:] = fillna(unfolded, 1).prod(dim=-1)
    return res


def ts_stddev(x: torch.Tensor, d: int) -> torch.Tensor:
    res = get_nan_tensor(shape=x.shape, device=x.device, dtype=x.dtype)
    x_unfold = x.unfold(0, d, 1)
    x_demean = x_unfold - x_unfold.nanmean(dim=-1, keepdim=True)
    x_std = torch.sqrt(torch.nanmean(torch.pow(x_demean, 2), dim=-1))
    res[d - 1:] = x_std
    return res


def ts_demean(x: torch.Tensor, d: int):
    return x - ts_mean(x, d)


# def ts_zscore(x: torch.Tensor, d: int):
#     x_demeaned = ts_demean(x, d)
#     x_std = ts_stddev(x, d)
#     return div(x_demeaned, x_std)


def ts_zscore(x: torch.Tensor, d: int):
    x_unfold = _unfold(x, d)
    x_demeaned = x_unfold - x_unfold.nanmean(dim=-1, keepdim=True)
    x_std = torch.sqrt(torch.nanmean(torch.pow(x_demeaned, 2), dim=-1, keepdim=True))
    zscore = div(x_demeaned, x_std)
    return zscore[..., -1]


# def ts_skew(x: torch.Tensor, d: int):
#     roll_zscore = torch.pow(ts_zscore(x, d), 3)
#     return ts_mean(roll_zscore, d)


def ts_skew(x: torch.Tensor, d: int):
    x_unfold = _unfold(x, d)
    return _skew(x_unfold)


# def ts_kurt(x: torch.Tensor, d: int):
#     roll_zscore = torch.pow(ts_zscore(x, d), 4)
#     return ts_mean(roll_zscore, d) - 3


def ts_kurt(x: torch.Tensor, d: int):
    x_unfold = _unfold(x, d)
    return _kurt(x_unfold)


def ts_regbeta(x: torch.Tensor, y: torch.Tensor, d: int) -> torch.Tensor:
    res = get_nan_tensor(shape=x.shape, device=x.device, dtype=x.dtype)
    x_unfold = x.unfold(0, d, 1)
    y_unfold = y.unfold(0, d, 1)
    x_mean = x_unfold.nanmean(dim=-1, keepdim=True)
    y_mean = y_unfold.nanmean(dim=-1, keepdim=True)
    x_demean = x_unfold - x_mean
    y_demean = y_unfold - y_mean
    std = torch.nansum(torch.pow(x_demean, 2), dim=-1)
    res[d - 1:] = torch.where(std < EPS, torch.nan, torch.nansum(x_demean * y_demean, dim=-1) / std)
    return res


def ts_regres(x: torch.Tensor, y: torch.Tensor, d: int) -> torch.Tensor:
    beta = ts_regbeta(x, y, d)
    return y - beta * x


def ts_rankregbeta(x: torch.Tensor, y: torch.Tensor, d: int) -> torch.Tensor:
    res = get_nan_tensor(shape=x.shape, device=x.device, dtype=x.dtype)
    x_unfold = _nanrank(x.unfold(0, d, 1), pct=False)
    y_unfold = _nanrank(y.unfold(0, d, 1), pct=False)
    x_mean = x_unfold.nanmean(dim=-1, keepdim=True)
    y_mean = y_unfold.nanmean(dim=-1, keepdim=True)
    x_demean = x_unfold - x_mean
    y_demean = y_unfold - y_mean
    std = torch.nansum(torch.pow(x_demean, 2), dim=-1)
    res[d - 1:] = torch.where(std < EPS, torch.nan, torch.nansum(x_demean * y_demean, dim=-1) / std)
    return res


def ts_rankregres(x: torch.Tensor, y: torch.Tensor, d: int) -> torch.Tensor:
    res = get_nan_tensor(shape=x.shape, device=x.device, dtype=x.dtype)
    x_unfold = _nanrank(x.unfold(0, d, 1), pct=False)
    y_unfold = _nanrank(y.unfold(0, d, 1), pct=False)
    x_mean = x_unfold.nanmean(dim=-1, keepdim=True)
    y_mean = y_unfold.nanmean(dim=-1, keepdim=True)
    x_demean = x_unfold - x_mean
    y_demean = y_unfold - y_mean
    std = torch.nansum(torch.pow(x_demean, 2), dim=-1)
    beta = torch.where(std < EPS, torch.nan, torch.nansum(x_demean * y_demean, dim=-1) / std)
    res[d - 1:] = y_unfold[..., -1] - beta * x_unfold[..., -1]
    return res


def ts_wma(x: torch.Tensor, d: int) -> torch.Tensor:
    res = get_nan_tensor(shape=x.shape, device=x.device, dtype=x.dtype)
    w = torch.tensor([0.9 ** i for i in range(d, 0, -1)], dtype=x.dtype, device=x.device)
    w = w / w.nansum()
    x_unfold = x.unfold(0, d, 1)
    res[d - 1:] = (x_unfold * w).nansum(dim=-1)
    return res


def question_xn0(x: torch.Tensor, y: torch.Tensor, z: torch.Tensor) -> torch.Tensor:
    return torch.where(x > 0, y, z)


def question_xny(x: torch.Tensor, y: torch.Tensor, z: torch.Tensor, w: torch.Tensor) -> torch.Tensor:
    return torch.where(x > y, z, w)


def fillna(x: torch.Tensor, fill_value: any, valid_mask: torch.Tensor = None) -> torch.Tensor:
    res = torch.where(x.isfinite(), x, fill_value)
    if valid_mask is not None:
        res[~valid_mask] = torch.nan
    return res


# 每个横截面上，x等于某固定值（如0）的比例
def cs_certain_value_proportion(x: torch.Tensor, valid_mask: torch.Tensor, certain_value: any) -> torch.Tensor:
    valid_count = ((x - certain_value).abs() < EPS).sum(dim=-1)
    tot_count = valid_mask.sum(dim=-1)
    return valid_count / tot_count


# 每个横截面上，x为nan的比例
def cs_nan_proportion(x: torch.Tensor, valid_mask: torch.Tensor) -> torch.Tensor:
    valid_count = torch.isfinite(x).sum(dim=-1)
    tot_count = valid_mask.sum(dim=-1)
    return 1 - valid_count / tot_count


# 横截面相关系数
def cs_corr(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
    x_demean = x - x.nanmean(dim=-1, keepdim=True)
    y_demean = y - y.nanmean(dim=-1, keepdim=True)

    x_std = torch.sqrt(torch.nansum(torch.pow(x_demean, 2), dim=-1))
    y_std = torch.sqrt(torch.nansum(torch.pow(y_demean, 2), dim=-1))

    numerator = (x_demean * y_demean).nansum(dim=-1)
    denominator = x_std * y_std
    res = numerator / denominator

    res[(x_std < EPS) | (y_std < EPS)] = torch.nan
    return res


# 横截面排序 排名从1开始 支持自定义valid_mask pct返回比例
def cs_rank(x: torch.Tensor, valid_mask: torch.Tensor = None, pct: bool = True) -> torch.Tensor:
    ranks = x.clone()
    if valid_mask is None:
        valid_mask = torch.isfinite(x)
    ranks[~valid_mask] = torch.finfo(x.dtype).max
    ranks = torch.argsort(torch.argsort(ranks, dim=-1), dim=-1)
    ranks = ranks.to(dtype=x.dtype) + 1
    if pct:
        valid_counts = valid_mask.sum(dim=-1, keepdim=True)
        ranks = ranks / valid_counts
    ranks[~valid_mask] = torch.nan
    return ranks


# 横截面求均值
def cs_mean(x: torch.Tensor) -> torch.Tensor:
    return torch.where(torch.isfinite(x), x.nanmean(dim=-1, keepdim=True), torch.tensor(torch.nan, device=x.device))


# 等分为N组的排名分界点
def get_group_rank_cutpoint(tot_num: int, group_num: int, start_rank: int = 1,
                            device: torch.device = torch.device('cpu')):
    step = tot_num // group_num
    low_rank = torch.arange(start=0, end=group_num * step, step=step)
    high_rank = torch.arange(start=step, end=tot_num + 1, step=step)
    assert len(low_rank) == len(high_rank) == group_num
    high_rank[-1] = tot_num
    low_rank += (start_rank - 1)
    high_rank += (start_rank - 1)
    return low_rank.to(device), high_rank.to(device)


# 等分为N组的排名分位数分界点
def get_group_quantile_cutpoint(group_num: int, device: torch.device = torch.device('cpu')):
    step = 1 / group_num
    low_rank = torch.tensor([step * x for x in range(group_num)])
    high_rank = torch.tensor([step * (x + 1) for x in range(group_num)])
    assert len(low_rank) == len(high_rank) == group_num
    low_rank[0] = -1
    high_rank[-1] = 1
    return low_rank.to(device), high_rank.to(device)


# 将valid_mask中的空值按截面均值填充
def cs_fillna_mean(x: torch.Tensor, valid_mask: torch.Tensor) -> torch.Tensor:
    assert x.shape == valid_mask.shape
    res = x.clone()
    finite_mask = torch.isfinite(res) & valid_mask
    res[~finite_mask] = torch.nan
    res_mean = torch.nanmean(res, dim=-1, keepdim=True)
    res[~finite_mask] = res_mean.expand_as(res)[~finite_mask]
    res[~valid_mask] = torch.nan
    return res


# 根据x在截面上分组，求每组内y的均值
def cs_group_mean(x: torch.Tensor, y: torch.Tensor, valid_mask: torch.Tensor, group_num: int) -> torch.Tensor:
    if valid_mask is not None:
        assert x.shape == y.shape == valid_mask.shape
    else:
        assert x.shape == y.shape
    # res = cs_fillna_mean(x, valid_mask)
    res = x.clone()
    res_rank = cs_rank(res, valid_mask=valid_mask, pct=True)
    group_mean = get_nan_tensor(shape=(res.shape[0], group_num), device=res.device, dtype=res.dtype)
    for group_idx, (low_q, high_q) in enumerate(zip(*get_group_quantile_cutpoint(group_num, device=res.device))):
        cond = (res_rank > low_q) & (res_rank <= high_q)
        y_cond = torch.where(cond, y, torch.tensor(torch.nan, device=res.device))
        group_mean[:, group_idx] = y_cond.nanmean(dim=-1)
    return group_mean


# 根据x在截面上找前head_num和后tail_num个标的，求每组内y的均值
def cs_head_mean(x: torch.Tensor, y: torch.Tensor, valid_mask: torch.Tensor, head_num_list: List[int],
                 tail_num_list: List[int]) -> torch.Tensor:
    if valid_mask is not None:
        assert x.shape == y.shape == valid_mask.shape
    else:
        assert x.shape == y.shape
    # res = cs_fillna_mean(x, valid_mask)
    res = x.clone()
    res_rank = cs_rank(res, valid_mask=valid_mask, pct=False)
    num_list = head_num_list + tail_num_list
    group_mean = get_nan_tensor(shape=(res.shape[0], len(num_list)), device=res.device, dtype=res.dtype)
    # 头部 排名为1至count_num
    for group_idx, count_num in enumerate(head_num_list, start=0):
        cond = res_rank <= count_num
        y_cond = torch.where(cond, y, torch.tensor(torch.nan, device=res.device))
        group_mean[:, group_idx] = y_cond.nanmean(dim=-1)
    # 尾部 排名为-count_num至-1
    dtype_min = torch.finfo(res_rank.dtype).min
    for group_idx, count_num in enumerate(tail_num_list, start=len(head_num_list)):
        # 求每一个时间步的最大排名
        res_rank_max = torch.nan_to_num(res_rank, nan=dtype_min, neginf=dtype_min, posinf=dtype_min).max(dim=-1,
                                                                                                         keepdim=True).values
        cond = res_rank_max - res_rank + 1 <= count_num
        y_cond = torch.where(cond, y, torch.tensor(torch.nan, device=res.device))
        group_mean[:, group_idx] = y_cond.nanmean(dim=-1)
    return group_mean


if __name__ == "__main__":
    pass
