from typing import Dict, List, Optional, Type, Set
from datetime import datetime, timedelta
from core.engine.event_engine import EventEngine
from core.constant import Order, OrderStatus, DictToClass, EventType, SecurityType
from abc import ABC
from core.base import BaseTrader, BaseOnline
import traceback
import logging

class MainEngine:
    """
    主引擎 - 交易平台核心
    支持多市场(A股、数字货币)、多时间周期(秒级、分钟级)的CTA交易框架
    """
    def __init__(self, query_interval: float = 1, log_level: int = logging.INFO):
        """
        初始化主引擎
        Args:
            query_interval: 订单查询间隔（秒）
            log_level: 日志级别
        """
        # 事件引擎 - 分别为秒级和分钟级设置不同的事件引擎
        self.event_engine = EventEngine(timer_interval=query_interval)
        self.min_event_engine = EventEngine(timer_interval=60)  # 分钟级事件引擎
        
        # 各类组件字典
        self.traders: Dict[str, BaseTrader] = {}  # 交易接口字典
        self.engines: Dict[str, BaseEngine] = {}  # 功能引擎字典
        self.datasources: Dict[str, BaseOnline] = {}  # 数据源字典
        self.strategies: Dict[str, 'BaseStrategy'] = {}  # 策略字典
        self.active_orders: Dict[str, Order] = {}  # 活跃订单字典
        self.logs = {}  # 日志组件字典
        
        # 市场分类
        self.stock_traders: Set[str] = set()  # A股交易接口名称集合
        self.crypto_traders: Set[str] = set()  # 数字货币交易接口名称集合
        
        # 配置日志
        self.logger = logging.getLogger("MainEngine")
        self.logger.setLevel(log_level)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
        
        # 启动引擎
        self.start()

    def add_trader(self, trader_engine, name, market_type: str = "stock"):
        """
        添加交易接口
        Args:
            trader_engine: 交易接口实例
            name: 交易接口名称
            market_type: 市场类型，"stock"表示A股，"crypto"表示数字货币
        """
        self.traders[name] = trader_engine
        
        # 根据市场类型分类
        if market_type.lower() == "stock":
            self.stock_traders.add(name)
        elif market_type.lower() == "crypto":
            self.crypto_traders.add(name)
        
        self.logger.info(f"添加交易接口: {name}, 市场类型: {market_type}")
    
    def add_log(self, log_engine, name):
        """添加日志引擎"""
        self.logs[name] = log_engine

    def add_datasource(self, datasource_engine, name):
        """添加数据源"""
        self.datasources[name] = datasource_engine
    
    def add_engine(self, engine):
        """添加功能引擎"""
        self.engines[engine.engine_name] = engine
        self.logger.info(f"添加功能引擎: {engine.engine_name}")
    
    def add_strategy(self, strategy, strategy_name):
        """
        添加CTA策略
        Args:
            strategy: 策略实例
            strategy_name: 策略名称
        """
        self.strategies[strategy_name] = strategy
        self.logger.info(f"添加策略: {strategy_name}")

    def init_strategy(self, strategy_name):
        """
        初始化指定策略
        Args:
            strategy_name: 策略名称
        """
        if strategy_name in self.strategies:
            self.strategies[strategy_name].init()
            self.logger.info(f"初始化策略: {strategy_name}")
        else:
            self.logger.error(f"策略不存在: {strategy_name}")
    
    def start_strategy(self, strategy_name):
        """
        启动指定策略
        Args:
            strategy_name: 策略名称
        """
        if strategy_name in self.strategies:
            self.strategies[strategy_name].start()
            self.logger.info(f"启动策略: {strategy_name}")
        else:
            self.logger.error(f"策略不存在: {strategy_name}")
    
    def stop_strategy(self, strategy_name):
        """
        停止指定策略
        Args:
            strategy_name: 策略名称
        """
        if strategy_name in self.strategies:
            self.strategies[strategy_name].stop()
            self.logger.info(f"停止策略: {strategy_name}")
        else:
            self.logger.error(f"策略不存在: {strategy_name}")

    def start(self):
        """启动交易系统"""
        self.event_engine.start()  # 启动秒级事件引擎
        self.min_event_engine.start()  # 启动分钟级事件引擎
        self.logger.info("交易系统已启动")
    
    def stop(self):
        """停止交易系统"""
        # 先停止所有策略
        for strategy_name in self.strategies:
            self.stop_strategy(strategy_name)
        
        # 停止事件引擎
        self.event_engine.stop()
        self.min_event_engine.stop()
        self.logger.info("交易系统已停止")
    
    def connect(self, trader_name):
        """连接交易接口"""
        trader = self.traders.get(trader_name)
        if trader:
            trader.connect()
            self.logger.info(f"连接交易接口: {trader_name}")
        else:
            self.logger.error(f"交易接口不存在: {trader_name}")

    def disconnect(self, trader_name):
        """断开交易接口"""
        trader = self.traders.get(trader_name)
        if trader:
            trader.disconnect()
            self.logger.info(f"断开交易接口: {trader_name}")
        else:
            self.logger.error(f"交易接口不存在: {trader_name}")

    def get_account_info(self, trader_name):
        """查询账户信息"""
        trader = self.traders.get(trader_name)
        if trader:
            return trader.get_account_info()
        else:
            self.logger.error(f"交易接口不存在: {trader_name}")
            return None
    
    def get_order_info(self, trader_name, order_id):
        """查询订单信息"""
        trader = self.traders.get(trader_name)
        if trader:
            return trader.get_order_info(order_id)
        else:
            self.logger.error(f"交易接口不存在: {trader_name}")
            return None
    
    def get_positions(self, trader_name):
        """查询持仓信息"""
        trader = self.traders.get(trader_name)
        if trader:
            return trader.get_positions()
        else:
            self.logger.error(f"交易接口不存在: {trader_name}")
            return None
    
    def place_order(self, order: Order) -> bool:
        """
        提交订单
        Args:
            order: 订单对象
        Returns:
            bool: 是否成功提交
        """
        try:
            # 获取对应的交易接口
            trader = self.traders.get(order.trader_platform)
            if not trader:
                self.logger.error(f"找不到交易接口: {order.trader_platform}")
                return False
            
            # 根据证券类型和交易所进行特定处理
            if order.security_type == SecurityType.STOCK:
                # A股特定处理
                success = trader.place_order(
                    symbol=order.symbol, 
                    volume=order.volume, 
                    price=order.limit_price, 
                    order_type=order.order_type,
                    direction=order.direction
                )
            elif order.security_type == SecurityType.CRYPTO:
                # 数字货币特定处理
                success = trader.place_order(
                    symbol=order.symbol, 
                    volume=order.volume, 
                    price=order.limit_price, 
                    order_type=order.order_type,
                    direction=order.direction,
                    leverage=order.get('leverage', 1)  # 数字货币特有参数-杠杆
                )
            else:
                self.logger.error(f"不支持的证券类型: {order.security_type}")
                return False
            
            if success:
                # 记录活跃订单
                self.active_orders[order.order_id] = order
                
                # 发送订单事件
                self.event_engine.put(
                    Event(type=EventType.ORDER, data=order)
                )
                
                self.logger.info(f"订单已提交: {order.order_id}, 交易品种: {order.symbol}")
            
            return success

        except Exception as e:
            self.logger.error(f"提交订单失败: {e}")
            self.logger.error(traceback.format_exc())
            return False

    def cancel_order(self, order: Order) -> bool:
        """
        撤销订单
        Args:
            order: 订单对象
        Returns:
            bool: 是否成功撤单
        """
        try:
            # 获取对应的交易接口
            trader = self.traders.get(order.trader_platform)
            if not trader:
                self.logger.error(f"找不到交易接口: {order.trader_platform}")
                return False
            
            # 撤销订单
            success = trader.cancel_order(order.order_id)
            
            if success:
                # 更新订单状态
                if order.order_id in self.active_orders:
                    self.active_orders[order.order_id].status = OrderStatus.CANCELLED
                    
                    # 发送订单状态变更事件
                    self.event_engine.put(
                        Event(type=EventType.ORDER, data=self.active_orders[order.order_id])
                    )
                    
                    self.logger.info(f"订单已撤销: {order.order_id}")
            
            return success

        except Exception as e:
            self.logger.error(f"撤销订单失败: {e}")
            self.logger.error(traceback.format_exc())
            return False
        
    def get_orders(self, trader_platform):
        """
        获取指定交易平台的订单列表
        """
        try:
            # 获取对应的交易接口
            trader = self.traders.get(trader_platform)
            if not trader:
                self.logger.error(f"找不到交易接口: {trader_platform}")
                return []
            
            # 获取订单列表
            orders = trader.get_orders()
            return orders

        except Exception as e:
            self.logger.error(f"获取订单列表失败: {e}")
            self.logger.error(traceback.format_exc())
            return []
    
    def query_order(self, order: Order) -> dict:
        """
        查询订单状态
        Args:
            order: 订单对象
        Returns:
            dict: 订单信息
        """
        try:
            # 获取对应的交易接口
            trader = self.traders.get(order.trader_platform)
            if not trader:
                self.logger.error(f"找不到交易接口: {order.trader_platform}")
                return None
            
            # 查询订单信息
            info = trader.get_order_info(order.order_id)
            
            # 如果订单已完成，从活跃订单列表中移除
            if info and info.get('status') in [OrderStatus.FILLED, OrderStatus.CANCELLED, OrderStatus.REJECTED]:
                if order.order_id in self.active_orders:
                    del self.active_orders[order.order_id]
            
            return info

        except Exception as e:
            self.logger.error(f"查询订单失败: {e}")
            self.logger.error(traceback.format_exc())
            return None

    def cancel_all(self, trader_platform: str, timeout: float = 60) -> dict:
        """
        撤销指定交易平台的所有未完成订单
        
        Args:
            trader_platform (str): 交易平台名称
            timeout (float, optional): 每个订单的查询超时时间(秒)
            
        Returns:
            dict: 撤单结果统计
        """
        result = {
            'total': 0,
            'success': 0,
            'failed': []
        }
        
        try:
            # 获取所有活跃订单
            orders = self.get_orders(trader_platform)
            if not orders:
                return result
            
            result['total'] = len(orders)
            
            # 遍历撤销每个订单
            for order in orders:
                order["trader_platform"] = trader_platform
                order_ = DictToClass(order)
                
                try:
                    if order and order.get('status_msg') in ['已报', '部分成交']:
                        if self.cancel_order(order_):
                            result['success'] += 1
                        else:
                            result['failed'].append(order_.order_id)
                            
                except Exception as e:
                    self.logger.error(f"撤销订单失败: {order_.order_id}, 错误: {str(e)}")
                    result['failed'].append(order_.order_id)
                    
            self.logger.info(f"批量撤单完成: 总数={result['total']}, 成功={result['success']}, 失败={len(result['failed'])}")
            return result
            
        except Exception as e:
            self.logger.error(f"批量撤单失败: {str(e)}")
            self.logger.error(traceback.format_exc())
            return result

    def process_tick(self, tick_data):
        """
        处理Tick数据
        Args:
            tick_data: Tick数据
        """
        # 创建TICK事件并推送
        self.event_engine.put(
            Event(type=EventType.TICK, data=tick_data)
        )
    
    def process_bar(self, bar_data, interval="1m"):
        """
        处理K线数据
        Args:
            bar_data: K线数据
            interval: K线周期，如"1m"表示1分钟
        """
        # 根据周期类型确定事件类型
        event_type = None
        if interval == "1m":
            event_type = EventType.BAR1MIN
        elif interval == "5m":
            event_type = EventType.BAR5MIN
        elif interval == "15m":
            event_type = EventType.BAR15MIN
        elif interval == "30m":
            event_type = EventType.BAR30MIN
        elif interval == "1h":
            event_type = EventType.BAR1HOUR
        else:
            self.logger.warning(f"不支持的K线周期: {interval}")
            return
        
        # 创建BAR事件并推送
        self.min_event_engine.put(
            Event(type=event_type, data=bar_data)
        )

    def close(self) -> None:
        """
        关闭所有组件
        """
        # 先停止事件引擎
        self.event_engine.stop()
        self.min_event_engine.stop()
        
        # 停止所有策略
        for strategy_name in self.strategies:
            self.stop_strategy(strategy_name)
        
        # 关闭所有引擎
        for engine in self.engines.values():
            if hasattr(engine, 'close') and callable(getattr(engine, 'close')):
                engine.close()

        # 关闭所有交易接口
        for gateway in self.traders.values():
            if hasattr(gateway, 'close') and callable(getattr(gateway, 'close')):
                gateway.close()
        
        self.logger.info("交易系统已完全关闭")

    def register_event(self, event_type: EventType, handler):
        """
        注册事件处理函数
        Args:
            event_type: 事件类型
            handler: 处理函数
        """
        # 根据事件类型决定注册到哪个事件引擎
        if event_type in [EventType.BAR1MIN, EventType.BAR5MIN, 
                          EventType.BAR15MIN, EventType.BAR30MIN, 
                          EventType.BAR1HOUR, EventType.BAR4HOUR]:
            self.min_event_engine.register(event_type, handler)
        else:
            self.event_engine.register(event_type, handler)

    def unregister_event(self, event_type: EventType, handler):
        """
        注销事件处理函数
        Args:
            event_type: 事件类型
            handler: 处理函数
        """
        # 根据事件类型决定从哪个事件引擎注销
        if event_type in [EventType.BAR1MIN, EventType.BAR5MIN, 
                          EventType.BAR15MIN, EventType.BAR30MIN, 
                          EventType.BAR1HOUR, EventType.BAR4HOUR]:
            self.min_event_engine.unregister(event_type, handler)
        else:
            self.event_engine.unregister(event_type, handler)


