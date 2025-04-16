#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Binance策略示例
展示如何在策略中使用Binance数据引擎
"""

import time
import sys
import os
from datetime import datetime
from typing import Dict, List, Optional

# 添加项目根目录到系统路径
root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
print(root_path)
if root_path not in sys.path:
    sys.path.append(root_path)

from core.engine.main_engine import MainEngine
from futurx_crypto.binance_engine import BinanceEngine
from core.constant import EventType, Event, OrderSide, OrderType, OrderStatus, SecurityType
from core.base import TickData, BarData

class BinanceStrategy:
    """
    Binance策略示例
    展示如何在策略中使用Binance数据引擎
    """
    
    def __init__(self, main_engine: MainEngine, strategy_name: str = "binance_strategy"):
        """
        初始化策略
        
        Args:
            main_engine: 主引擎
            strategy_name: 策略名称
        """
        self.main_engine = main_engine
        self.strategy_name = strategy_name
        
        # 注册事件处理函数
        self.main_engine.event_engine.register(EventType.TICK, self.on_tick)
        self.main_engine.event_engine.register(EventType.BAR1MIN, self.on_bar)
        
        # 订阅的交易对
        self.symbol = 'btcusdt'
        
        # 数据缓存
        self.tick_cache = {}  # 缓存最新的Tick数据
        self.bar_cache = {}   # 缓存最新的K线数据
        
        # 策略参数
        self.ma_period = 20  # 移动平均线周期
        self.bar_data = []   # 存储K线数据用于计算移动平均线
        
        print(f"策略 {strategy_name} 初始化完成")
    
    def on_tick(self, event: Event):
        """
        处理Tick数据事件
        
        Args:
            event: 事件对象
        """
        tick = event.data
        if not isinstance(tick, TickData):
            return
            
        # 更新Tick缓存
        self.tick_cache[tick.symbol] = tick
        
        # 打印Tick数据
        print(f"收到Tick数据: {tick.symbol}, 价格: {tick.last_price}, 数量: {tick.last_volume}, 时间: {tick.datetime}")
        
        # 这里可以添加基于Tick数据的交易逻辑
        # 例如：当价格突破某个阈值时下单
        # if tick.last_price > threshold:
        #     self.buy(tick.symbol, 0.01, tick.last_price)
    
    def on_bar(self, event: Event):
        """
        处理K线数据事件
        
        Args:
            event: 事件对象
        """
        bar = event.data
        if not isinstance(bar, BarData):
            return
            
        # 更新K线缓存
        self.bar_cache[bar.symbol] = bar
        
        # 打印K线数据
        print(f"收到K线数据: {bar.symbol}, 周期: {bar.interval}, 开: {bar.open_price}, 高: {bar.high_price}, 低: {bar.low_price}, 收: {bar.close_price}, 时间: {bar.datetime}")
        
        # 更新K线数据列表
        self.bar_data.append(bar)
        
        # 保持数据量在指定范围内
        if len(self.bar_data) > self.ma_period:
            self.bar_data.pop(0)
        
        # 计算移动平均线
        if len(self.bar_data) == self.ma_period:
            ma = sum(bar.close_price for bar in self.bar_data) / self.ma_period
            print(f"移动平均线: {ma}")
            
            # 简单的交易策略：当收盘价高于移动平均线时买入，低于时卖出
            if bar.close_price > ma:
                print(f"价格高于移动平均线，可以考虑买入")
                # self.buy(bar.symbol, 0.01, bar.close_price)
            elif bar.close_price < ma:
                print(f"价格低于移动平均线，可以考虑卖出")
                # self.sell(bar.symbol, 0.01, bar.close_price)
    
    def buy(self, symbol: str, volume: float, price: float):
        """
        买入
        
        Args:
            symbol: 交易对
            volume: 数量
            price: 价格
        """
        # 创建订单
        from core.constant import Order
        order = Order(
            order_id=None,
            symbol=symbol,
            direction=OrderSide.BUY,
            price=price,
            volume=volume,
            status=OrderStatus.SUBMITTING,
            create_time=datetime.now(),
            trader_platform="binance",
            order_type=OrderType.LIMIT,
            security_type=SecurityType.CRYPTO,
            strategy_name=self.strategy_name
        )
        
        # 提交订单
        success = self.main_engine.place_order(order)
        if success:
            print(f"买入订单提交成功: {symbol}, 数量: {volume}, 价格: {price}")
        else:
            print(f"买入订单提交失败: {symbol}, 数量: {volume}, 价格: {price}")
    
    def sell(self, symbol: str, volume: float, price: float):
        """
        卖出
        
        Args:
            symbol: 交易对
            volume: 数量
            price: 价格
        """
        # 创建订单
        from core.constant import Order
        order = Order(
            order_id=None,
            symbol=symbol,
            direction=OrderSide.SELL,
            price=price,
            volume=volume,
            status=OrderStatus.SUBMITTING,
            create_time=datetime.now(),
            trader_platform="binance",
            order_type=OrderType.LIMIT,
            security_type=SecurityType.CRYPTO,
            strategy_name=self.strategy_name
        )
        
        # 提交订单
        success = self.main_engine.place_order(order)
        if success:
            print(f"卖出订单提交成功: {symbol}, 数量: {volume}, 价格: {price}")
        else:
            print(f"卖出订单提交失败: {symbol}, 数量: {volume}, 价格: {price}")

def main():
    """主函数"""
    print("开始运行Binance策略示例...")
    
    # 创建主引擎
    main_engine = MainEngine()
    
    # 创建Binance数据引擎
    binance_engine = BinanceEngine(main_engine, main_engine.event_engine)
    
    # 添加Binance数据引擎到主引擎
    main_engine.add_component("data", binance_engine, "binance")
    
    # 创建策略
    strategy = BinanceStrategy(main_engine)
    
    # 连接Binance
    binance_engine.connect()
    
    # 订阅交易对
    symbol = 'btcusdt'  # 比特币/USDT
    
    # 订阅逐笔交易数据
    binance_engine.subscribe_tick(symbol)
    
    # 订阅1分钟K线数据
    binance_engine.subscribe_kline(symbol, '1m')
    
    print(f"已订阅 {symbol.upper()} 的逐笔交易数据和1分钟K线数据")
    print("正在接收数据，按Ctrl+C退出...")
    
    try:
        # 持续运行一段时间
        count = 0
        max_count = 120  # 最多运行120秒
        while count < max_count:
            time.sleep(1)
            count += 1
    except KeyboardInterrupt:
        print("\n用户中断，正在退出...")
    finally:
        # 关闭引擎
        main_engine.close()
        print("策略示例结束")

if __name__ == "__main__":
    main() 