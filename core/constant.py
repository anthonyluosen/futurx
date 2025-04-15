from enum import Enum
from dataclasses import dataclass, field, fields
from datetime import datetime
from typing import Dict, Optional, List, Union, Any
from copy import deepcopy
from abc import ABC, abstractmethod
from datetime import datetime

class OrderStatus(Enum):
    """订单状态"""
    PENDING = "PENDING"  # 待处理
    FILLED = "FILLED"    # 已成交
    CANCELLED = "CANCELLED"  # 已取消
    REJECTED = "REJECTED"  # 已拒绝
    PARTIALLY_FILLED = "PARTIALLY_FILLED"  # 部分成交
    
class OrderType(Enum):
    """订单类型"""
    MARKET = "MARKET"  # 市价单
    LIMIT = "LIMIT"    # 限价单
    
class OrderSide(Enum):
    """交易方向"""
    BUY = "BUY"    # 买入
    SELL = "SELL"  # 卖出
    
class SecurityType(Enum):
    """证券类型"""
    STOCK = "STOCK"  # 股票
    ETF = "ETF"      # ETF基金
    CRYPTO = "CRYPTO" # 数字货币

class EngineType(Enum):
    """组件类型"""
    TRADER = "trader"      # 交易接口
    DATA = "data"          # 数据源
    ENGINE = "engine"      # 功能引擎

# 数据频率类型
class FreqType(Enum):
    """数据频率类型"""
    M1 = "M1"    # 1分钟
    M5 = "M5"    # 5分钟
    M15 = "M15"  # 15分钟
    M30 = "M30"  # 30分钟
    M60 = "M60"  # 60分钟
    EOD = "EOD"  # 日线

# 价格类型
class PriceType(Enum):
    """价格类型"""
    OPEN = "OPEN"    # 开盘价
    HIGH = "HIGH"    # 最高价
    LOW = "LOW"      # 最低价
    CLOSE = "CLOSE"  # 收盘价
    
# 常用类型别名
SymbolType = str
PriceValueType = float
QuantityType = int
DateType = str
TimeIndexType = int
DateIndexType = int

# 持仓信息类型
PositionInfo = Dict[str, Union[str, int, float]]

# 订单信息类型
OrderInfo = Dict[str, Any] 

class Interval(Enum):
    """
    Interval of bar data.
    """
    MINUTE = "1m"
    HOUR = "1h"
    DAILY = "d"
    WEEKLY = "w"
    TICK = "tick"
class Exchange(Enum):
    """
    Exchange.
    """
    # Chinese
    CFFEX = "CFFEX"         # China Financial Futures Exchange
    SHFE = "SHFE"           # Shanghai Futures Exchange
    CZCE = "CZCE"           # Zhengzhou Commodity Exchange
    DCE = "DCE"             # Dalian Commodity Exchange
    INE = "INE"             # Shanghai International Energy Exchange
    GFEX = "GFEX"           # Guangzhou Futures Exchange
    SSE = "SSE"             # Shanghai Stock Exchange
    SZSE = "SZSE"           # Shenzhen Stock Exchange
    BSE = "BSE"             # Beijing Stock Exchange
    SHHK = "SHHK"           # Shanghai-HK Stock Connect
    SZHK = "SZHK"           # Shenzhen-HK Stock Connect
    SGE = "SGE"             # Shanghai Gold Exchange
    WXE = "WXE"             # Wuxi Steel Exchange
    CFETS = "CFETS"         # CFETS Bond Market Maker Trading System
    XBOND = "XBOND"         # CFETS X-Bond Anonymous Trading System

    # Global
    SMART = "SMART"         # Smart Router for US stocks
    NYSE = "NYSE"           # New York Stock Exchnage
    NASDAQ = "NASDAQ"       # Nasdaq Exchange
    ARCA = "ARCA"           # ARCA Exchange
    EDGEA = "EDGEA"         # Direct Edge Exchange
    ISLAND = "ISLAND"       # Nasdaq Island ECN
    BATS = "BATS"           # Bats Global Markets
    IEX = "IEX"             # The Investors Exchange
    AMEX = "AMEX"           # American Stock Exchange
    TSE = "TSE"             # Toronto Stock Exchange
    NYMEX = "NYMEX"         # New York Mercantile Exchange
    COMEX = "COMEX"         # COMEX of CME
    GLOBEX = "GLOBEX"       # Globex of CME
    IDEALPRO = "IDEALPRO"   # Forex ECN of Interactive Brokers
    CME = "CME"             # Chicago Mercantile Exchange
    ICE = "ICE"             # Intercontinental Exchange
    SEHK = "SEHK"           # Stock Exchange of Hong Kong
    HKFE = "HKFE"           # Hong Kong Futures Exchange
    SGX = "SGX"             # Singapore Global Exchange
    CBOT = "CBT"            # Chicago Board of Trade
    CBOE = "CBOE"           # Chicago Board Options Exchange
    CFE = "CFE"             # CBOE Futures Exchange
    DME = "DME"             # Dubai Mercantile Exchange
    EUREX = "EUX"           # Eurex Exchange
    APEX = "APEX"           # Asia Pacific Exchange
    LME = "LME"             # London Metal Exchange
    BMD = "BMD"             # Bursa Malaysia Derivatives
    TOCOM = "TOCOM"         # Tokyo Commodity Exchange
    EUNX = "EUNX"           # Euronext Exchange
    KRX = "KRX"             # Korean Exchange
    OTC = "OTC"             # OTC Product (Forex/CFD/Pink Sheet Equity)
    IBKRATS = "IBKRATS"     # Paper Trading Exchange of IB

    # Special Function
    LOCAL = "LOCAL"         # For local generated data


