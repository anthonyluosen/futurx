#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
强制更新某区间的kline数据，不论该区间是否已经有数据存在
适合数据出错的适合强制覆盖
"""

import os
import sys

# 添加项目根目录到系统路径
root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
if root_path not in sys.path:
    sys.path.append(root_path)


from factor_crypto.binance_rest import *

if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler()]
    )
    # 开始时间
    start_time = '2025-05-16 00:00:00'
    # 结束时间选择最新可得的完整k线
    _, now_comp_time = now_time_to_trade_time()
    end_time = now_comp_time
    for code in tqdm(trade_code_list):
        interval = '15m'
        time_update = [x for x in trade_time_cont if start_time <= x <= end_time]
        display_ls(time_update, code + ':time_update')
        rest_api = BinanceRest()
        rest_api.kline_to_mmap(time_update, code, interval)
