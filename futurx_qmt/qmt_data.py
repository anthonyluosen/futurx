from typing import Dict, List, Optional, Callable, Any
from datetime import datetime
from core.engine.main_engine import BaseEngine
from core.engine.event_engine import EventEngine
from core.constant import EventType, SecurityType, BarData, TickData, Exchange, Interval, Event
import pandas as pd
from xtquant import xtdata
import logging

class QmtDataEngine(BaseEngine):
    """
    QMT数据引擎 - 专注于数据推送服务
    """
    
    def __init__(
        self,
        main_engine: 'MainEngine',
        event_engine: EventEngine,
        engine_name: str = "qmt_data"
    ):
        """初始化"""
        super().__init__(main_engine, event_engine, engine_name)
        
        # 订阅的股票和周期列表
        self.subscriptions: Dict[str, List[str]] = {}
        
        # 初始化QMT数据接口
        self._init_qmt()
        
    def _init_qmt(self) -> None:
        """初始化QMT数据接口"""
        try:
            # 初始化xtdata
            xtdata.init()
            self.logger.info("QMT数据接口初始化成功")
        except Exception as e:
            self.logger.error(f"QMT数据接口初始化失败: {e}")
            raise
    
    def _on_data_update(self, data: Any) -> None:
        """
        数据更新回调函数 - 将数据通过事件引擎推送给其他组件
        
        Args:
            data: 接收到的数据
        """
        try:
            if not data or not isinstance(data, dict):
                return
                
            symbol = data.get('symbol')
            if not symbol:
                return
                
            # 获取周期
            period = data.get('period', '1m')
            
            # 根据周期类型确定事件类型
            event_type = self._get_event_type(period)
            
            # 转换为BarData或TickData
            if period == 'tick':
                event_data = self._convert_to_tick_data(data)
            else:
                event_data = self._convert_to_bar_data(data, period)
            
            # 创建事件对象
            event = Event(
                type=event_type,
                data=event_data
            )
            
            # 推送事件
            self.event_engine.put(event)
            self.logger.debug(f"推送{symbol}的{period}数据")
                    
        except Exception as e:
            self.logger.error(f"处理数据更新失败: {e}")
    
    def _get_event_type(self, period: str) -> EventType:
        """根据周期获取对应的事件类型"""
        if period == 'tick':
            return EventType.TICK
        elif period == '1m':
            return EventType.BAR1MIN
        # elif period == '5m':
        #     return EventType.BAR5MIN
        # elif period == '15m':
        #     return EventType.BAR15MIN
        # elif period == '30m':
        #     return EventType.BAR30MIN
        # elif period == '60m' or period == '1h':
        #     return EventType.BAR1HOUR
        else:
            # 默认使用1分钟K线事件类型
            return EventType.BAR1MIN
    
    def _convert_to_bar_data(self, data: dict, period: str) -> BarData:
        """将QMT数据转换为BarData"""
        # 解析交易所
        symbol = data.get('symbol', '')
        exchange_code = "SSE" if symbol.endswith("SH") else "SZSE" if symbol.endswith("SZ") else "LOCAL"
        
        # 获取时间间隔
        interval_map = {
            '1m': Interval.MINUTE,
            '1h': Interval.HOUR,
            'd': Interval.DAILY,
            'w': Interval.WEEKLY
        }
        interval = interval_map.get(period, Interval.MINUTE)
        
        # 创建BarData对象
        bar = BarData(
            symbol=symbol,
            exchange=Exchange(exchange_code),
            datetime=datetime.now() if 'time' not in data else data['time'],
            interval=interval,
            volume=data.get('volume', 0),
            turnover=data.get('amount', 0),
            open_interest=data.get('open_interest', 0),
            open_price=data.get('open', 0),
            high_price=data.get('high', 0),
            low_price=data.get('low', 0),
            close_price=data.get('close', 0)
        )
        
        return bar
    
    def _convert_to_tick_data(self, data: dict) -> TickData:
        """将QMT数据转换为TickData"""
        # 解析交易所
        symbol = data.get('symbol', '')
        exchange_code = "SSE" if symbol.endswith("SH") else "SZSE" if symbol.endswith("SZ") else "LOCAL"
        
        # 创建TickData对象
        tick = TickData(
            symbol=symbol,
            exchange=Exchange(exchange_code),
            datetime=datetime.now() if 'time' not in data else data['time'],
            name=data.get('name', ''),
            volume=data.get('volume', 0),
            turnover=data.get('amount', 0),
            open_interest=data.get('open_interest', 0),
            last_price=data.get('last', 0),
            last_volume=data.get('last_volume', 0),
            limit_up=data.get('limit_up', 0),
            limit_down=data.get('limit_down', 0),
            open_price=data.get('open', 0),
            high_price=data.get('high', 0),
            low_price=data.get('low', 0),
            pre_close=data.get('pre_close', 0),
            bid1=data.get('bid1', 0),
            bid2=data.get('bid2', 0),
            bid3=data.get('bid3', 0),
            bid4=data.get('bid4', 0),
            bid5=data.get('bid5', 0),
            ask1=data.get('ask1', 0),
            ask2=data.get('ask2', 0),
            ask3=data.get('ask3', 0),
            ask4=data.get('ask4', 0),
            ask5=data.get('ask5', 0),
            bidvol1=data.get('bidvol1', 0),
            bidvol2=data.get('bidvol2', 0),
            bidvol3=data.get('bidvol3', 0),
            bidvol4=data.get('bidvol4', 0),
            bidvol5=data.get('bidvol5', 0),
            askvol1=data.get('askvol1', 0),
            askvol2=data.get('askvol2', 0),
            askvol3=data.get('askvol3', 0),
            askvol4=data.get('askvol4', 0),
            askvol5=data.get('askvol5', 0),
            localtime=datetime.now()
        )
        
        return tick
            
    def subscribe(self, symbol: str, period: str = '1m') -> bool:
        """
        订阅股票数据
        
        Args:
            symbol: 股票代码
            period: 时间周期，如 '1m'(1分钟), '5m'(5分钟), '1d'(日线)
            
        Returns:
            bool: 是否订阅成功
        """
        try:
            # 添加到订阅字典
            if symbol not in self.subscriptions:
                self.subscriptions[symbol] = []
                
            # 检查是否已经订阅了该周期
            if period in self.subscriptions[symbol]:
                self.logger.warning(f"股票{symbol}的{period}周期数据已经订阅")
                return True
                
            # 订阅数据
            xtdata.subscribe_quote(symbol, period, callback=self._on_data_update)
            
            # 保存订阅信息
            self.subscriptions[symbol].append(period)
            
            self.logger.info(f"成功订阅股票{symbol}的{period}周期数据")
            return True
            
        except Exception as e:
            self.logger.error(f"订阅股票{symbol}的{period}周期数据失败: {e}")
            return False
            
    def unsubscribe(self, symbol: str, period: str = None) -> bool:
        """
        取消订阅股票数据
        
        Args:
            symbol: 股票代码
            period: 时间周期，如果为None则取消所有周期
            
        Returns:
            bool: 是否取消订阅成功
        """
        try:
            if symbol not in self.subscriptions:
                self.logger.warning(f"股票{symbol}未订阅")
                return True
                
            # 取消特定周期的订阅
            if period:
                if period not in self.subscriptions[symbol]:
                    self.logger.warning(f"股票{symbol}的{period}周期数据未订阅")
                    return True
                    
                # 取消订阅
                xtdata.unsubscribe_quote(symbol, period)
                
                # 删除订阅记录
                self.subscriptions[symbol].remove(period)
                
                self.logger.info(f"成功取消订阅股票{symbol}的{period}周期数据")
                
                # 如果没有其他周期的订阅，清理缓存
                if not self.subscriptions[symbol]:
                    del self.subscriptions[symbol]
            
            # 取消所有周期的订阅
            else:
                for p in list(self.subscriptions[symbol]):
                    xtdata.unsubscribe_quote(symbol, p)
                
                # 删除订阅记录
                del self.subscriptions[symbol]
                
                self.logger.info(f"成功取消订阅股票{symbol}的所有周期数据")
                
            return True
            
        except Exception as e:
            self.logger.error(f"取消订阅股票{symbol}数据失败: {e}")
            return False
            
    def start(self) -> None:
        """启动引擎"""
        super().start()
        
    def stop(self) -> None:
        """停止引擎"""
        # 取消所有订阅
        for symbol in list(self.subscriptions.keys()):
            self.unsubscribe(symbol)
            
        super().stop()
        
    def close(self) -> None:
        """关闭引擎"""
        self.stop()
        super().close()
        
# 使用示例:
"""
# 初始化引擎
qmt_engine = QmtDataEngine(main_engine, event_engine)

# 订阅数据 - 数据会通过事件引擎推送
qmt_engine.subscribe('000001.SZ', '1m')

# 取消订阅
qmt_engine.unsubscribe('000001.SZ', '1m')
"""
