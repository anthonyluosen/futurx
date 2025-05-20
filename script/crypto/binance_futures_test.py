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

# def testnet_request(method, endpoint, api_key, secret_key, params=None):
#     """
#     向Binance测试网发送请求
    
#     Args:
#         method: HTTP方法 ('GET', 'POST', 'DELETE')
#         endpoint: API端点路径
#         api_key: 测试网API密钥
#         secret_key: 测试网密钥
#         params: 请求参数
    
#     Returns:
#         dict: API响应
#     """
#     # 测试网基础URL
#     base_url = "https://testnet.binancefuture.com"
    
#     # 如果没有参数，创建一个空字典
#     if params is None:
#         params = {}
    
#     # 添加时间戳
#     params['timestamp'] = int(time.time() * 1000)
    
#     # 将参数转换为查询字符串
#     query_string = urllib.parse.urlencode(params)
    
#     # 使用密钥创建签名
#     signature = hmac.new(
#         secret_key.encode('utf-8'),
#         query_string.encode('utf-8'),
#         hashlib.sha256
#     ).hexdigest()
    
#     # 将签名添加到参数中
#     query_string = f"{query_string}&signature={signature}"
    
#     # 设置请求头
#     headers = {
#         'X-MBX-APIKEY': api_key
#     }
    
#     # 构建完整URL
#     url = f"{base_url}{endpoint}"
    
#     # 发送请求
#     if method == 'GET':
#         response = requests.get(f"{url}?{query_string}", headers=headers)
#     elif method == 'POST':
#         response = requests.post(f"{url}?{query_string}", headers=headers)
#     elif method == 'DELETE':
#         response = requests.delete(f"{url}?{query_string}", headers=headers)
#     else:
#         raise ValueError(f"不支持的HTTP方法: {method}")
    
#     # 检查响应
#     if response.status_code == 200:
#         return response.json()
#     else:
#         print(f"API请求失败: {response.status_code} - {response.text}")
#         return {'error': response.text}

# def main():
#     """主函数"""
#     print("开始测试Binance合约TestNet交易...")
    
#     # 设置测试网API密钥（替换为您从测试网获取的密钥）
#     test_api_key = "c3be109e8eb4be673f69b2bced4be0494efe24bb45ee31aae152c44c60ffdbd8"
#     test_secret_key = "20beaf4892d63ae8fa58fe3b3d5e49030f428859567a64449bfb42fa5465165a"
    
#     # 选择一个测试的交易对
#     symbol = 'BTCUSDT'
    
#     # 步骤1: 获取账户信息
#     print("\n获取测试网账户信息:")
#     account_info = testnet_request('GET', '/fapi/v2/account', test_api_key, test_secret_key)
#     if 'error' not in account_info:
#         print(f"账户余额: {account_info.get('totalWalletBalance', 'N/A')} USDT")
#         print(f"可用余额: {account_info.get('availableBalance', 'N/A')} USDT")
#         print(f"未实现盈亏: {account_info.get('totalUnrealizedProfit', 'N/A')} USDT")
    
#     # 步骤2: 查询当前挂单
#     print("\n获取当前测试网挂单:")
#     open_orders = testnet_request('GET', '/fapi/v1/openOrders', test_api_key, test_secret_key)
#     if isinstance(open_orders, list):
#         if open_orders:
#             for order in open_orders:
#                 print(f"订单ID: {order.get('orderId')}")
#                 print(f"交易对: {order.get('symbol')}")
#                 print(f"订单方向: {order.get('side')}")
#                 print(f"订单类型: {order.get('type')}")
#                 print(f"订单价格: {order.get('price')}")
#                 print(f"订单数量: {order.get('origQty')}")
#                 print(f"订单状态: {order.get('status')}")
#         else:
#             print("没有挂单")
    
#     # 步骤3: 设置杠杆倍数
#     print("\n设置杠杆倍数:")
#     leverage_params = {
#         'symbol': symbol,
#         'leverage': 5  # 设置5倍杠杆
#     }
#     leverage_result = testnet_request('POST', '/fapi/v1/leverage', test_api_key, test_secret_key, leverage_params)
#     print(f"杠杆设置结果: {leverage_result}")
    
#     # 步骤4: 设置保证金类型
#     print("\n设置保证金类型:")
#     margin_params = {
#         'symbol': symbol,
#         'marginType': 'ISOLATED'  # 设置为逐仓模式
#     }
#     margin_result = testnet_request('POST', '/fapi/v1/marginType', test_api_key, test_secret_key, margin_params)
#     print(f"保证金类型设置结果: {margin_result}")
    
