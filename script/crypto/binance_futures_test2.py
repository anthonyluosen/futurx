#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Binance合约交易测试脚本
用于测试SOLUSDT的交易
"""

import time
import sys
import os
from datetime import datetime
import json
import math
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

def format_price_quantity(trader, symbol, action_type, price=None, quantity=None):
    """
    严格格式化价格和数量以符合交易所规则
    
    Args:
        trader: 交易引擎实例
        symbol: 交易对名称
        action_type: 'BUY' 或 'SELL'
        price: 价格，如果不提供则获取市场价
        quantity: 数量，可选
        
    Returns:
        (formatted_price, formatted_quantity): 格式化后的价格和数量
    """
    symbol_info = trader.get_symbol_info(symbol)
    if not symbol_info or 'filters' not in symbol_info:
        print(f"无法获取{symbol}的交易规则")
        return None, None
    
    # 价格精度和步长
    price_precision = 8  # 默认值
    price_step = 0.1     # 默认值
    
    # 数量精度和步长
    qty_precision = 8    # 默认值
    qty_step = 0.001     # 默认值
    
    # 最小名义价值
    min_notional = 5.0   # 默认值
    
    # 从交易所规则中解析精度要求
    for filter_item in symbol_info['filters']:
        if filter_item['filterType'] == 'PRICE_FILTER':
            price_step = float(filter_item['tickSize'])
            # 计算精度(小数点后的位数)
            price_precision = len(str(price_step).split('.')[-1].rstrip('0')) if '.' in str(price_step) else 0
        
        elif filter_item['filterType'] == 'LOT_SIZE':
            qty_step = float(filter_item['stepSize'])
            # 计算精度
            qty_precision = len(str(qty_step).split('.')[-1].rstrip('0')) if '.' in str(qty_step) else 0
            
        elif filter_item['filterType'] == 'MIN_NOTIONAL':
            min_notional = float(filter_item.get('notional', 5.0))
    
    # 如果没有提供价格，获取当前市场价
    if price is None:
        ticker = trader.get_ticker_price(symbol)
        price = ticker
    
    # 格式化价格 - 使用字符串格式确保精度准确
    step_decimals = str(price_step).split('.')[-1].count('0') + 1 if '.' in str(price_step) else 0
    price_format = f"{{:.{price_precision}f}}"
    
    # 向上/向下取整到最接近的步长倍数
    price_in_steps = price / price_step
    if action_type == 'BUY':
        # 买入时向上取整确保价格足够高
        price_in_steps = math.ceil(price_in_steps)
    else:
        # 卖出时向下取整确保价格足够低
        price_in_steps = math.floor(price_in_steps)
    
    formatted_price = price_in_steps * price_step
    # 使用字符串格式化确保精度准确
    formatted_price_str = price_format.format(formatted_price)
    
    # 如果提供了数量，格式化数量
    formatted_qty_str = None
    if quantity is not None:
        qty_format = f"{{:.{qty_precision}f}}"
        qty_in_steps = math.floor(quantity / qty_step) * qty_step  # 向下取整到步长倍数
        formatted_qty = max(qty_in_steps, qty_step)  # 确保不小于最小步长
        formatted_qty_str = qty_format.format(formatted_qty)
        
        # 检查名义价值是否满足最小要求
        notional = float(formatted_price_str) * float(formatted_qty_str)
        if notional < min_notional:
            # 调整数量以满足最小名义价值
            min_qty = math.ceil(min_notional / float(formatted_price_str) / qty_step) * qty_step
            formatted_qty_str = qty_format.format(min_qty)
    
    return formatted_price_str, formatted_qty_str

# 选择测试模式
print("\n请选择测试模式:")
print("1. 使用保证金值设置仓位")
print("2. 使用具体数量设置仓位")
print("3. 使用自定义order_factor设置保证金值")
print("4. 使用模拟order_factor设置保证金值(最准确)")
mode = input("请输入选择 (1/2/3/4): ")

# 针对SOLUSDT进行测试
symbol = "SOLUSDT"
print(f"\n===== 测试 {symbol} =====")

# 设置杠杆和保证金模式
leverage = 5  # 默认5倍杠杆
leverage_result = trader.set_leverage(symbol, leverage)  # 设置5倍杠杆
print(f"设置杠杆结果: {leverage_result}")

margin_result = trader.set_margin_type(symbol, "ISOLATED")  # 设置逐仓模式
print(f"设置保证金模式结果: {margin_result}")

# 获取交易对精度信息
symbol_info = trader.get_symbol_info(symbol)
print(f"交易对信息摘要:")
if 'filters' in symbol_info:
    for filter_item in symbol_info['filters']:
        if filter_item['filterType'] in ['PRICE_FILTER', 'LOT_SIZE', 'MIN_NOTIONAL']:
            print(f"{filter_item['filterType']}: {filter_item}")

# 获取当前持仓和价格
position = trader.get_position_amount(symbol)
current_price = trader.get_ticker_price(symbol)
current_value = position * current_price
print(f"当前持仓: {position} SOL")
print(f"当前价格: {current_price} USDT")
print(f"当前持仓价值: {current_value} USDT")
print(f"当前保证金估计: {current_value / leverage} USDT")

if mode == "1":
    # 模式1: 使用保证金值设置仓位
    print("\n===== 使用保证金值设置仓位 =====")
    
    target_margin = float(input("请输入目标保证金值(USDT): "))
    direction = input("请输入仓位方向 (long/short): ").lower()
    
    # 确保方向正确
    if direction not in ["long", "short"]:
        print("方向输入错误，必须是'long'或'short'")
        exit()
    
    # 计算目标价值和仓位差额
    target_value = target_margin * leverage  # 根据杠杆计算仓位价值
    if direction == "short":
        target_value = -target_value  # 如果是做空，目标价值为负
    
    # 计算需要调整的价值
    value_diff = target_value - current_value
    if abs(value_diff) < 1:
        print("当前持仓已经接近目标值，无需调整")
        exit()
    
    # 确定买卖方向
    if value_diff > 0:
        side = "BUY"
        print(f"需要买入价值 {value_diff} USDT 的 {symbol}")
    else:
        side = "SELL"
        value_diff = -value_diff  # 转为正数
        print(f"需要卖出价值 {value_diff} USDT 的 {symbol}")
    
    # 获取订单簿
    orderbook = trader.get_orderbook(symbol)
    if 'error' in orderbook:
        print(f"获取订单簿失败: {orderbook['error']}")
        exit()
    
    # 根据方向获取合适的价格
    if side == "BUY":
        price = float(orderbook['asks'][0][0])  # 卖一价
        print(f"使用卖一价: {price}")
    else:
        price = float(orderbook['bids'][0][0])  # 买一价
        print(f"使用买一价: {price}")
    
    # 计算并格式化价格和数量
    formatted_price, _ = format_price_quantity(trader, symbol, side, price)
    quantity = value_diff / float(formatted_price)
    _, formatted_qty = format_price_quantity(trader, symbol, side, float(formatted_price), quantity)
    
    print(f"\n下单信息:")
    print(f"交易对: {symbol}")
    print(f"方向: {side}")
    print(f"价格: {formatted_price}")
    print(f"数量: {formatted_qty}")
    print(f"名义价值: {float(formatted_price) * float(formatted_qty)} USDT")
    print(f"预计保证金: {float(formatted_price) * float(formatted_qty) / leverage} USDT")
    
    # 确认是否下单
    confirm = input("\n确认下单吗？(y/n): ")
    if confirm.lower() != 'y':
        print("取消下单")
        exit()
    
    # 下单
    order_result = trader.place_order(
        symbol=symbol,
        side=side,
        order_type="LIMIT",
        quantity=float(formatted_qty),
        price=float(formatted_price)
    )
    
    print(f"\n下单结果: {json.dumps(order_result, indent=2)}")
    result = order_result  # 用于后续处理

elif mode == "2":
    # 模式2: 使用具体数量设置仓位
    print("\n===== 使用具体数量设置仓位 =====")
    
    # 输入具体的目标数量
    target_position = float(input("请输入目标持仓数量(正数为多头,负数为空头): "))
    
    # 计算需要调整的数量
    qty_diff = target_position - position
    if abs(qty_diff) < 0.001:
        print("当前持仓已经接近目标数量，无需调整")
        exit()
    
    # 确定买卖方向
    if qty_diff > 0:
        side = "BUY"
        quantity = qty_diff
        print(f"需要买入 {quantity} 个 {symbol}")
    else:
        side = "SELL"
        quantity = -qty_diff  # 转为正数
        print(f"需要卖出 {quantity} 个 {symbol}")
    
    # 获取订单簿
    orderbook = trader.get_orderbook(symbol)
    if 'error' in orderbook:
        print(f"获取订单簿失败: {orderbook['error']}")
        exit()
    
    # 根据方向获取合适的价格
    if side == "BUY":
        price = float(orderbook['asks'][0][0])  # 卖一价
        print(f"使用卖一价: {price}")
    else:
        price = float(orderbook['bids'][0][0])  # 买一价
        print(f"使用买一价: {price}")
    
    # 格式化价格和数量
    formatted_price, formatted_qty = format_price_quantity(trader, symbol, side, price, quantity)
    
    print(f"\n下单信息:")
    print(f"交易对: {symbol}")
    print(f"方向: {side}")
    print(f"价格: {formatted_price}")
    print(f"数量: {formatted_qty}")
    print(f"名义价值: {float(formatted_price) * float(formatted_qty)} USDT")
    print(f"预计保证金: {float(formatted_price) * float(formatted_qty) / leverage} USDT")
    
    # 确认是否下单
    confirm = input("\n确认下单吗？(y/n): ")
    if confirm.lower() != 'y':
        print("取消下单")
        exit()
    
    # 下单
    order_result = trader.place_order(
        symbol=symbol,
        side=side,
        order_type="LIMIT",
        quantity=float(formatted_qty),
        price=float(formatted_price)
    )
    
    print(f"\n下单结果: {json.dumps(order_result, indent=2)}")
    result = order_result  # 用于后续处理

elif mode == "3":
    # 模式3: 使用原生order_factor方法
    print("\n===== 使用order_factor方法 =====")
    
    # 输入factor值(即目标保证金值)和方向
    target_margin = float(input("请输入目标保证金值(USDT): "))
    direction = input("请输入仓位方向 (long/short): ").lower()
    
    # 确保方向正确
    if direction not in ["long", "short"]:
        print("方向输入错误，必须是'long'或'short'")
        exit()
    
    # 计算目标市值 (factor * multiplier = 总市值)
    # 为了得到正确的保证金值，我们应该:
    # - 设置factor为margin / multiplier
    # - 设置multiplier为leverage
    # 这样 factor * multiplier = margin * leverage = 总市值
    factor = target_margin / leverage
    multiplier = leverage
    
    # 如果是做空,将factor设为负数
    if direction == "short":
        factor = -factor
    
    # 计算预期持仓价值
    expected_value = factor * multiplier  # factor * multiplier = 总市值
    expected_direction = "多头" if expected_value > 0 else "空头"
    
    print(f"预期持仓方向: {expected_direction}")
    print(f"预期总持仓市值: {abs(expected_value)} USDT")
    print(f"预期保证金: {target_margin} USDT")
    
    # 获取订单簿以获取准确价格
    orderbook = trader.get_orderbook(symbol)
    if 'error' in orderbook:
        print(f"获取订单簿失败: {orderbook['error']}")
        exit()
    
    # 根据仓位方向获取合适的价格
    if direction == "long":  # 做多
        price = float(orderbook['asks'][0][0])  # 卖一价
        print(f"做多 - 使用卖一价: {price}")
        action_type = "BUY"
    else:  # 做空
        price = float(orderbook['bids'][0][0])  # 买一价
        print(f"做空 - 使用买一价: {price}")
        action_type = "SELL"
    
    # 格式化价格
    formatted_price, _ = format_price_quantity(trader, symbol, action_type, price)
    price = float(formatted_price)
    
    print(f"\norder_factor参数:")
    print(f"交易对: {symbol}")
    print(f"factor: {factor}")  # factor = 保证金 / 杠杆
    print(f"multiplier: {multiplier}")  # multiplier = 杠杆
    print(f"order_type: LIMIT")
    print(f"price: {price}")
    
    # 确认是否执行
    confirm = input("\n确认使用order_factor吗？(y/n): ")
    if confirm.lower() != 'y':
        print("取消操作")
        exit()
    
    # 使用order_factor方法
    result = trader.order_factor(
        symbol=symbol,
        factor=factor,
        multiplier=float(multiplier),
        order_type="LIMIT",
        price=price
    )
    
    print(f"\norder_factor结果: {json.dumps(result, indent=2)}")

else:
    # 模式4: 模拟order_factor方法但正确处理保证金
    print("\n===== 模拟order_factor设置保证金值(最准确) =====")
    
    # 输入保证金值和方向
    target_margin = float(input("请输入目标保证金值(USDT): "))
    direction = input("请输入仓位方向 (long/short): ").lower()
    
    # 确保方向正确
    if direction not in ["long", "short"]:
        print("方向输入错误，必须是'long'或'short'")
        exit()
    
    # 计算目标市值
    target_value = target_margin * leverage
    
    # 获取订单簿价格
    orderbook = trader.get_orderbook(symbol)
    if 'error' in orderbook:
        print(f"获取订单簿失败: {orderbook['error']}")
        exit()
    
    # 根据方向获取价格和计算目标数量
    if direction == "long":
        price = float(orderbook['asks'][0][0])  # 卖一价
        side = "BUY"
        # 多头仓位 = 市值 / 价格
        target_position = target_value / price
    else:
        price = float(orderbook['bids'][0][0])  # 买一价
        side = "SELL"
        # 空头仓位 = -市值 / 价格
        target_position = -target_value / price
    
    # 计算需要调整的数量
    position_diff = target_position - position
    
    # 如果差异很小，不进行调整
    if abs(position_diff) < 0.001:
        print("当前持仓已经接近目标数量，无需调整")
        exit()
    
    # 确定实际操作的方向和数量
    if position_diff > 0:
        action_side = "BUY"
        action_qty = position_diff
    else:
        action_side = "SELL"
        action_qty = -position_diff  # 转为正数
    
    # 格式化价格和数量
    formatted_price, _ = format_price_quantity(trader, symbol, action_side, price)
    _, formatted_qty = format_price_quantity(trader, symbol, action_side, float(formatted_price), action_qty)
    
    print(f"\n目标设置:")
    print(f"目标保证金: {target_margin} USDT")
    print(f"目标持仓市值: {target_value} USDT")
    print(f"目标持仓方向: {direction}")
    print(f"目标持仓数量: {target_position} SOL")
    print(f"当前持仓数量: {position} SOL")
    print(f"需要调整数量: {position_diff} SOL")
    
    print(f"\n下单信息:")
    print(f"交易对: {symbol}")
    print(f"方向: {action_side}")
    print(f"价格: {formatted_price}")
    print(f"数量: {formatted_qty}")
    print(f"名义价值: {float(formatted_price) * float(formatted_qty)} USDT")
    print(f"对应保证金: {float(formatted_price) * float(formatted_qty) / leverage} USDT")
    
    # 确认是否下单
    confirm = input("\n确认下单吗？(y/n): ")
    if confirm.lower() != 'y':
        print("取消下单")
        exit()
    
    # 下单
    order_result = trader.place_order(
        symbol=symbol,
        side=action_side,
        order_type="LIMIT",
        quantity=float(formatted_qty),
        price=float(formatted_price)
    )
    
    print(f"\n下单结果: {json.dumps(order_result, indent=2)}")
    result = order_result  # 用于后续处理

# 检查订单结果
if 'orderId' in result:
    print(f"\n订单已提交，订单ID: {result['orderId']}")
    print("等待订单成交...")
    
    # 轮询检查订单状态
    for i in range(10):  # 尝试10次，每次等待1秒
        time.sleep(1)
        order_status = trader.get_order(symbol, result['orderId'])
        status = order_status.get('status', '')
        print(f"订单状态: {status}")
        
        if status == 'FILLED':
            print("订单已成交")
            break
        elif status in ['CANCELED', 'REJECTED', 'EXPIRED']:
            print("订单未成交")
            break
    
    # 再次获取持仓情况
    new_position = trader.get_position_amount(symbol)
    new_price = trader.get_ticker_price(symbol)
    new_value = new_position * new_price
    
    print(f"\n交易后持仓: {new_position} SOL")
    print(f"当前价格: {new_price} USDT")
    print(f"当前持仓价值: {new_value} USDT")
    print(f"估计保证金: {new_value / leverage} USDT")
    
    # 显示变化
    position_change = new_position - position
    value_change = new_value - current_value
    print(f"\n持仓变化: {position_change} SOL")
    print(f"价值变化: {value_change} USDT")
    
    # 显示预期值与实际值比较
    if mode == "3" or mode == "4":
        expected_margin = target_margin
        actual_margin = abs(new_value) / leverage
        
        print(f"\n预期保证金: {expected_margin} USDT")
        print(f"实际保证金: {actual_margin} USDT")
        
        if expected_margin > 0:
            diff_percentage = (actual_margin - expected_margin) / expected_margin * 100
            print(f"保证金差异: {diff_percentage:.2f}%")
            
        if mode == "4":
            expected_position = target_position
            actual_position = new_position
            
            print(f"预期持仓数量: {expected_position} SOL")
            print(f"实际持仓数量: {actual_position} SOL")
            
            if abs(expected_position) > 0.001:
                qty_diff_percentage = (abs(actual_position) - abs(expected_position)) / abs(expected_position) * 100
                print(f"数量差异: {qty_diff_percentage:.2f}%")
else:
    print(f"下单失败: {result.get('error', 'Unknown error')}")

print("\n测试完成") 