class BaseEngine(ABC):
    """
    功能引擎基类
    """

    def __init__(
        self,
        main_engine: MainEngine,
        event_engine: EventEngine,
        engine_name: str,
    ) -> None:
        """
        初始化
        Args:
            main_engine: 主引擎
            event_engine: 事件引擎
            engine_name: 引擎名称
        """
        self.main_engine: MainEngine = main_engine
        self.event_engine: EventEngine = event_engine
        self.engine_name: str = engine_name

    def close(self) -> None:
        """
        关闭引擎
        """
        pass


class BaseStrategy(ABC):
    """
    CTA策略基类
    """
    def __init__(
        self,
        main_engine: MainEngine,
        strategy_name: str,
        symbols: List[str] = None,
        setting: dict = None
    ) -> None:
        """
        初始化
        Args:
            main_engine: 主引擎
            strategy_name: 策略名称
            symbols: 交易品种列表
            setting: 策略参数设置
        """
        self.main_engine = main_engine
        self.strategy_name = strategy_name
        self.symbols = symbols or []
        self.setting = setting or {}
        self.active = False
        
        # 日志设置
        self.logger = logging.getLogger(f"Strategy.{strategy_name}")
        self.logger.setLevel(logging.INFO)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
    
    def init(self):
        """
        策略初始化
        """
        pass
    
    def start(self):
        """
        启动策略
        """
        self.active = True
        self.register_events()
        self.logger.info(f"策略{self.strategy_name}已启动")
    
    def stop(self):
        """
        停止策略
        """
        self.active = False
        self.unregister_events()
        self.logger.info(f"策略{self.strategy_name}已停止")
    
    def register_events(self):
        """
        注册事件处理函数
        """
        pass
    
    def unregister_events(self):
        """
        注销事件处理函数
        """
        pass
    
    def on_tick(self, tick):
        """
        Tick数据回调
        """
        pass
    
    def on_bar(self, bar):
        """
        K线数据回调
        """
        pass
    
    def on_trade(self, trade):
        """
        成交回调
        """
        pass
    
    def on_order(self, order):
        """
        订单状态回调
        """
        pass
    
    def on_position(self, position):
        """
        持仓回调
        """
        pass
    
    def buy(self, symbol, price, volume, order_type=None, trader_platform=None):
        """
        买入
        """
        pass
    
    def sell(self, symbol, price, volume, order_type=None, trader_platform=None):
        """
        卖出
        """
        pass
    
    def short(self, symbol, price, volume, order_type=None, trader_platform=None):
        """
        做空
        """
        pass
    
    def cover(self, symbol, price, volume, order_type=None, trader_platform=None):
        """
        平空
        """
        pass