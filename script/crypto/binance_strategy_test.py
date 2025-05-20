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
from core.base import TickData, BarData
from futurx_crypto.binance_engine import BinanceEngine
from core.constant import EventType, Event
from factor_crypto.write_mmap import *
from factor_crypto.calc_fac import calc_fac_byloc, calc_posi
from factor_crypto.binance_rest import BinanceRest
from futurx_crypto.binance_trader_engine import BinanceTraderEngine

import logging

logging.basicConfig(
    level=logging.DEBUG,
    format='%(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)


class BinanceStrategy:
    """
    Binance策略示例
    展示如何在策略中使用Binance数据引擎
    """

    def __init__(self, main_engine: MainEngine, trade_engine: BinanceTraderEngine,
                 strategy_name: str = "binance_strategy", symbol: str = "btcusdt"):
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
        self.main_engine.event_engine.register(EventType.BAR15MIN, self.on_bar)

        # 订阅的交易对
        self.symbol = symbol

        # 频率
        self.interval = '15m'

        # rest api
        self.rest_api = BinanceRest()

        # 日志
        self.logger = logging.getLogger(strategy_name)

        self.logger.info(f"策略 {strategy_name} 初始化完成")

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

        self.logger.debug(
            f"收到ws {code} {self.interval} K线: 时间{tm} 开{bar.open_price} 高{bar.high_price} 低{bar.low_price} 收{bar.close_price}")

        lut = get_last_mmap_update_time(code, base_name_list)
        self.logger.debug(rf'上次更新时间{lut} ws时间{tm}')

        if get_mmap_time_delta(tm, lut) > 1:
            self.logger.debug(rf'历史数据缺失 开始下载数据')
            self.rest_api.update_miss_kline(code, self.interval)

        if get_mmap_time_delta(tm, lut) <= 1:
            self.logger.debug(rf'ws数据是最新 开始计算信号')
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

            trade_info = self.trade_engine.order_target_amount(code, posi, 1, "MARKET")
            self.logger.info(rf'{tm}时刻 调仓下单成功')
            self.logger.info(rf'下单信息 {str(trade_info)}')


def main():
    """主函数"""
    print("开始测试")

    main_engine = MainEngine()
    binance_engine = BinanceEngine(main_engine, main_engine.event_engine)
    main_engine.add_component("data", binance_engine, "binance")

    test_api_key = "c3be109e8eb4be673f69b2bced4be0494efe24bb45ee31aae152c44c60ffdbd8"
    test_secret_key = "20beaf4892d63ae8fa58fe3b3d5e49030f428859567a64449bfb42fa5465165a"
    trade_engine = BinanceTraderEngine()
    trade_engine.init_client(test_api_key, test_secret_key, use_testnet=True)

    test_local = False

    if test_local:
        strategy = BinanceStrategy(main_engine, trade_engine, symbol='btcusdt')
        binance_engine.subscribe_kline(strategy.symbol, strategy.interval, check_conc=False)
        local_kline = pd.read_csv(rf"{facfmk_root_path}/sample_kline/BTCUSDT-15m-2025-05-07.csv")
        for index, row in local_kline.iterrows():
            msg = dict()
            msg['e'] = 'kline'
            dic = dict()
            dic['x'] = True
            dic['t'] = row['open_time']
            dic['o'] = row['open']
            dic['h'] = row['high']
            dic['l'] = row['low']
            dic['c'] = row['close']
            dic['v'] = row['volume']
            dic['q'] = row['quote_volume']
            msg['k'] = dic
            binance_engine._on_kline_message(msg, strategy.symbol, '15m')

    else:
        binance_engine.connect()
        strategy = BinanceStrategy(main_engine, trade_engine, symbol='btcusdt')
        binance_engine.subscribe_kline(strategy.symbol, strategy.interval)

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
