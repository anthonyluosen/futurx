#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Binance数据引擎
用于订阅Binance交易所的行情数据
"""

import time
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Callable
from threading import Thread, Lock

from binance.client import Client
# from binance import ThreadedWebsocketManager
from binance.ws.streams import ThreadedWebsocketManager
from binance.enums import FuturesType, ContractType

from core.engine.main_engine import BaseEngine
from core.constant import EventType, Event, Exchange, Interval, SecurityType
from core.base import TickData, BarData
import traceback

class BinanceEngine(BaseEngine):
    """
    Binance数据引擎
    用于订阅Binance交易所的行情数据
    """

    def __init__(self, main_engine, event_engine, engine_name: str = "binance") -> None:
        """
        初始化Binance数据引擎
        
        Args:
            main_engine: 主引擎
            event_engine: 事件引擎
            engine_name: 引擎名称
        """
        super().__init__(main_engine, event_engine, engine_name)

        # Binance客户端
        self.client = None

        # WebSocket管理器
        self.twm = None

        # 订阅的交易对
        self.subscribed_symbols = set()

        # 订阅的K线周期
        self.subscribed_intervals = set()

        self.subscribed_futures_intervals = set()

        # 连接状态
        self.connected = False

        # 线程锁
        self._lock = Lock()

        self.logger = logging.getLogger("BinanceEngine")

    def init_client(self, api_key: str = "", api_secret: str = "", testnet: bool = False,
                    proxies: Optional[Dict[str, str]] = None) -> None:
        """
        初始化Binance客户端
        
        Args:
            api_key: API密钥
            api_secret: API密钥
            testnet: 是否使用测试网
            proxies: 代理设置
        """
        self.client = Client(api_key, api_secret, requests_params={'proxies': proxies}, testnet=testnet)
        self.logger.info("Binance客户端初始化成功")

    def connect(self) -> bool:
        """
        连接Binance
        
        Returns:
            bool: 连接是否成功
        """
        if self.connected:
            return True

        try:
            # 创建线程化websocket管理器
            self.twm = ThreadedWebsocketManager()
            # 启动线程化websocket管理器
            self.twm.start()
            self.connected = True
            self.logger.info("Binance WebSocket连接成功")

            return True
        except Exception as e:
            self.logger.error(f"Binance WebSocket连接失败: {e}")
            return False

    def disconnect(self) -> bool:
        """
        断开Binance连接
        
        Returns:
            bool: 断开是否成功
        """
        if not self.connected:
            return True

        try:
            if self.twm:
                self.twm.stop()
                self.twm = None
            self.connected = False
            self.logger.info("Binance WebSocket连接已断开")
            return True
        except Exception as e:
            self.logger.error(f"断开Binance WebSocket连接失败: {e}")
            return False

    def subscribe_tick(self, symbol: str, check_conc: bool = True) -> bool:
        """
        订阅逐笔交易数据
        
        Args:
            symbol: 交易对，例如 'btcusdt'
            check_conc: 检查连接状态

        Returns:
            bool: 订阅是否成功
        """
        if check_conc:
            if not self.connected:
                if not self.connect():
                    return False

        try:
            # 标准化交易对格式
            symbol = symbol.lower()

            # 检查是否已订阅
            if symbol in self.subscribed_symbols:
                return True

            # 订阅逐笔交易数据
            self.twm.start_trade_socket(callback=lambda msg: self._on_trade_message(msg, symbol), symbol=symbol)

            # 添加到已订阅列表
            with self._lock:
                self.subscribed_symbols.add(symbol)

            self.logger.info(f"成功订阅 {symbol.upper()} 的逐笔交易数据")
            return True
        except Exception as e:
            self.logger.error(f"订阅 {symbol} 逐笔交易数据失败: {e}")
            return False

    def subscribe_kline(self, symbol: str, interval: str, check_conc: bool = True) -> bool:
        """
        订阅K线数据
        
        Args:
            symbol: 交易对，例如 'btcusdt'
            interval: K线周期，例如 '1m', '5m', '15m', '30m', '1h', '4h', '1d'
            check_conc: 检查连接状态
        Returns:
            bool: 订阅是否成功
        """

        if check_conc:
            if not self.connected:
                if not self.connect():
                    return False

        try:
            # 标准化交易对格式
            symbol = symbol.lower()

            # 检查是否已订阅
            subscription_key = f"{symbol}_{interval}"
            if subscription_key in self.subscribed_intervals:
                return True

            # 订阅K线数据
            self.twm.start_kline_socket(callback=lambda msg: self._on_kline_message(msg, symbol, interval),
                                        symbol=symbol, interval=interval)

            # 添加到已订阅列表
            with self._lock:
                self.subscribed_intervals.add(subscription_key)

            self.logger.info(f"成功订阅 {symbol.upper()} 的 {interval} K线数据")
            return True
        except Exception as e:
            self.logger.error(f"订阅 {symbol} {interval} K线数据失败: {e}")
            return False

    def subscribe_futures_kline(self, symbol: str, interval: str,
                              futures_type: FuturesType = FuturesType.USD_M,
                              contract_type: ContractType = ContractType.PERPETUAL,
                              check_conc: bool = True) -> bool:
        """
        订阅期货K线数据
        
        Args:
            symbol: 交易对，例如 'btcusdt'
            interval: K线周期，例如 '1m', '5m', '15m', '30m', '1h', '4h', '1d'
            futures_type: 期货类型，USD_M表示U本位合约
            contract_type: 合约类型，PERPETUAL表示永续合约
            check_conc: 检查连接状态
            
        Returns:
            bool: 订阅是否成功
        """
        if check_conc:
            if not self.connected:
                if not self.connect():
                    return False

        try:
            # 标准化交易对格式
            symbol = symbol.lower()

            # 检查是否已订阅
            subscription_key = f"{symbol}_{interval}_{futures_type}_{contract_type}"
            if subscription_key in self.subscribed_futures_intervals:
                return True

            # 订阅期货K线数据
            self.twm.start_kline_futures_socket(
                callback=lambda msg: self._on_futures_kline_message(msg, symbol, interval),
                symbol=symbol,
                interval=interval,
                futures_type=futures_type,
                contract_type=contract_type
            )

            # 添加到已订阅列表
            with self._lock:
                self.subscribed_futures_intervals.add(subscription_key)

            self.logger.info(f"成功订阅 {symbol.upper()} 的期货 {interval} K线数据")
            return True
        except Exception as e:
            self.logger.error(f"订阅 {symbol} 期货 {interval} K线数据失败: {e}")
            return False

    def _on_trade_message(self, msg: Dict, symbol: str) -> None:
        """
        处理逐笔交易消息
        
        Args:
            msg: 消息内容
            symbol: 交易对
        """
        try:
            # 检查消息是否包含错误
            if 'error' in msg:
                self.logger.error(f"接收到错误: {msg['error']}")
                return

            # 检查消息类型
            if 'e' in msg and msg['e'] == 'trade':
                # 创建TickData对象
                tick = TickData(
                    gateway_name="binance",
                    symbol=symbol,
                    exchange=Exchange.BINANCE,
                    datetime=datetime.fromtimestamp(msg['T'] / 1000, tz=timezone.utc),
                    name=symbol.upper(),
                    last_price=float(msg['p']),
                    last_volume=float(msg['q']),
                    volume=float(msg['q']),
                    turnover=float(msg['p']) * float(msg['q'])
                )

                # 推送事件
                event = Event(type=EventType.TICK, data=tick)
                self.event_engine.put(event)

                self.logger.debug(f"收到 {symbol} 交易: 价格={msg['p']}, 数量={msg['q']}")
        except Exception as e:
            self.logger.error(f"处理逐笔交易消息时发生错误: {e}")
    
    def _on_futures_kline_message(self, msg: Dict, symbol: str, interval: str) -> None:
        """
        处理期货K线消息
        
        Args:
            msg: 消息内容
            symbol: 交易对
            interval: K线周期
        """
        try:
            # print(msg)
            # 检查消息是否包含错误
            if 'error' in msg:
                self.logger.error(f"接收到期货错误: {msg['error']}")
                return

            # 检查消息类型
            if 'e' in msg and msg['e'] == 'continuous_kline':
                kline = msg['k']
                # 只有当K线完成时才推送事件
                if kline['x']:
                    # 创建BarData对象
                    bar = BarData(
                        gateway_name="binance_futures",
                        symbol=symbol,
                        exchange=Exchange.BINANCE,
                        datetime=datetime.fromtimestamp(kline['t'] / 1000, tz=timezone.utc),
                        interval=self._convert_interval(interval),
                        open_price=float(kline['o']),
                        high_price=float(kline['h']),
                        low_price=float(kline['l']),
                        close_price=float(kline['c']),
                        volume=float(kline['v']),
                        turnover=float(kline['q']),
                    )

                    # 根据K线周期推送不同的事件
                    event_type = self._get_event_type(interval)
                    event = Event(type=event_type, data=bar)
                    self.event_engine.put(event)

                    self.logger.debug(f"收到期货 {symbol} {interval} K线: 开盘={kline['o']}, 收盘={kline['c']}, 成交量={kline['v']}")

        except Exception as e:
            self.logger.error(f"处理期货K线消息时发生错误: {traceback.format_exc()}")
            
            self.logger.error(f"消息内容: {msg}")

        except Exception as e:
            self.logger.error(f"处理期货K线消息时发生错误: {e}")
    def _on_kline_message(self, msg: Dict, symbol: str, interval: str) -> None:
        """
        处理K线消息
        
        Args:
            msg: 消息内容
            symbol: 交易对
            interval: K线周期
        """
        try:
            # 检查消息是否包含错误
            if 'error' in msg:
                self.logger.error(f"接收到错误: {msg['error']}")
                return

            # 检查消息类型
            if 'e' in msg and msg['e'] == 'kline':
                kline = msg['k']

                # 只有当K线完成时才推送事件
                if kline['x']:
                    # 创建BarData对象
                    bar = BarData(
                        gateway_name="binance",
                        symbol=symbol,
                        exchange=Exchange.BINANCE,
                        datetime=datetime.fromtimestamp(kline['t'] / 1000, tz=timezone.utc),
                        interval=self._convert_interval(interval),
                        open_price=float(kline['o']),
                        high_price=float(kline['h']),
                        low_price=float(kline['l']),
                        close_price=float(kline['c']),
                        volume=float(kline['v']),
                        turnover=float(kline['q'])
                    )

                    # 根据K线周期推送不同的事件
                    event_type = self._get_event_type(interval)
                    event = Event(type=event_type, data=bar)
                    self.event_engine.put(event)

        except Exception as e:
            self.logger.error(f"处理K线消息时发生错误: {e}")

    def _convert_interval(self, interval: str) -> Interval:
        """
        将Binance的K线周期转换为系统内部的K线周期
        
        Args:
            interval: Binance的K线周期
            
        Returns:
            Interval: 系统内部的K线周期
        """
        interval_map = {
            '1m': Interval.MINUTE,
            '1h': Interval.HOUR,
            '1d': Interval.DAILY,
            '1w': Interval.WEEKLY
        }
        return interval_map.get(interval, Interval.MINUTE)

    def _get_event_type(self, interval: str) -> EventType:
        """
        根据K线周期获取对应的事件类型
        
        Args:
            interval: K线周期
            
        Returns:
            EventType: 事件类型
        """
        interval_map = {
            '1m': EventType.BAR1MIN,
            '5m': EventType.BAR5MIN,
            '15m': EventType.BAR15MIN,
            '30m': EventType.BAR30MIN,
            '1h': EventType.BAR1HOUR,
            '4h': EventType.BAR4HOUR
        }
        return interval_map.get(interval, EventType.BAR1MIN)

    def get_realtime_quotes(self, symbol: str) -> Dict:
        """
        获取实时行情
        
        Args:
            symbol: 交易对
            
        Returns:
            Dict: 行情数据
        """
        try:
            # 标准化交易对格式
            symbol = symbol.upper()

            # 获取24小时价格变化统计
            ticker = self.client.get_ticker(symbol=symbol)

            return {
                'symbol': symbol,
                'last_price': float(ticker['lastPrice']),
                'volume': float(ticker['volume']),
                'turnover': float(ticker['quoteVolume']),
                'open_price': float(ticker['openPrice']),
                'high_price': float(ticker['highPrice']),
                'low_price': float(ticker['lowPrice']),
                'pre_close': float(ticker['prevClosePrice']),
                'bid1': float(ticker['bidPrice']),
                'ask1': float(ticker['askPrice']),
                'bidvol1': float(ticker['bidQty']),
                'askvol1': float(ticker['askQty'])
            }
        except Exception as e:
            self.logger.error(f"获取 {symbol} 实时行情失败: {e}")
            return {}

    def get_realtime_quotes_list(self, symbol_list: List[str]) -> List[Dict]:
        """
        获取多个交易对的实时行情
        
        Args:
            symbol_list: 交易对列表
            
        Returns:
            List[Dict]: 行情数据列表
        """
        result = []
        for symbol in symbol_list:
            quotes = self.get_realtime_quotes(symbol)
            if quotes:
                result.append(quotes)
        return result

    def close(self) -> None:
        """
        关闭引擎
        """
        self.disconnect()
        super().close()
