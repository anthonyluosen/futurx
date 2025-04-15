from abc import ABC, abstractmethod
from typing import Dict, Optional, List
from dataclasses import dataclass, field, fields
from .constant import OrderType, OrderSide, Exchange, Interval
from datetime import datetime
class BaseOnline(ABC):
    """在线数据基类"""
    @abstractmethod
    def get_realtime_quotes(self, code: str) -> Dict:
        pass
    @abstractmethod
    def get_realtime_quotes_list(self, code_list: List[str]) -> List[Dict]:
        pass
@dataclass
class BaseData:
    """
    Any data object needs a gateway_name as source
    and should inherit base data.
    """

    gateway_name: str

    extra: Optional[dict] = field(default=None, init=False)
@dataclass
class TickData(BaseData):
    """
    Tick data contains information about:
        * last trade in market
        * orderbook snapshot
        * intraday market statistics.
    """

    symbol: str
    exchange: Exchange
    datetime: datetime

    name: str = ""
    volume: float = 0
    turnover: float = 0
    open_interest: float = 0
    last_price: float = 0
    last_volume: float = 0
    limit_up: float = 0
    limit_down: float = 0

    open_price: float = 0
    high_price: float = 0
    low_price: float = 0
    pre_close: float = 0

    bid1: float = 0
    bid2: float = 0
    bid3: float = 0
    bid4: float = 0
    bid5: float = 0

    ask1: float = 0
    ask2: float = 0
    ask3: float = 0
    ask4: float = 0
    ask5: float = 0

    bidvol1: float = 0
    bidvol2: float = 0
    bidvol3: float = 0
    bidvol4: float = 0
    bidvol5: float = 0

    askvol1: float = 0
    askvol2: float = 0
    askvol3: float = 0
    askvol4: float = 0
    askvol5: float = 0

    localtime: datetime = None

    def __post_init__(self) -> None:
        """"""
        self.vt_symbol: str = f"{self.symbol}.{self.exchange.value}"

@dataclass
class BarData(BaseData):
    """
    Candlestick bar data of a certain trading period.
    """

    symbol: str
    exchange: Exchange
    datetime: datetime

    interval: Interval = None
    volume: float = 0
    turnover: float = 0
    open_interest: float = 0
    open_price: float = 0
    high_price: float = 0
    low_price: float = 0
    close_price: float = 0

    def __post_init__(self) -> None:
        """"""
        self.vt_symbol: str = f"{self.symbol}.{self.exchange.value}"

class BaseTrader(ABC):
    """
    量化交易接口基类，定义了统一的接口方法
    """
    def __init__(self):
        self.name = "BaseTrader"
        self.connected = False
    
    @abstractmethod
    def connect(self) -> bool:
        """连接交易接口"""
        pass
    
    @abstractmethod
    def disconnect(self) -> bool:
        """断开连接"""
        pass
    
    @abstractmethod
    def get_account_info(self) -> Dict:
        """获取账户信息"""
        pass
    
    @abstractmethod
    def get_positions(self) -> Dict:
        """获取持仓信息"""
        pass
    
    @abstractmethod
    def place_order(self, symbol: str, volume: float, price: Optional[float] = None, 
                    order_type:OrderType = OrderType.LIMIT,direction: OrderSide = OrderSide.BUY) -> str:
        """下单"""
        pass
    
    @abstractmethod
    def cancel_order(self, order_id: str) -> bool:
        """撤单"""
        pass
    
    @abstractmethod
    def get_orders(self) -> Dict:
        """获取订单信息"""
        pass 
    def order_info(self, order_id: str) -> Dict:
        """获取订单详情"""
        pass


class DataConverter(ABC):
    """行情数据转换器基类"""
    
    @abstractmethod
    def convert_realtime_quotes(self, data: Dict) -> Dict:
        """转换实时行情数据为统一格式
        "price",     # 现价
        "lastclose", # 昨收
        "open",      # 今开
        "high",      # 最高
        "low",       # 最低
        "bid1",      # 买一
        "bid2",      # 买二
        "bid3",      # 买三
        "bid4",      # 买四
        "bid5",      # 买五
        "ask1",      # 卖一
        "ask2",      # 卖二
        "ask3",      # 卖三
        "ask4",      # 卖四
        "ask5",      # 卖五
        "bidvol1",   # 买一量
        "bidvol2",   # 买二量
        "bidvol3",   # 买三量
        "bidvol4",   # 买四量
        "bidvol5",   # 买五量
        "askvol1",   # 卖一量
        "askvol2",   # 卖二量
        "askvol3",   # 卖三量
        "askvol4",   # 卖四量
        "askvol5",   # 卖五量
        """
        pass
    
    @abstractmethod
    def convert_klines(self, data: Dict) -> Dict:
        """转换K线数据为统一格式"""
        pass
        
    @abstractmethod
    def convert_minute_history(self, data: Dict) -> Dict:
        """转换历史分时数据为统一格式"""
        pass

    def convert_tick(self, data: Dict) -> Dict:
        """转换Tick数据为统一格式"""
        pass


class TraderConverter(ABC):
    """交易接口转换器基类"""
    
    @abstractmethod
    def convert_account_info(self, data: Dict) -> Dict:
        """转换账户信息为统一格式
        
        统一格式：
        {
            "account_id": str,          # 账户ID
            "total_value": float,       # 总资产
            "cash": float,              # 可用资金
            "frozen_cash": float,       # 冻结资金
            "stock_value": float,       # 持仓市值
        }
        """
        pass
    
    @abstractmethod
    def convert_positions(self, data: Dict) -> Dict:
        """转换持仓信息为统一格式
        
        统一格式DataFrame列：
        - security_type: str               # 股票类型
        - symbol: str               # 股票代码
        - name: str                # 股票名称
        - holding_qty: int              # 持仓数量
        - sellable_qty: int           # 可用数量
        - unsellable_qty: int          # 不可卖数量
        - total_cost: float        # 成本
        - lastest_price: float     # 现价
        - market_value: float      # 市值
        - profit: float           # 浮动盈亏
        - profit_ratio: float     # 盈亏比例(%)
        """

        pass
    
    @abstractmethod
    def convert_orders(self, data: Dict) -> Dict:
        """转换订单信息为统一格式
        
        统一格式DataFrame列：
        - order_id: str           # 订单ID
        - symbol: str            # 股票代码
        - direction: str         # 交易方向(BUY/SELL)
        - price: float          # 委托价格
        - volume: int           # 委托数量
        - filled: int           # 已成交数量
        - status: str           # 订单状态
        - order_time: datetime  # 委托时间
        """
        pass
    
    @abstractmethod
    def convert_trades(self, data: Dict) -> Dict:
        """转换成交信息为统一格式
        
        统一格式DataFrame列：
        - trade_id: str          # 成交ID
        - order_id: str         # 订单ID
        - symbol: str          # 股票代码
        - direction: str       # 交易方向
        - price: float        # 成交价格
        - volume: int         # 成交数量
        - trade_time: datetime # 成交时间
        """
        pass
    
    @abstractmethod
    def convert_order_status(self, data: Dict) -> Dict:
        """转换订单状态为统一格式"""
        pass
    
    