class EventType(Enum):
    """事件类型枚举"""
    ORDER = "ORDER"  # 订单事件
    TRADE = "TRADE"  # 成交事件
    POSITION = "POSITION"  # 持仓事件
    ACCOUNT = "ACCOUNT"  # 账户事件
    ERROR = "ERROR"  # 错误事件
    TIMER = "TIMER"  # 计时器事件
    
    TICK = "TICK"  # 行情事件
    BAR1MIN = "BAR1MIN"  # 1分钟K线
    BAR5MIN = "BAR5MIN"  # 5分钟K线
    BAR15MIN = "BAR15MIN"  # 15分钟K线
    BAR30MIN = "BAR30MIN"  # 30分钟K线
    BAR1HOUR = "BAR1HOUR"  # 1小时K线
    BAR4HOUR = "BAR4HOUR"  # 4小时K线
    
class OrderStatus(Enum):
    """订单状态"""
    SUBMITTING = "提交中"
    SUBMITTED = "已提交"
    PARTIAL_FILLED = "部分成交"
    FILLED = "全部成交"
    CANCELLED = "已撤销"
    REJECTED = "拒单"

@dataclass
class Event:
    """事件对象"""
    type: EventType  # 事件类型
    data: Any  # 事件数据
    timestamp: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        """初始化后的类型检查"""
        self.data = deepcopy(self.data)

    def clone(self) -> 'Event':
        """使用fields方法创建对象副本"""
        new_event = Event(type=self.type, data=None, timestamp=self.timestamp)
        
        if isinstance(self.data, Order):
            new_order = Order(
                order_id=None,
                symbol="",
                direction=OrderSide.BUY,
                price=0,
                volume=0,
                status=OrderStatus.SUBMITTING,
                create_time=datetime.now()
            )
            for field in fields(self.data):
                setattr(new_order, field.name, getattr(self.data, field.name))
            new_event.data = new_order
        else:
            new_event.data = deepcopy(self.data)  # 对于非Order对象，仍使用deepcopy
            
        return new_event
    
@dataclass
class Order:
    """订单对象"""
    
    order_id: Optional[str]
    symbol: str
    direction: OrderSide
    price: float # 想要交易的价格
    volume: float
    status: OrderStatus
    create_time: datetime
    filled_volume: float = 0
    trader_platform: str = ""
    is_active: bool = True
    order_type: OrderType = OrderType.MARKET
    is_finished: bool = False
    strategy_name: str = ""
    traded_price: Optional[float] = None
    execution_strategy: Optional[str] = None
    security_type: SecurityType = SecurityType.STOCK
    parent_id: str = None
    limit_price: Optional[float] = None
    amt: Optional[float] = None
    # 届时会将算法单写入order

    def __post_init__(self):
        """初始化后的类型检查"""
        self.security_type = get_security_type(self.symbol)

    def get_extra_params(self) -> dict:
        """获取额外参数"""
        extra_params = {}
        
        # 根据证券类型添加特定参数
        if self.security_type == SecurityType.CRYPTO:
            if hasattr(self, 'leverage'):
                extra_params['leverage'] = getattr(self, 'leverage', 1)
                
        return extra_params

# 动态创建类
class DictToClass:
    def __init__(self, data):
        for key, value in data.items():
            setattr(self, key, value)