
"""
Binance数据引擎测试脚本
测试Binance数据引擎的订阅功能
"""

import time
import sys
import os
from datetime import datetime
import pandas as pd

# 添加项目根目录到系统路径
root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
if root_path not in sys.path:
    sys.path.append(root_path)

from core.engine.main_engine import MainEngine
from core.config import position_path,secret_key,api_key
from core.base import TickData, BarData
from futurx_crypto.binance_engine import BinanceEngine
from core.constant import EventType, Event,OrderType,EngineType
from factor_crypto.write_mmap import *
from factor_crypto.calc_fac import calc_fac_byloc, calc_posi
from factor_crypto.binance_rest import BinanceRest
from futurx_crypto.binance_trader_engine import BinanceTraderEngine

import logging


binance_engine = BinanceTraderEngine()
binance_engine.init_client(api_key=api_key,api_secret=secret_key)
symbol = "btcusdt"
orderbook = binance_engine.get_orderbook(symbol, limit=5)

print(orderbook['bids'])
print(orderbook['asks'])