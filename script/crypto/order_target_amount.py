#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Binance合约交易测试脚本
简单演示如何使用BinanceEngine在测试网上进行U本位合约交易
"""

import time
import sys
import os
from datetime import datetime
import requests
import urllib.parse
import hmac
import hashlib
import json
# 添加项目根目录到系统路径
root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
if root_path not in sys.path:
    sys.path.append(root_path)
from futurx_crypto.binance_trader_engine import BinanceTraderEngine
from core.engine.main_engine import MainEngine

test_api_key = "c3be109e8eb4be673f69b2bced4be0494efe24bb45ee31aae152c44c60ffdbd8"
test_secret_key = "20beaf4892d63ae8fa58fe3b3d5e49030f428859567a64449bfb42fa5465165a"

# 示例：如何在程序中直接使用
trader = BinanceTraderEngine()
trader.init_client(test_api_key, test_secret_key, use_testnet=True)

# 目标金额模式
trader.order_target_amount("BTCUSDT", 100, 50, "MARKET")

# 传统模式
# trader.order_by_margin("BTCUSDT", 100, 10, "BUY", "MARKET")

# # 设置杠杆和保证金类型
# # leverage_result = trader.set_leverage("BTCUSDT", 5)
# # print(f"设置杠杆倍数结果: {leverage_result}")

# # margin_result = trader.set_margin_type("BTCUSDT", "ISOLATED")
# # print(f"设置保证金类型结果: {margin_result}")

# # 获取当前价格
# price = trader.get_ticker_price("BTCUSDT")
# print(f"当前BTCUSDT价格: {price}")

# # 获取交易对精度信息
# price_precision, quantity_precision = trader.get_symbol_precision("BTCUSDT")
# print(f"价格精度: {price_precision}, 数量精度: {quantity_precision}")




