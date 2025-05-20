#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
基于保证金金额的Binance合约下单脚本
根据指定的保证金金额(USDT)和杠杆倍数计算并下单
用法示例：
python order_by_margin.py BTCUSDT 100 10 BUY
表示用100USDT保证金，10倍杠杆，做多BTCUSDT

python order_by_margin.py --target BTCUSDT 100 10
表示调整BTCUSDT仓位到100USDT保证金(10倍杠杆)，正数做多负数做空
"""

import time
import sys
import os
import math
from datetime import datetime
import argparse

# 添加项目根目录到系统路径
root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
if root_path not in sys.path:
    sys.path.append(root_path)
    
from futurx_crypto.binance_trader_engine import BinanceTraderEngine

def order_by_margin(symbol, margin, leverage, side, order_type="MARKET", test_mode=True):
    """
    根据保证金金额下单
    
    Args:
        symbol: 交易对，如 "BTCUSDT"
        margin: 保证金金额(USDT)，正数表示做多，负数表示做空
        leverage: 杠杆倍数，范围1-125，根据具体交易对不同而不同
        side: 方向，"BUY"或"SELL"
        order_type: 订单类型，"MARKET"或"LIMIT"
        test_mode: 是否使用测试网
        
    Returns:
        Dict: 下单结果
    """
    # 初始化交易引擎
    trader = BinanceTraderEngine()
    
    # 根据测试模式使用不同的API密钥
    if test_mode:
        api_key = "c3be109e8eb4be673f69b2bced4be0494efe24bb45ee31aae152c44c60ffdbd8"
        api_secret = "20beaf4892d63ae8fa58fe3b3d5e49030f428859567a64449bfb42fa5465165a"
        trader.init_client(
            api_key=api_key,
            api_secret=api_secret,
            use_testnet=True,
            simulate_trading=False
        )
    else:
        # 实盘模式下，需要设置实际的API密钥
        api_key = os.environ.get("BINANCE_API_KEY", "")
        api_secret = os.environ.get("BINANCE_API_SECRET", "")
        
        if not api_key or not api_secret:
            print("错误: 实盘模式需要设置BINANCE_API_KEY和BINANCE_API_SECRET环境变量")
            return {'error': '未设置API密钥'}
            
        trader.init_client(
            api_key=api_key,
            api_secret=api_secret,
            use_testnet=False,
            simulate_trading=False
        )
    
    # 获取交易对信息
    symbol_info = trader.get_symbol_info(symbol)
    if not symbol_info:
        return {'error': f'获取{symbol}信息失败'}
    
    # 获取交易对价格
    price = trader.get_ticker_price(symbol)
    if price <= 0:
        return {'error': f'获取{symbol}价格失败'}
    
    print(f"当前{symbol}价格: {price}")
    
    # 设置杠杆
    leverage_result = trader.set_leverage(symbol, leverage)
    print(f"设置杠杆倍数结果: {leverage_result}")
    
    # 设置保证金类型为逐仓
    margin_result = trader.set_margin_type(symbol, "ISOLATED")
    print(f"设置保证金类型结果: {margin_result}")
    
    # 计算合约数量
    # 合约数量 = 保证金金额 * 杠杆倍数 / 价格
    abs_margin = abs(margin)  # 取保证金绝对值
    contract_amount = (abs_margin * leverage) / price
    
    # 币安的最小名义价值要求通常是5-10 USDT
    min_notional = 5.0
    
    # 检查名义价值是否满足最小要求
    notional_value = contract_amount * price
    if notional_value < min_notional:
        print(f"警告: 计算的名义价值 {notional_value:.2f} USDT 小于最小要求 {min_notional} USDT")
        # 调整合约数量以满足最小名义价值要求
        contract_amount = min_notional / price
        notional_value = contract_amount * price
        print(f"调整后合约数量: {contract_amount}, 名义价值: {notional_value:.2f} USDT")
    
    # 获取数量精度和最小变动单位
    try:
        step_size, quantity_precision = trader.get_lot_size_filter(symbol)
        print(f"获取到{symbol}数量精度: {quantity_precision}, 最小数量变动单位: {step_size}")
        
        # 确保数量符合最小变动单位
        contract_amount = math.floor(contract_amount / step_size) * step_size
    except Exception as e:
        print(f"获取数量精度失败: {e}, 使用默认值")
        # 使用默认值
        if symbol.lower().startswith("btc"):
            quantity_precision = 3
        elif symbol.lower().startswith("eth"):
            quantity_precision = 3
        else:
            quantity_precision = 1
    
    # 四舍五入到指定精度
    contract_amount = round(contract_amount, quantity_precision)
    
    print(f"下单信息:")
    print(f"交易对: {symbol}")
    print(f"方向: {side}")
    print(f"保证金: {abs_margin} USDT")
    print(f"杠杆: {leverage}倍")
    print(f"价格: {price}")
    print(f"合约数量: {contract_amount}")
    print(f"名义价值: {contract_amount * price:.2f} USDT")
    
    # 执行下单
    if order_type == "MARKET":
        result = trader.place_order(
            symbol=symbol,
            side=side,
            order_type="MARKET",
            quantity=contract_amount
        )
    else:
        # 对于限价单，需要提供价格
        # 这里可以设置比当前价格略低/高的价格，视交易策略而定
        price_offset = 0.005  # 价格偏移0.5%
        limit_price = price * (1 - price_offset) if side == "BUY" else price * (1 + price_offset)
        
        # 获取价格精度和最小价格变动单位
        try:
            tick_size, price_precision = trader.get_price_filter(symbol)
            print(f"获取到{symbol}价格精度: {price_precision}, 最小价格变动单位: {tick_size}")
            
            # 确保价格符合最小价格变动单位
            limit_price = math.floor(limit_price / tick_size) * tick_size
        except Exception as e:
            print(f"获取价格精度失败: {e}, 使用默认值")
            # 使用默认值
            if symbol.lower().startswith("btc"):
                price_precision = 1
                tick_size = 0.1
            elif symbol.lower().startswith("eth"):
                price_precision = 2
                tick_size = 0.01
            else:
                price_precision = 2
                tick_size = 0.01
            
            # 处理价格
            limit_price = math.floor(limit_price / tick_size) * tick_size
            
        # 四舍五入到指定精度
        limit_price = round(limit_price, price_precision)
        
        print(f"限价单价格: {limit_price} (精度: {price_precision}, 最小变动单位: {tick_size})")
        
        result = trader.place_order(
            symbol=symbol,
            side=side,
            order_type="LIMIT",
            quantity=contract_amount,
            price=limit_price
        )
    
    print(f"下单结果: {result}")
    return result

def order_target_amount(symbol, target_margin, leverage, order_type="MARKET", test_mode=True):
    """
    根据目标保证金金额调整仓位
    
    Args:
        symbol: 交易对，如 "BTCUSDT"
        target_margin: 目标保证金金额(USDT)，正数表示做多，负数表示做空
        leverage: 杠杆倍数，范围1-125，根据具体交易对不同而不同
        order_type: 订单类型，"MARKET"或"LIMIT"
        test_mode: 是否使用测试网
        
    Returns:
        Dict: 下单结果
    """
    # 初始化交易引擎
    trader = BinanceTraderEngine()
    
    # 根据测试模式使用不同的API密钥
    if test_mode:
        api_key = "c3be109e8eb4be673f69b2bced4be0494efe24bb45ee31aae152c44c60ffdbd8"
        api_secret = "20beaf4892d63ae8fa58fe3b3d5e49030f428859567a64449bfb42fa5465165a"
        trader.init_client(
            api_key=api_key,
            api_secret=api_secret,
            use_testnet=True,
            simulate_trading=False
        )
    else:
        # 实盘模式下，需要设置实际的API密钥
        api_key = os.environ.get("BINANCE_API_KEY", "")
        api_secret = os.environ.get("BINANCE_API_SECRET", "")
        
        if not api_key or not api_secret:
            print("错误: 实盘模式需要设置BINANCE_API_KEY和BINANCE_API_SECRET环境变量")
            return {'error': '未设置API密钥'}
            
        trader.init_client(
            api_key=api_key,
            api_secret=api_secret,
            use_testnet=False,
            simulate_trading=False
        )
    
    # 获取交易对信息
    symbol_info = trader.get_symbol_info(symbol)
    if not symbol_info:
        return {'error': f'获取{symbol}信息失败'}
    
    # 获取交易对价格
    price = trader.get_ticker_price(symbol)
    if price <= 0:
        return {'error': f'获取{symbol}价格失败'}
    
    print(f"当前{symbol}价格: {price}")
    
    # 设置杠杆
    leverage_result = trader.set_leverage(symbol, leverage)
    print(f"设置杠杆倍数结果: {leverage_result}")
    
    # 设置保证金类型为逐仓
    margin_result = trader.set_margin_type(symbol, "ISOLATED")
    print(f"设置保证金类型结果: {margin_result}")
    
    # 获取当前持仓
    positions = trader.get_positions(symbol)
    # 查找当前持仓
    current_position = 0.0
    for pos in positions:
        if pos.get('symbol') == symbol.upper():
            current_position = float(pos.get('positionAmt', 0))
            break
    
    print(f"当前持仓数量: {current_position}")
    
    # 计算目标持仓数量
    # 目标持仓数量 = 目标保证金金额 * 杠杆倍数 / 价格
    # 如果目标保证金为负，表示做空
    target_position = (target_margin * leverage) / price
    
    print(f"目标持仓数量: {target_position}")
    
    # 计算需要调整的数量
    position_diff = target_position - current_position
    
    # 如果差额很小，不做调整
    precision = 5
    if abs(position_diff) < 10**(-precision):
        print("当前持仓已经接近目标持仓，无需调整")
        return {
            'status': 'NO_CHANGE',
            'message': '当前持仓已经接近目标持仓，无需调整',
            'current_position': current_position,
            'target_position': target_position,
            'position_diff': position_diff
        }
    
    # 确定交易方向
    side = "BUY" if position_diff > 0 else "SELL"
    
    # 计算需要调整的合约数量
    contract_amount = abs(position_diff)
    
    # 币安的最小名义价值要求通常是5-10 USDT
    min_notional = 5.0
    
    # 检查名义价值是否满足最小要求
    notional_value = contract_amount * price
    if notional_value < min_notional:
        print(f"警告: 计算的调整名义价值 {notional_value:.2f} USDT 小于最小要求 {min_notional} USDT")
        # 如果调整量太小，考虑是否要强制调整
        if abs(position_diff) < (min_notional / price / leverage):
            print("调整量太小，无法满足最小交易要求，跳过调整")
            return {
                'status': 'TOO_SMALL',
                'message': '调整量太小，无法满足最小交易要求',
                'current_position': current_position,
                'target_position': target_position,
                'position_diff': position_diff,
                'min_required_diff': min_notional / price / leverage
            }
        # 调整合约数量以满足最小名义价值要求
        contract_amount = min_notional / price
        notional_value = contract_amount * price
        print(f"调整后合约数量: {contract_amount}, 名义价值: {notional_value:.2f} USDT")
    
    # 获取数量精度和最小变动单位
    try:
        step_size, quantity_precision = trader.get_lot_size_filter(symbol)
        print(f"获取到{symbol}数量精度: {quantity_precision}, 最小数量变动单位: {step_size}")
        
        # 确保数量符合最小变动单位
        contract_amount = math.floor(contract_amount / step_size) * step_size
    except Exception as e:
        print(f"获取数量精度失败: {e}, 使用默认值")
        # 使用默认值
        if symbol.lower().startswith("btc"):
            quantity_precision = 3
        elif symbol.lower().startswith("eth"):
            quantity_precision = 3
        else:
            quantity_precision = 1
    
    # 四舍五入到指定精度
    contract_amount = round(contract_amount, quantity_precision)
    
    print(f"下单信息:")
    print(f"交易对: {symbol}")
    print(f"方向: {side}")
    print(f"当前持仓: {current_position}")
    print(f"目标持仓: {target_position}")
    print(f"调整数量: {contract_amount}")
    print(f"杠杆: {leverage}倍")
    print(f"价格: {price}")
    print(f"名义价值: {contract_amount * price:.2f} USDT")
    
    # 执行下单
    if order_type == "MARKET":
        result = trader.place_order(
            symbol=symbol,
            side=side,
            order_type="MARKET",
            quantity=contract_amount
        )
    else:
        # 对于限价单，需要提供价格
        # 这里可以设置比当前价格略低/高的价格，视交易策略而定
        price_offset = 0.005  # 价格偏移0.5%
        limit_price = price * (1 - price_offset) if side == "BUY" else price * (1 + price_offset)
        
        # 获取价格精度和最小价格变动单位
        try:
            tick_size, price_precision = trader.get_price_filter(symbol)
            print(f"获取到{symbol}价格精度: {price_precision}, 最小价格变动单位: {tick_size}")
            
            # 确保价格符合最小价格变动单位
            limit_price = math.floor(limit_price / tick_size) * tick_size
        except Exception as e:
            print(f"获取价格精度失败: {e}, 使用默认值")
            # 使用默认值
            if symbol.lower().startswith("btc"):
                price_precision = 1
                tick_size = 0.1
            elif symbol.lower().startswith("eth"):
                price_precision = 2
                tick_size = 0.01
            else:
                price_precision = 2
                tick_size = 0.01
            
            # 处理价格
            limit_price = math.floor(limit_price / tick_size) * tick_size
            
        # 四舍五入到指定精度
        limit_price = round(limit_price, price_precision)
        
        print(f"限价单价格: {limit_price} (精度: {price_precision}, 最小变动单位: {tick_size})")
        
        result = trader.place_order(
            symbol=symbol,
            side=side,
            order_type="LIMIT",
            quantity=contract_amount,
            price=limit_price
        )
    
    # 添加调整信息到结果
    if isinstance(result, dict) and 'error' not in result:
        result.update({
            'current_position': current_position,
            'target_position': target_position,
            'position_diff': position_diff,
            'adjusted_amount': contract_amount,
            'leverage': leverage,
            'target_margin': target_margin
        })
    
    print(f"下单结果: {result}")
    return result

if __name__ == "__main__":
    # 创建命令行参数解析器
    parser = argparse.ArgumentParser(description='基于保证金金额的Binance合约下单工具')
    parser.add_argument('--target', action='store_true', help='使用目标金额模式，自动调整仓位')
    parser.add_argument('symbol', type=str, default= "btcusdt",help='交易对，如BTCUSDT')
    parser.add_argument('margin', type=float,default=5, help='保证金金额(USDT)，正数为做多，负数为做空')
    parser.add_argument('leverage', type=int,default=20, help='杠杆倍数，范围1-125')
    parser.add_argument('--side', type=str, choices=['BUY', 'SELL'], help='交易方向，只在非target模式下使用')
    parser.add_argument('--type', type=str, default='MARKET', choices=['MARKET', 'LIMIT'], help='订单类型，默认为MARKET')
    parser.add_argument('--test', type=bool, default=True, help='是否使用测试网，默认为True')
    
    # 解析命令行参数
    args = parser.parse_args()
    
    # 初始化交易引擎
    trader = BinanceTraderEngine()
    
    # 根据测试模式使用不同的API密钥
    if args.test:
        api_key = "c3be109e8eb4be673f69b2bced4be0494efe24bb45ee31aae152c44c60ffdbd8"
        api_secret = "20beaf4892d63ae8fa58fe3b3d5e49030f428859567a64449bfb42fa5465165a"
        trader.init_client(
            api_key=api_key,
            api_secret=api_secret,
            use_testnet=True,
            simulate_trading=False
        )
    else:
        # 实盘模式下，需要设置实际的API密钥
        api_key = os.environ.get("BINANCE_API_KEY", "")
        api_secret = os.environ.get("BINANCE_API_SECRET", "")
        
        if not api_key or not api_secret:
            print("错误: 实盘模式需要设置BINANCE_API_KEY和BINANCE_API_SECRET环境变量")
            sys.exit(1)
            
        trader.init_client(
            api_key=api_key,
            api_secret=api_secret,
            use_testnet=False,
            simulate_trading=False
        )
    
    if args.target:
        # 目标金额模式
        print(f"使用目标金额模式，调整{args.symbol}仓位到{args.margin} USDT保证金({args.leverage}倍杠杆)")
        result = trader.order_target_amount(
            symbol=args.symbol,
            target_margin=args.margin,
            leverage=args.leverage,
            order_type=args.type
        )
    else:
        # 传统模式
        if not args.side:
            print("错误: 非target模式下必须指定交易方向(--side)")
            sys.exit(1)
            
        print(f"使用传统模式，{args.side} {args.symbol} 使用{args.margin} USDT保证金({args.leverage}倍杠杆)")
        result = trader.order_by_margin(
            symbol=args.symbol,
            margin=args.margin,
            leverage=args.leverage,
            side=args.side,
            order_type=args.type
        ) 