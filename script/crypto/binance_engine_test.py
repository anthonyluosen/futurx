#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Binance数据引擎测试脚本
测试Binance数据引擎的订阅功能
"""

import time
import sys
import os
from datetime import datetime

# 添加项目根目录到系统路径
root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
if root_path not in sys.path:
    sys.path.append(root_path)

from core.engine.main_engine import MainEngine
from futurx_crypto.binance_engine import BinanceEngine
from core.constant import EventType, Event

def on_tick(event: Event):
    """处理Tick数据事件"""
    tick = event.data
    # print(tick)
    print(f"收到Tick数据: {tick.symbol}, 价格: {tick.last_price}, 数量: {tick.last_volume}, 时间: {tick.datetime}")

def on_bar(event: Event):
    """处理K线数据事件"""
    bar = event.data
    print(f"收到K线数据: {bar.symbol}, 周期: {bar.interval}, 开: {bar.open_price}, 高: {bar.high_price}, 低: {bar.low_price}, 收: {bar.close_price}, 时间: {bar.datetime}")

def main():
    """主函数"""
    print("开始测试Binance数据引擎...")
    
    # 创建主引擎
    main_engine = MainEngine()
    
    # 创建Binance数据引擎
    binance_engine = BinanceEngine(main_engine, main_engine.event_engine)
    
    # 添加Binance数据引擎到主引擎
    main_engine.add_component(EngineType.DATA, binance_engine, "binance")
    
    # 注册事件处理函数
    # main_engine.event_engine.register(EventType.TICK, on_tick)
    main_engine.event_engine.register(EventType.BAR1MIN, on_bar)
    # main_engine.event_engine.register(EventType.BAR5MIN, on_bar)
    # main_engine.event_engine.register(EventType.BAR15MIN, on_bar)
    # main_engine.event_engine.register(EventType.BAR30MIN, on_bar)
    # main_engine.event_engine.register(EventType.BAR1HOUR, on_bar)
    # main_engine.event_engine.register(EventType.BAR4HOUR, on_bar)
    
    # 连接Binance
    binance_engine.connect()
    
    # 订阅交易对
    symbol = 'btcusdt'  # 比特币/USDT
    
    # 订阅逐笔交易数据
    binance_engine.subscribe_tick(symbol)
    
    # 订阅不同周期的K线数据
    binance_engine.subscribe_futures_kline(symbol, '1m')  # 1分钟K线
    # binance_engine.subscribe_kline(symbol, '5m')  # 5分钟K线
    # binance_engine.subscribe_kline(symbol, '15m')  # 15分钟K线
    # binance_engine.subscribe_kline(symbol, '30m')  # 30分钟K线
    # binance_engine.subscribe_kline(symbol, '1h')  # 1小时K线
    # binance_engine.subscribe_kline(symbol, '4h')  # 4小时K线



    # binance_engine.subscribe_futures_kline(symbol, '1m')  # 15分钟K线

    print(f"已订阅 {symbol.upper()} 的逐笔交易数据和K线数据")
    print("正在接收数据，按Ctrl+C退出...")
    
    try:
        # 持续运行一段时间
        count = 0
        max_count = 60  # 最多运行60秒
        while count < max_count:
            time.sleep(1)
            count += 1
    except KeyboardInterrupt:
        print("\n用户中断，正在退出...")
    finally:
        # 关闭引擎
        main_engine.close()
        print("测试结束")

if __name__ == "__main__":
    main() 