#     # 获取交易对信息，包括价格精度和数量精度
#     print("\n获取交易对信息:")
#     exchange_info = testnet_request('GET', '/fapi/v1/exchangeInfo', test_api_key, test_secret_key)
    
#     price_precision = 2  # 默认值
#     quantity_precision = 3  # 默认值
    
#     if 'error' not in exchange_info and 'symbols' in exchange_info:
#         for symbol_info in exchange_info['symbols']:
#             if symbol_info['symbol'] == symbol:
#                 # 查找价格过滤器
#                 for filter_info in symbol_info['filters']:
#                     if filter_info['filterType'] == 'PRICE_FILTER':
#                         tick_size = float(filter_info['tickSize'])
#                         # 计算精度 (小数点后的位数)
#                         price_precision = len(str(tick_size).split('.')[-1].rstrip('0'))
#                         print(f"价格精度: {price_precision}, 最小价格变动单位: {tick_size}")
#                     elif filter_info['filterType'] == 'LOT_SIZE':
#                         step_size = float(filter_info['stepSize'])
#                         # 计算精度
#                         quantity_precision = len(str(step_size).split('.')[-1].rstrip('0'))
#                         print(f"数量精度: {quantity_precision}, 最小数量变动单位: {step_size}")
#                 break
    
#     # 步骤5: 下限价买单
#     print("\n测试下限价买单:")
#     # 首先获取当前市场价格作为参考
#     price_ticker = testnet_request('GET', '/fapi/v1/ticker/price', test_api_key, test_secret_key, {'symbol': symbol})
    
#     current_price = float(price_ticker.get('price', 20000))
#     # 设置价格比当前市场价低一定比例，使用正确的价格精度
#     limit_price = round(current_price * 0.95, price_precision)  # 比当前价格低5%
    
#     # 计算满足最小名义价值100的数量
#     min_notional = 100  # 最小名义价值要求
#     min_quantity = min_notional / limit_price  # 计算满足最小名义价值的数量
#     quantity = round(max(min_quantity, 0.001), quantity_precision)  # 确保数量足够大
    
#     # 再次检查名义价值是否满足要求，如果不满足，增加数量
#     notional_value = limit_price * quantity
#     if notional_value < min_notional:
#         # 增加数量以满足最小名义价值要求
#         quantity = round(min_notional / limit_price + 0.001, quantity_precision)
#         notional_value = limit_price * quantity
    
#     print(f"当前价格: {current_price}, 下单价格: {limit_price}, 下单数量: {quantity}, 名义价值: {round(notional_value, 2)} USDT")
    
#     # 尝试下限价单
#     order_params = {
#         'symbol': symbol,
#         'side': 'BUY',
#         'type': 'LIMIT',
#         'timeInForce': 'GTC',
#         'quantity': quantity,
#         'price': limit_price,
#         'recvWindow': 5000  # 接收窗口
#     }
    
#     print("尝试下限价单:")
#     order_result = testnet_request('POST', '/fapi/v1/order', test_api_key, test_secret_key, order_params)
#     print(f"限价单结果: {order_result}")
    
#     # 如果限价单失败，尝试下市价单
#     if 'error' in order_result:
#         print("\n限价单失败，尝试下市价单:")
#         market_order_params = {
#             'symbol': symbol,
#             'side': 'BUY',
#             'type': 'MARKET',
#             'quantity': quantity,
#             'recvWindow': 5000  # 接收窗口
#         }
        
#         order_result = testnet_request('POST', '/fapi/v1/order', test_api_key, test_secret_key, market_order_params)
#         print(f"市价单结果: {order_result}")
    
#     # 如果下单成功，查询订单并取消
#     if 'orderId' in order_result:
#         order_id = order_result['orderId']
        
#         # 查询订单
#         print("\n查询订单:")
#         query_params = {
#             'symbol': symbol,
#             'orderId': order_id
#         }
#         order_info = testnet_request('GET', '/fapi/v1/order', test_api_key, test_secret_key, query_params)
#         print(f"订单信息: {order_info}")
        
#         # 取消订单
#         print("\n取消订单:")
#         cancel_params = {
#             'symbol': symbol,
#             'orderId': order_id
#         }
#         cancel_result = testnet_request('DELETE', '/fapi/v1/order', test_api_key, test_secret_key, cancel_params)
#         print(f"取消订单结果: {cancel_result}")
    
#     print("\n测试完成")

# if __name__ == "__main__":
#     main() 