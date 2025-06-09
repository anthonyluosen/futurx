#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
展示如何从mmap中读写指定币种和时间的数据
"""

import time
import sys
import os
from datetime import datetime
import pandas as pd

root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
if root_path not in sys.path:
    sys.path.append(root_path)

from factor_crypto.write_mmap import *

# 显示全部可用币种列表
display_ls(trade_code_list, '币种展示')

# 显示全部可用时间列表
display_ls(trade_time_cont, '时间展示')

# 示例币种，起止时间，示例字段
code = 'BTCUSDT'
time_start = trade_time_cont[0]
time_end = trade_time_cont[10]
field = 'Open'

# 返回某币种某时刻的数值
res = read_mmap(time_start, code, field)

# 返回某币种某区间的数值
res_cont = read_cont_mmap(time_start, time_end, code, field)

# 写入某币种某时刻的数值
write_mmap(time_start, code, field, res)

# 写入某币种某区间的数值
write_cont_mmap(time_start, time_end, code, field, res_cont)
