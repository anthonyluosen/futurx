# -*- coding: utf-8 -*-

"""
Binance交易引擎简化版
用于在Binance交易所进行交易操作，支持实盘和测试网，以及模拟交易
"""

import time
import logging
import hmac
import hashlib
import urllib.parse
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
import requests
import math

class BinanceTraderEngine:
    """
    Binance交易引擎简化版
    用于在Binance交易所进行交易操作，支持实盘和测试网，以及模拟交易
    """
    
    def __init__(self):
        """
        初始化Binance交易引擎
        """
        # API配置
        self.api_key = ""
        self.api_secret = ""
        
        # 是否使用测试网
        self.use_testnet = False
        
        # 交易模式
        self.simulate_trading = False
        
        # 连接状态
        self.connected = False
        
        # 基础URL
        self.base_url = ""
        
        # 设置日志
        self.logger = logging.getLogger("BinanceTrader")
        self.logger.setLevel(logging.INFO)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
        
    def init_client(self, api_key: str = "", api_secret: str = "", use_testnet: bool = False, simulate_trading: bool = False):
        """
        初始化Binance客户端
        
        Args:
            api_key: API密钥
            api_secret: API密钥
            use_testnet: 是否使用测试网
            simulate_trading: 是否使用模拟交易
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.use_testnet = use_testnet
        self.simulate_trading = simulate_trading
        
        # 设置基础URL
        if self.use_testnet:
            self.base_url = "https://testnet.binancefuture.com"
        else:
            self.base_url = "https://fapi.binance.com"
        
        self.connected = True
        self.logger.info(f"Binance{'模拟' if simulate_trading else ''}{'测试网' if use_testnet else ''}交易引擎初始化成功")
    
    def _send_request(self, method: str, endpoint: str, params: Dict = None) -> Dict:
        """
        向Binance发送请求
        
        Args:
            method: HTTP方法 ('GET', 'POST', 'DELETE')
            endpoint: API端点路径
            params: 请求参数
        
        Returns:
            Dict: API响应
        """
        if not self.connected:
            return {"error": "未连接到Binance"}
            
        # 如果是模拟交易模式，则返回模拟消息
        if self.simulate_trading:
            return {"status": "success", "message": "模拟交易模式"}
            
        # 如果没有参数，创建一个空字典
        if params is None:
            params = {}
        
        # 添加时间戳
        params['timestamp'] = int(time.time() * 1000)
        
        # 将参数转换为查询字符串
        query_string = urllib.parse.urlencode(params)
        
        # 使用密钥创建签名
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        # 将签名添加到参数中
        query_string = f"{query_string}&signature={signature}"
        
        # 设置请求头
        headers = {
            'X-MBX-APIKEY': self.api_key
        }
        
        # 构建完整URL
        url = f"{self.base_url}{endpoint}"
        
        # 发送请求
        try:
            if method == 'GET':
                response = requests.get(f"{url}?{query_string}", headers=headers)
            elif method == 'POST':
                response = requests.post(f"{url}?{query_string}", headers=headers)
            elif method == 'DELETE':
                response = requests.delete(f"{url}?{query_string}", headers=headers)
            else:
                raise ValueError(f"不支持的HTTP方法: {method}")
            
            # 检查响应
            if response.status_code == 200:
                return response.json()
            else:
                error_msg = f"API请求失败: {response.status_code} - {response.text}"
                self.logger.error(error_msg)
                return {'error': response.text}
        except Exception as e:
            self.logger.error(f"发送请求时发生错误: {e}")
            return {'error': str(e)}

    # 基本市场数据功能
    def get_ticker_price(self, symbol: str) -> float:
        """
        获取当前市场价格
        
        Args:
            symbol: 交易对
            
        Returns:
            float: 当前价格
        """
        try:
            params = {'symbol': symbol}
            result = self._send_request('GET', '/fapi/v1/ticker/price', params)
            
            if 'error' in result:
                self.logger.error(f"获取{symbol}价格失败: {result['error']}")
                return 0
            
            price = float(result.get('price', 0))
            self.logger.info(f"获取{symbol}价格成功: {price}")
            return price
            
        except Exception as e:
            self.logger.error(f"获取{symbol}价格异常: {str(e)}")
            return 0
    
    def get_orderbook(self, symbol: str, limit: int = 5) -> Dict:
        """
        获取订单簿深度数据
        
        Args:
            symbol: 交易对
            limit: 获取的档位数量，默认5档
            
        Returns:
            Dict: 订单簿数据，包含bids和asks
        """
        params = {
            'symbol': symbol,
            'limit': limit
        }
        return self._send_request('GET', '/fapi/v1/depth', params)
    
    # 账户和持仓信息
    def get_account(self) -> Dict:
        """
        获取账户信息
        
        Returns:
            Dict: 账户信息
        """
        return self._send_request('GET', '/fapi/v2/account')
    
    def get_positions(self, symbol: str = None) -> List[Dict]:
        """
        获取持仓信息
        
        Args:
            symbol: 交易对，如果不指定则获取所有持仓
            
        Returns:
            List[Dict]: 持仓列表
        """
        params = {}
        if symbol:
            params['symbol'] = symbol
            
        result = self._send_request('GET', '/fapi/v2/positionRisk', params)
        return result if isinstance(result, list) else []
    
    def get_position_amount(self, symbol: str) -> float:
        """
        获取指定交易对的持仓数量
        
        Args:
            symbol: 交易对
            
        Returns:
            float: 持仓数量，正数表示多头，负数表示空头
        """
        positions = self.get_positions(symbol)
        
        # 如果没有找到持仓，返回0
        if not positions:
            return 0
            
        # 找到对应持仓
        position = None
        for pos in positions:
            if pos.get('symbol') == symbol:
                position = pos
                break
                
        if not position:
            return 0
            
        return float(position.get('positionAmt', 0))
    
    # 订单操作
    def place_order(self, symbol: str, side: str, order_type: str, 
                   quantity: float, price: float = None, time_in_force: str = 'GTC') -> Dict:
        """
        下单
        
        Args:
            symbol: 交易对
            side: 方向 ('BUY', 'SELL')
            order_type: 订单类型 ('LIMIT', 'MARKET')
            quantity: 数量
            price: 价格 (LIMIT单必填)
            time_in_force: 有效期 ('GTC', 'IOC', 'FOK')
            
        Returns:
            Dict: 下单结果
        """
        params = {
            'symbol': symbol,
            'side': side,
            'type': order_type,
            'quantity': quantity
        }
        
        if order_type == 'LIMIT':
            params['timeInForce'] = time_in_force
            params['price'] = price
            
        return self._send_request('POST', '/fapi/v1/order', params)
    
    def cancel_order(self, symbol: str, order_id: int) -> Dict:
        """
        撤销订单
        
        Args:
            symbol: 交易对
            order_id: 订单ID
            
        Returns:
            Dict: 撤单结果
        """
        params = {
            'symbol': symbol,
            'orderId': order_id
        }
        return self._send_request('DELETE', '/fapi/v1/order', params)
    
    def get_order(self, symbol: str, order_id: int) -> Dict:
        """
        查询订单
        
        Args:
            symbol: 交易对
            order_id: 订单ID
            
        Returns:
            Dict: 订单信息
        """
        params = {
            'symbol': symbol,
            'orderId': order_id
        }
        return self._send_request('GET', '/fapi/v1/order', params)
    
    def get_open_orders(self, symbol: str = None) -> List[Dict]:
        """
        获取当前挂单
        
        Args:
            symbol: 交易对
            
        Returns:
            List[Dict]: 挂单列表
        """
        params = {}
        if symbol:
            params['symbol'] = symbol
            
        result = self._send_request('GET', '/fapi/v1/openOrders', params)
        return result if isinstance(result, list) else []
    
    # 杠杆和保证金类型
    def set_leverage(self, symbol: str, leverage: int) -> Dict:
        """
        设置杠杆倍数
        
        Args:
            symbol: 交易对
            leverage: 杠杆倍数
            
        Returns:
            Dict: 设置结果
        """
        params = {
            'symbol': symbol,
            'leverage': leverage
        }
        return self._send_request('POST', '/fapi/v1/leverage', params)
    
    def set_margin_type(self, symbol: str, margin_type: str) -> Dict:
        """
        设置保证金类型
        
        Args:
            symbol: 交易对
            margin_type: 保证金类型 ('ISOLATED', 'CROSSED')
            
        Returns:
            Dict: 设置结果
        """
        params = {
            'symbol': symbol,
            'marginType': margin_type
        }
        return self._send_request('POST', '/fapi/v1/marginType', params)
    
    # 简单的交易辅助方法
    def buy_market(self, symbol: str, quantity: float) -> Dict:
        """
        市价买入
        
        Args:
            symbol: 交易对
            quantity: 数量
            
        Returns:
            Dict: 下单结果
        """
        return self.place_order(
            symbol=symbol,
            side='BUY',
            order_type='MARKET',
            quantity=quantity
        )
    
    def sell_market(self, symbol: str, quantity: float) -> Dict:
        """
        市价卖出
        
        Args:
            symbol: 交易对
            quantity: 数量
            
        Returns:
            Dict: 下单结果
        """
        return self.place_order(
            symbol=symbol,
            side='SELL',
            order_type='MARKET',
            quantity=quantity
        )
        
    def buy_limit(self, symbol: str, quantity: float, price: float) -> Dict:
        """
        限价买入
        
        Args:
            symbol: 交易对
            quantity: 数量
            price: 价格
            
        Returns:
            Dict: 下单结果
        """
        return self.place_order(
            symbol=symbol,
            side='BUY',
            order_type='LIMIT',
            quantity=quantity,
            price=price
        )
    
    def sell_limit(self, symbol: str, quantity: float, price: float) -> Dict:
        """
        限价卖出
        
        Args:
            symbol: 交易对
            quantity: 数量
            price: 价格
            
        Returns:
            Dict: 下单结果
        """
        return self.place_order(
            symbol=symbol,
            side='SELL',
            order_type='LIMIT',
            quantity=quantity,
            price=price
        )
