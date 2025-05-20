import pandas as pd
import numpy as np
import zipfile
from tqdm import tqdm
import glob
import os
import pickle
import gzip
import torch
from torch.utils.data import Dataset, DataLoader
import matplotlib.pyplot as plt
from datetime import datetime, timezone


def load_pickle(path):
    with open(path, 'rb') as f:
        return pickle.load(f)


def dump_pickle(path, data):
    directory = os.path.dirname(path)
    if not os.path.exists(directory):
        os.makedirs(directory)
    with open(path, 'wb') as f:
        pickle.dump(data, f)


# 返回创建或可修改的内存映射
def return_rw_mmap(file_path, dtype, shape):
    if os.path.exists(file_path):
        factor_data = np.memmap(file_path, dtype=dtype, mode='r+', shape=shape)
    else:
        factor_data = np.memmap(file_path, dtype=dtype, mode='w+', shape=shape)
    return factor_data


# 返回只读的内存映射
def return_ro_mmap(file_path, dtype, shape):
    factor_data = np.memmap(file_path, dtype=dtype, mode='r', shape=shape)
    return factor_data


def dt_to_second_str(dt: datetime):
    return dt.strftime('%Y-%m-%d %H:%M:%S')


def second_str_to_dt(second_str: str) -> datetime:
    return datetime.strptime(second_str, '%Y-%m-%d %H:%M:%S')


def msts_to_dt(msts: int):
    return datetime.fromtimestamp(msts / 1000, tz=timezone.utc)


def dt_to_msts(dt: datetime):
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)


def msts_to_second_str(msts: int):
    return dt_to_second_str(msts_to_dt(msts))


def second_str_to_msts(second_str: str):
    return dt_to_msts(second_str_to_dt(second_str))


def sep_list(list_in, max_len):
    res = []
    n = len(list_in) // max_len
    for i in range(n):
        res.append(list_in[i * max_len: (i + 1) * max_len])
    left = len(list_in) - n * max_len
    if left > 0:
        res.append(list_in[-left:])
    assert sum([len(x) for x in res]) == len(list_in)
    return res
