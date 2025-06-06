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


main_engine = MainEngine()
event_engine = main_engine.event_engine

trader = BinanceTraderEngine(main_engine, event_engine)
trader.init_client(
    api_key=test_api_key, 
    api_secret=test_secret_key, 
    use_testnet=True,
    simulate_trading=False
)

# 设置杠杆和保证金类型
leverage_result = trader.set_leverage("BTCUSDT", 5)
print(f"设置杠杆倍数结果: {leverage_result}")

margin_result = trader.set_margin_type("BTCUSDT", "ISOLATED")
print(f"设置保证金类型结果: {margin_result}")

# 获取当前价格
price = trader.get_ticker_price("BTCUSDT")
print(f"当前BTCUSDT价格: {price}")

# 获取交易对精度信息
price_precision, quantity_precision = trader.get_symbol_precision("BTCUSDT")
print(f"价格精度: {price_precision}, 数量精度: {quantity_precision}")

# 计算满足最小名义价值100 USDT的数量
limit_price = round(price * 0.95, price_precision)  # 比当前价格低5%
min_notional = 100  # 最小名义价值要求(Binance规定)
min_quantity = min_notional / limit_price  # 计算满足最小名义价值的数量
quantity = round(max(min_quantity, 0.001), quantity_precision)  # 确保数量足够大

# 检查名义价值是否满足要求
notional_value = limit_price * quantity
if notional_value < min_notional:
    # 增加数量以满足最小名义价值要求
    quantity = round(min_notional / limit_price + 0.001, quantity_precision)
    notional_value = limit_price * quantity

print(f"下单价格: {limit_price}, 下单数量: {quantity}, 名义价值: {round(notional_value, 2)} USDT")

# 下限价单
result = trader.place_order(
    symbol="BTCUSDT",
    side="BUY",
    order_type="LIMIT",
    quantity=quantity,
    price=limit_price
)

print(f"下单结果: {result}")

# 检查下单是否成功
if 'error' in result:
    print(f"下单失败: {result['error']}")
else:
    # 如果下单成功并且返回了订单ID，则尝试撤单
    if 'orderId' in result:
        order_id = result["orderId"]
        print(f"订单ID: {order_id}")
        
        # 撤单
        cancel_result = trader.cancel_order("BTCUSDT", order_id)
        print(f"撤单结果: {cancel_result}")
    else:
        print("下单可能成功但未返回订单ID")

print("测试完成")

