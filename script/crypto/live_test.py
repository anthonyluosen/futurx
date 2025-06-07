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

logging.basicConfig(
    level=logging.INFO,
    format='%(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)


class BinanceStrategy:
    """
    Binance策略示例
    展示如何在策略中使用Binance数据引擎
    """

    def __init__(self, main_engine: MainEngine, trade_engine: BinanceTraderEngine,
                 strategy_name: str = "binance_strategy"):
        """
        初始化策略

        Args:
            main_engine: 主引擎
            strategy_name: 策略名称
        """
        self.main_engine = main_engine

        self.trade_engine = trade_engine

        self.strategy_name = strategy_name

        # 注册事件处理函数

        # 频率
        self.interval = '15m'

        # rest api
        self.rest_api = BinanceRest()

        # 日志
        self.logger = logging.getLogger(strategy_name)
        self.position_path = position_path
        self.register()
        self.logger.info(f"策略 {strategy_name} 初始化完成")
    
    def register(self,):
        self.main_engine.event_engine.register(EventType.BAR15MIN, self.on_bar)

    def on_bar(self, event: Event):
        """
        处理K线数据事件

        Args:
            event: 事件对象, 数据源为websocket
        """
        bar = event.data
        if not isinstance(bar, BarData):
            return

        tm = bar.datetime.strftime('%Y-%m-%d %H:%M:%S')
        # todo 本地测试时可以临时修改
        # tm = tm.replace('2025-05-07', '2025-03-20')
        # tm, _ = now_time_to_trade_time()
        code = bar.symbol.upper()

        self.logger.info(
            f"收到ws {code} {self.interval} K线: 时间{tm} 开{bar.open_price} 高{bar.high_price} 低{bar.low_price} 收{bar.close_price}")

        lut = get_last_mmap_update_time(code, base_name_list)
        self.logger.info(rf'上次更新时间{lut} ws时间{tm}')

        if get_mmap_time_delta(tm, lut) > 1:
            self.logger.info(rf'历史数据缺失 开始下载数据')
            self.rest_api.update_miss_kline(code, self.interval)

        if get_mmap_time_delta(tm, lut) <= 1:
            self.logger.info(rf'ws数据是最新 开始计算信号')
            time_loc = get_mmap_time_loc(tm)
            code_loc = get_mmap_code_loc(code)

            write_mmap_byloc(time_loc, code_loc, 'Open', bar.open_price)
            write_mmap_byloc(time_loc, code_loc, 'High', bar.high_price)
            write_mmap_byloc(time_loc, code_loc, 'Low', bar.low_price)
            write_mmap_byloc(time_loc, code_loc, 'Close', bar.close_price)
            write_mmap_byloc(time_loc, code_loc, 'Volume', bar.volume)
            write_mmap_byloc(time_loc, code_loc, 'Amt', bar.turnover)
            for bn in base_name_list:
                mmap_dict[bn].flush()

            calc_fac_byloc(fac_exp_dict, time_loc, code_loc)
            posi = calc_posi(fac_exp_dict, time_loc, code_loc).mean()
            self.logger.info(rf'{tm}时刻仓位 {posi}')

            trade_info = self.trade_engine.order_target_amount(code, posi, 10, OrderType.MARKET.value
                                                                ,factor_expansion=5,margin_type="CROSSED")

            self.logger.info(rf'{tm}时刻 调仓下单成功')

            # 保存trade_info到csv
            if isinstance(trade_info, dict):
                trade_info_with_time = dict(trade_info)
                trade_info_with_time['time'] = tm  # 增加时间字段
                df = pd.DataFrame([trade_info_with_time])
                file_path = os.path.join(self.position_path, f"{code}.csv")
                if not os.path.exists(file_path):
                    df.to_csv(file_path, index=False, mode='w', encoding='utf-8-sig')
                else:
                    df.to_csv(file_path, index=False, mode='a', header=False, encoding='utf-8-sig')
            

def main():
    """主函数"""
    print("开始测试")

    main_engine = MainEngine()
    binance_engine = BinanceEngine(main_engine, main_engine.event_engine)
    main_engine.add_component(EngineType.DATA, binance_engine, "binance")


    trade_engine = BinanceTraderEngine()
    trade_engine.init_client(api_key, secret_key, use_testnet=False)

    binance_engine.connect()
    strategy = BinanceStrategy(main_engine, trade_engine)
    trade_code_list = ['DOGEUSDT']
    for code in trade_code_list:
        if code != 'FTMUSDT':
            binance_engine.subscribe_futures_kline(code, strategy.interval)

    try:
        # 持续运行一段时间
        count = 0
        # max_count = 5
        max_count = 5e10
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
