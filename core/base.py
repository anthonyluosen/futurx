from abc import ABC, abstractmethod
from typing import Dict, Optional
from dataclasses import dataclass, field, fields

@dataclass
class BaseData:
    """
    Any data object needs a gateway_name as source
    and should inherit base data.
    """

    gateway_name: str

    extra: Optional[dict] = field(default=None, init=False)
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
    
    