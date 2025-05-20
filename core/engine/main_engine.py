from typing import Dict, List, Optional, Type, Set, Any
from datetime import datetime, timedelta
from core.engine.event_engine import EventEngine
from core.constant import Order, OrderStatus, DictToClass, EventType, SecurityType, EngineType
from abc import ABC
from core.base import BaseTrader, BaseOnline
import traceback
import logging



class MainEngine:
    """
    主引擎 - 交易平台核心
    支持多市场(A股、数字货币)、多时间周期(秒级、分钟级)的CTA交易框架
    """
    def __init__(self, query_interval: float = 1, logger=None):
        """
        初始化主引擎
        Args:
            query_interval: 订单查询间隔（秒）
            logger: 外部注入的日志对象，如果为None则使用默认日志
        """
        # 事件引擎
        self.event_engine = EventEngine(timer_interval=query_interval)
        
        # 组件字典
        self.traders: Dict[str, BaseTrader] = {}  # 交易接口
        self.data_engines: Dict[str, BaseOnline] = {}  # 数据源
        self.engines = {}  # 功能引擎（包含策略引擎）
        self.active_orders: Dict[str, Order] = {}  # 活跃订单
        
        # 组件类型映射
        self._component_maps = {
            EngineType.TRADER: self.traders,
            EngineType.DATA: self.data_engines,
            EngineType.ENGINE: self.engines
        }
        
        # 使用外部传入的日志器或创建默认日志器
        self.logger = logger or logging.getLogger("MainEngine")
        
        # 启动引擎
        self.start()

    def add_component(self, engine_type: EngineType, component: Any, name: str = None) -> None:
        """
        添加组件到主引擎
        
        Args:
            engine_type: 引擎类型，使用EngineType枚举
            component: 组件实例
            name: 组件名称，如果为None且是engine类型，会使用component.engine_name
        """
        if engine_type not in self._component_maps:
            self.logger.error(f"未知引擎类型: {engine_type}")
            return
        
        # 处理组件名称
        if name is None:
            if hasattr(component, "engine_name"):
                name = component.engine_name
            else:
                self.logger.error(f"添加{engine_type.value}引擎时必须提供名称")
                return
            
        # 将组件添加到对应的字典中
        self._component_maps[engine_type][name] = component
        self.logger.info(f"添加{engine_type.value}: {name}")
        
        # 设置主引擎和日志
        if hasattr(component, "set_main_engine"):
            component.set_main_engine(self)
        elif hasattr(component, "main_engine") and component.main_engine is None:
            component.main_engine = self

    def get_engine(self, engine_name: str):
        """获取指定名称的引擎"""
        return self.engines.get(engine_name)
    
    def get_trader(self, trader_name: str) -> Optional[BaseTrader]:
        """获取指定名称的交易接口"""
        return self.traders.get(trader_name)
    
    def get_data_engine(self, name: str) -> Optional[BaseOnline]:
        """获取指定名称的数据源"""
        return self.data_engines.get(name)

    def start(self) -> None:
        """启动交易系统"""
        self.event_engine.start()
        self.logger.info("交易系统已启动")
    
    def stop(self) -> None:
        """停止交易系统"""
        # 停止所有引擎
        for engine in list(self.engines.values()):
            if hasattr(engine, 'stop') and callable(getattr(engine, 'stop')):
                try:
                    engine.stop()
                except Exception as e:
                    self.logger.error(f"停止引擎{engine.engine_name}失败: {e}")
                    traceback.print_exc()
        
        # 停止事件引擎
        self.event_engine.stop()
        self.logger.info("交易系统已停止")
    
    def connect(self, trader_name: str) -> None:
        """连接交易接口"""
        trader = self.traders.get(trader_name)
        if trader:
            trader.connect()
            self.logger.info(f"连接交易接口: {trader_name}")
        else:
            self.logger.error(f"交易接口不存在: {trader_name}")

    def disconnect(self, trader_name: str) -> None:
        """断开交易接口"""
        trader = self.traders.get(trader_name)
        if trader:
            trader.disconnect()
            self.logger.info(f"断开交易接口: {trader_name}")
        else:
            self.logger.error(f"交易接口不存在: {trader_name}")

    def place_order(self, order: Order) -> bool:
        """提交订单"""
        try:
            trader = self.traders.get(order.trader_platform)
            if not trader:
                self.logger.error(f"找不到交易接口: {order.trader_platform}")
                return False
            
            # 提交订单
            success = trader.place_order(
                symbol=order.symbol, 
                volume=order.volume, 
                price=order.limit_price, 
                order_type=order.order_type,
                direction=order.direction,
                **order.get_extra_params()  # 获取额外参数
            )
            
            return success

        except Exception as e:
            self.logger.error(f"提交订单失败: {e}")
            traceback.print_exc()
            return False

    def cancel_order(self, order: Order) -> bool:
        """撤销订单"""
        try:
            trader = self.traders.get(order.trader_platform)
            if not trader:
                self.logger.error(f"找不到交易接口: {order.trader_platform}")
                return False
            
            success = trader.cancel_order(order.order_id)
            
            return success

        except Exception as e:
            self.logger.error(f"撤销订单失败: {e}")
            traceback.print_exc()
            return False

    def get_order_status(self, order: Order) -> Optional[OrderStatus]:
        """获取订单状态"""
        try:
            trader = self.traders.get(order.trader_platform)
            if not trader:
                self.logger.error(f"找不到交易接口: {order.trader_platform}")
                return False
            
            success = trader.get_order_status(order.order_id)
            
            return success

        except Exception as e:
            self.logger.error(f"获取订单状态失败: {e}")
            traceback.print_exc()
            return None

    def get_order(self, order_id: str) -> Optional[Order]:
        """获取订单"""
        return self.active_orders.get(order_id)

    def close(self) -> None:
        """关闭所有组件"""
        self.stop()  # 停止所有策略和事件引擎
        
        # 关闭所有引擎
        for engine in self.engines.values():
            if hasattr(engine, 'close') and callable(getattr(engine, 'close')):
                try:
                    engine.close()
                except Exception as e:
                    self.logger.error(f"关闭引擎{engine.engine_name}失败: {e}")

        # 关闭所有交易接口
        for trader in self.traders.values():
            if hasattr(trader, 'close') and callable(getattr(trader, 'close')):
                try:
                    trader.close()
                except Exception as e:
                    self.logger.error(f"关闭交易接口失败: {e}")
        for data_engine in self.data_engines.values():
            if hasattr(data_engine, 'close') and callable(getattr(data_engine, 'close')):
                try:
                    data_engine.close()
                except Exception as e:
                    self.logger.error(f"关闭数据源失败: {e}")

        self.logger.info("交易系统已完全关闭")




class BaseEngine(ABC):
    """功能引擎基类"""

    def __init__(self, main_engine: MainEngine, event_engine: EventEngine, engine_name: str) -> None:
        """初始化"""
        self.main_engine = main_engine
        self.event_engine = event_engine
        self.engine_name = engine_name
        self.logger = main_engine.logger if main_engine else None
        self.active = False

    def start(self) -> None:
        """启动引擎"""
        self.active = True
        self.logger.info(f"引擎{self.engine_name}已启动")
    
    def stop(self) -> None:
        """停止引擎"""
        self.active = False
        self.logger.info(f"引擎{self.engine_name}已停止")

    def close(self) -> None:
        """关闭引擎"""
        if self.active:
            self.stop()

    def set_main_engine(self, main_engine: MainEngine) -> None:
        """设置主引擎"""
        self.main_engine = main_engine
        self.logger = main_engine.logger


