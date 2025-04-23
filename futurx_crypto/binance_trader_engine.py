# -*- coding: utf-8 -*-

"""
Binance交易引擎
用于在Binance交易所进行交易操作，支持实盘和测试网，以及模拟交易
"""

import time
import logging
import json
import hmac
import hashlib
import urllib.parse
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from threading import Thread, Lock
import requests
import math

from core.engine.main_engine import BaseEngine

class BinanceTraderEngine(BaseEngine):
    """
    Binance交易引擎
    用于在Binance交易所进行交易操作，支持实盘和测试网，以及模拟交易
    """
    
    def __init__(self, main_engine, event_engine, engine_name: str = "binance_trader"):
        """
        初始化Binance交易引擎
        
        Args:
            main_engine: 主引擎
            event_engine: 事件引擎
            engine_name: 引擎名称
        """
        super().__init__(main_engine, event_engine, engine_name)
        
        # API配置
        self.api_key = ""
        self.api_secret = ""
        
        # 是否使用测试网
        self.use_testnet = False
        
        # 交易模式
        self.simulate_trading = False
        
        # 连接状态
        self.connected = False
        
        # 线程锁
        self._lock = Lock()
        
        # 模拟交易订单字典
        self.simulate_orders = {}
        
        # 模拟交易ID计数器
        self.simulate_order_count = 0
        
        # 模拟账户余额
        self.simulate_balance = {"USDT": 10000.0}
        
        # 模拟持仓
        self.simulate_positions = {}
        
        # 基础URL
        self.base_url = ""
        
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
            
        # 如果是模拟交易模式，则直接返回模拟响应
        if self.simulate_trading:
            return self._simulate_request(method, endpoint, params)
            
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
    
    def _simulate_request(self, method: str, endpoint: str, params: Dict = None) -> Dict:
        """
        模拟Binance请求
        
        Args:
            method: HTTP方法 ('GET', 'POST', 'DELETE')
            endpoint: API端点路径
            params: 请求参数
        
        Returns:
            Dict: 模拟的API响应
        """
        if params is None:
            params = {}
            
        # 获取账户信息
        if endpoint == '/fapi/v2/account' and method == 'GET':
            return {
                'totalWalletBalance': str(self.simulate_balance.get("USDT", 10000.0)),
                'availableBalance': str(self.simulate_balance.get("USDT", 10000.0)),
                'totalUnrealizedProfit': '0.00000000'
            }
            
        # 获取持仓
        if endpoint == '/fapi/v2/positionRisk' and method == 'GET':
            symbol = params.get('symbol')
            positions = []
            
            if symbol:
                if symbol in self.simulate_positions:
                    # 返回特定交易对的持仓
                    positions.append(self._get_simulate_position(symbol))
            else:
                # 返回所有交易对的持仓
                for sym in self.simulate_positions:
                    positions.append(self._get_simulate_position(sym))
            
            # 如果没有持仓，返回空持仓
            if not positions and symbol:
                positions.append({
                    'symbol': symbol,
                    'positionAmt': '0',
                    'entryPrice': '0',
                    'markPrice': '0',
                    'unRealizedProfit': '0',
                    'notional': '0',
                    'isolatedWallet': '0',
                    'positionSide': 'BOTH'
                })
                
            return positions
            
        # 下单
        if endpoint == '/fapi/v1/order' and method == 'POST':
            result = self._simulate_place_order(params)
            # 更新模拟持仓
            if 'error' not in result and result.get('status') == 'FILLED':
                self._update_simulate_position(result)
            return result
            
        # 查询订单
        if endpoint == '/fapi/v1/order' and method == 'GET':
            order_id = params.get('orderId')
            if order_id in self.simulate_orders:
                return self.simulate_orders[order_id]
            return {'error': 'Order not found'}
            
        # 查询所有订单
        if endpoint == '/fapi/v1/openOrders' and method == 'GET':
            open_orders = []
            for order_id, order in self.simulate_orders.items():
                if order['status'] in ['NEW', 'PARTIALLY_FILLED']:
                    open_orders.append(order)
            return open_orders
            
        # 撤销订单
        if endpoint == '/fapi/v1/order' and method == 'DELETE':
            order_id = params.get('orderId')
            if order_id in self.simulate_orders:
                order = self.simulate_orders[order_id]
                if order['status'] in ['NEW', 'PARTIALLY_FILLED']:
                    order['status'] = 'CANCELED'
                    return {**order, 'cancelTime': int(time.time() * 1000)}
            return {'error': 'Order not found or already closed'}
            
        # 设置杠杆
        if endpoint == '/fapi/v1/leverage' and method == 'POST':
            return {
                'leverage': params.get('leverage', 1),
                'maxNotionalValue': '1000000',
                'symbol': params.get('symbol')
            }
            
        # 设置保证金类型
        if endpoint == '/fapi/v1/marginType' and method == 'POST':
            return {
                'code': 200,
                'msg': 'success'
            }
            
        # 获取价格
        if endpoint == '/fapi/v1/ticker/price' and method == 'GET':
            symbol = params.get('symbol', 'BTCUSDT')
            # 随机生成一个合理的价格
            import random
            if symbol == 'BTCUSDT':
                price = 30000 + random.random() * 5000
            elif symbol == 'ETHUSDT':
                price = 2000 + random.random() * 200
            else:
                price = 100 + random.random() * 10
                
            return {
                'symbol': symbol,
                'price': str(price)
            }
            
        # 交易规则
        if endpoint == '/fapi/v1/exchangeInfo' and method == 'GET':
            return {
                "symbols": [
                    {
                        "symbol": "BTCUSDT",
                        "filters": [
                            {
                                "filterType": "PRICE_FILTER",
                                "tickSize": "0.01"
                            },
                            {
                                "filterType": "LOT_SIZE",
                                "stepSize": "0.001"
                            }
                        ]
                    }
                ]
            }
        
        # 默认返回空数据
        return {}
    
    def _get_simulate_position(self, symbol: str) -> Dict:
        """
        获取模拟持仓数据
        
        Args:
            symbol: 交易对
            
        Returns:
            Dict: 持仓数据
        """
        position_data = self.simulate_positions.get(symbol, {
            'amount': 0,
            'entry_price': 0,
            'notional': 0  # 名义价值
        })
        
        # 获取当前价格
        ticker = self._simulate_request('GET', '/fapi/v1/ticker/price', {'symbol': symbol})
        mark_price = float(ticker.get('price', 0))
        
        amount = position_data.get('amount', 0)
        entry_price = position_data.get('entry_price', 0)
        notional = abs(amount * mark_price)
        
        # 计算未实现盈亏
        if amount > 0:  # 多头
            unrealized_profit = amount * (mark_price - entry_price)
        elif amount < 0:  # 空头
            unrealized_profit = amount * (entry_price - mark_price)
        else:
            unrealized_profit = 0
            
        return {
            'symbol': symbol,
            'positionAmt': str(amount),
            'entryPrice': str(entry_price),
            'markPrice': str(mark_price),
            'unRealizedProfit': str(unrealized_profit),
            'notional': str(notional),
            'isolatedWallet': str(notional * 0.1),  # 假设10%保证金率
            'positionSide': 'BOTH'
        }
    
    def _update_simulate_position(self, order: Dict) -> None:
        """
        更新模拟持仓
        
        Args:
            order: 订单信息
        """
        symbol = order.get('symbol')
        side = order.get('side')
        executed_qty = float(order.get('executedQty', 0))
        price = float(order.get('avgPrice', 0)) or float(order.get('price', 0))
        
        if not symbol or not executed_qty:
            return
            
        with self._lock:
            # 获取当前持仓
            position = self.simulate_positions.get(symbol, {'amount': 0, 'entry_price': 0, 'notional': 0})
            current_amount = position.get('amount', 0)
            current_entry_price = position.get('entry_price', 0)
            
            # 根据订单方向更新持仓
            if side == 'BUY':
                # 如果是开多仓或者减少空仓
                if current_amount >= 0:  # 原本就是多仓或无仓位
                    # 计算新的开仓均价
                    total_cost = current_amount * current_entry_price + executed_qty * price
                    new_amount = current_amount + executed_qty
                    new_entry_price = total_cost / new_amount if new_amount > 0 else 0
                else:  # 原本是空仓，现在减仓
                    executed_qty = min(abs(current_amount), executed_qty)  # 最多只能减到0
                    if abs(current_amount) > executed_qty:  # 减仓但仍有仓位
                        new_amount = current_amount + executed_qty  # 因为current_amount是负数
                        new_entry_price = current_entry_price
                    else:  # 完全平仓
                        new_amount = 0
                        new_entry_price = 0
            else:  # 'SELL'
                # 如果是开空仓或者减少多仓
                if current_amount <= 0:  # 原本就是空仓或无仓位
                    # 计算新的开仓均价
                    total_cost = abs(current_amount) * current_entry_price + executed_qty * price
                    new_amount = current_amount - executed_qty
                    new_entry_price = total_cost / abs(new_amount) if new_amount < 0 else 0
                else:  # 原本是多仓，现在减仓
                    executed_qty = min(current_amount, executed_qty)  # 最多只能减到0
                    if current_amount > executed_qty:  # 减仓但仍有仓位
                        new_amount = current_amount - executed_qty
                        new_entry_price = current_entry_price
                    else:  # 完全平仓
                        new_amount = 0
                        new_entry_price = 0
            
            # 更新持仓
            self.simulate_positions[symbol] = {
                'amount': new_amount,
                'entry_price': new_entry_price,
                'notional': abs(new_amount * price)
            }
    
    def _simulate_place_order(self, params: Dict) -> Dict:
        """
        模拟下单
        
        Args:
            params: 订单参数
            
        Returns:
            Dict: 模拟的订单响应
        """
        symbol = params.get('symbol')
        side = params.get('side')
        type = params.get('type')
        quantity = float(params.get('quantity', 0))
        price = float(params.get('price', 0)) if params.get('price') else 0
        
        # 生成订单ID
        self.simulate_order_count += 1
        order_id = self.simulate_order_count
        
        # 获取当前时间戳
        timestamp = int(time.time() * 1000)
        
        # 如果是市价单，获取模拟价格
        if type == 'MARKET' or not price:
            ticker_response = self._simulate_request('GET', '/fapi/v1/ticker/price', {'symbol': symbol})
            price = float(ticker_response.get('price', 10000))
        
        # 创建订单对象
        order = {
            'orderId': order_id,
            'symbol': symbol,
            'status': 'NEW',
            'price': str(price),
            'origQty': str(quantity),
            'executedQty': '0',
            'avgPrice': '0',
            'type': type,
            'side': side,
            'time': timestamp,
            'updateTime': timestamp
        }
        
        # 存储订单
        self.simulate_orders[order_id] = order
        
        # 如果是市价单，立即执行
        if type == 'MARKET':
            # 模拟执行
            order['status'] = 'FILLED'
            order['executedQty'] = str(quantity)
            order['avgPrice'] = str(price)
            
            # 更新余额 - 这里不再更新余额，因为合约交易是保证金交易
            
        return order
    
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
    
    def get_position_value(self, symbol: str) -> float:
        """
        获取指定交易对的持仓价值（以USDT计价）
        
        Args:
            symbol: 交易对
            
        Returns:
            float: 持仓价值
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
            
        return float(position.get('notional', 0))
    
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
    
    def get_symbol_precision(self, symbol: str) -> Tuple[int, int]:
        """
        获取交易对的价格精度和数量精度
        
        Args:
            symbol: 交易对
            
        Returns:
            Tuple[int, int]: (价格精度, 数量精度)
        """
        exchange_info = self._send_request('GET', '/fapi/v1/exchangeInfo')
        
        price_precision = 2  # 默认值
        quantity_precision = 3  # 默认值
        
        if 'error' not in exchange_info and 'symbols' in exchange_info:
            for symbol_info in exchange_info['symbols']:
                if symbol_info['symbol'] == symbol:
                    # 查找价格过滤器
                    for filter_info in symbol_info['filters']:
                        if filter_info['filterType'] == 'PRICE_FILTER':
                            tick_size = float(filter_info['tickSize'])
                            # 计算精度 (小数点后的位数)
                            price_precision = len(str(tick_size).split('.')[-1].rstrip('0'))
                        elif filter_info['filterType'] == 'LOT_SIZE':
                            step_size = float(filter_info['stepSize'])
                            # 计算精度
                            quantity_precision = len(str(step_size).split('.')[-1].rstrip('0'))
                    break
                    
        return price_precision, quantity_precision
    
    def get_symbol_info(self, symbol: str) -> Dict:
        """
        获取交易对的详细信息
        
        Args:
            symbol: 交易对
            
        Returns:
            Dict: 交易对信息
        """
        exchange_info = self._send_request('GET', '/fapi/v1/exchangeInfo')
        
        if 'error' not in exchange_info and 'symbols' in exchange_info:
            for symbol_info in exchange_info['symbols']:
                if symbol_info['symbol'] == symbol:
                    return symbol_info
                    
        return {}
    
    def format_price_quantity(self, symbol: str, price: float = None, quantity: float = None) -> Tuple[Optional[float], Optional[float]]:
        """
        按照交易对的精度要求格式化价格和数量
        
        Args:
            symbol: 交易对
            price: 价格，None表示不需要格式化
            quantity: 数量，None表示不需要格式化
            
        Returns:
            Tuple[Optional[float], Optional[float]]: (格式化后的价格, 格式化后的数量)
        """
        symbol_info = self.get_symbol_info(symbol)
        if not symbol_info:
            return price, quantity
            
        formatted_price = price
        formatted_quantity = quantity
        
        # 处理价格精度
        if price is not None:
            for filter_info in symbol_info.get('filters', []):
                if filter_info['filterType'] == 'PRICE_FILTER':
                    tick_size = float(filter_info['tickSize'])
                    # 使用向下取整确保不超过最大价格
                    formatted_price = float(int(price / tick_size) * tick_size)
                    # 确保格式化后的价格不低于最小价格
                    min_price = float(filter_info.get('minPrice', 0))
                    if formatted_price < min_price:
                        formatted_price = min_price
                    break
                    
        # 处理数量精度
        if quantity is not None:
            for filter_info in symbol_info.get('filters', []):
                if filter_info['filterType'] == 'LOT_SIZE':
                    step_size = float(filter_info['stepSize'])
                    # 使用向下取整确保不超过最大数量
                    formatted_quantity = float(int(quantity / step_size) * step_size)
                    # 确保格式化后的数量不低于最小数量
                    min_qty = float(filter_info.get('minQty', 0))
                    if formatted_quantity < min_qty:
                        formatted_quantity = min_qty
                    break
                    
            # 检查最小名义价值
            if formatted_quantity is not None and formatted_price is not None:
                for filter_info in symbol_info.get('filters', []):
                    if filter_info['filterType'] == 'MIN_NOTIONAL':
                        min_notional = float(filter_info.get('notional', 100))
                        current_notional = formatted_quantity * (formatted_price or price)
                        if current_notional < min_notional:
                            # 调整数量以满足最小名义价值
                            min_qty = float(symbol_info.get('minQty', 0.001))
                            step_size = float(filter_info.get('stepSize', 0.001))
                            needed_qty = min_notional / (formatted_price or price)
                            # 向上取整到步长的倍数
                            formatted_quantity = max(min_qty, float(int(needed_qty / step_size + 1) * step_size))
                        break
                    
        return formatted_price, formatted_quantity
    
    def get_ticker_price(self, symbol: str) -> float:
        """
        获取当前市场价格
        
        Args:
            symbol: 交易对
            
        Returns:
            float: 当前价格
        """
        params = {'symbol': symbol}
        result = self._send_request('GET', '/fapi/v1/ticker/price', params)
        
        if 'error' in result:
            return 0
            
        return float(result.get('price', 0))
    
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
    
    def order_factor(self, symbol: str, factor: float, multiplier: float = 1.0, 
                    order_type: str = 'MARKET', price: float = None) -> Dict:
        """
        根据目标保证金值调整仓位
        
        Args:
            symbol: 交易对
            factor: 目标保证金值(USDT)，正数为做多，负数为做空
            multiplier: 杠杆倍数
            order_type: 订单类型 ('LIMIT', 'MARKET')
            price: 价格 (LIMIT单必填)
            
        Returns:
            Dict: 操作结果
        """
        # 获取当前持仓和价格信息
        current_position = self.get_position_amount(symbol)
        current_price = price if price and order_type == 'LIMIT' else self.get_ticker_price(symbol)
        
        if current_price <= 0:
            return {'error': '无法获取有效价格'}
        
        # 获取杠杆信息
        leverage = multiplier
        
        # 计算当前持仓的保证金价值
        current_margin = abs(current_position * current_price) / leverage
        
        # 目标保证金值
        target_margin = abs(factor)
        
        # 目标持仓方向
        target_direction = 'LONG' if factor >= 0 else 'SHORT'
        
        # 当前持仓方向
        current_direction = 'LONG' if current_position >= 0 else 'SHORT'
        
        # 计算目标持仓数量
        if target_direction == 'LONG':
            target_position = (target_margin * leverage) / current_price
        else:
            target_position = -(target_margin * leverage) / current_price
        
        # 计算需要调整的数量
        position_diff = target_position - current_position
        
        # 如果调整量很小，不进行操作
        if abs(position_diff) < 0.001:
            return {
                'status': 'NO_CHANGE',
                'message': '当前持仓已接近目标持仓',
                'current_margin': current_margin,
                'target_margin': target_margin,
                'current_position': current_position,
                'target_position': target_position
            }
        
        # 判断交易方向
        side = 'BUY' if position_diff > 0 else 'SELL'
        quantity = abs(position_diff)
        
        # 获取交易对信息
        symbol_info = self.get_symbol_info(symbol)
        if not symbol_info:
            return {'error': f'无法获取{symbol}的交易信息'}
        
        # 格式化数量以符合交易规则
        formatted_quantity = self._format_quantity(symbol, symbol_info, quantity)
        
        # 格式化价格以符合交易规则
        formatted_price = None
        if order_type == 'LIMIT':
            formatted_price = self._format_price(symbol, symbol_info, current_price, side)
        
        # 下单
        result = self.place_order(
            symbol=symbol,
            side=side,
            order_type=order_type,
            quantity=formatted_quantity,
            price=formatted_price
        )
        
        # 添加因子信息到结果
        if 'error' not in result:
            result['factor'] = factor
            result['leverage'] = leverage
            result['current_margin'] = current_margin
            result['target_margin'] = target_margin
            result['current_position'] = current_position
            result['target_position'] = target_position
            result['position_diff'] = position_diff
            result['formatted_quantity'] = formatted_quantity
            if order_type == 'LIMIT':
                result['formatted_price'] = formatted_price
        
        return result
    
    def _format_quantity(self, symbol: str, symbol_info: dict, quantity: float) -> float:
        """
        格式化数量以符合交易规则
        
        Args:
            symbol: 交易对
            symbol_info: 交易对信息
            quantity: 原始数量
            
        Returns:
            float: 格式化后的数量
        """
        step_size = None
        min_qty = None
        
        # 获取步长和最小数量
        for filter_item in symbol_info.get('filters', []):
            if filter_item['filterType'] == 'LOT_SIZE':
                step_size = float(filter_item['stepSize'])
                min_qty = float(filter_item.get('minQty', 0))
                break
        
        # 使用默认值
        if not step_size:
            step_size = 0.001
        if not min_qty:
            min_qty = 0.001
        
        # 计算数量精度
        qty_precision = len(str(step_size).split('.')[-1].rstrip('0')) if '.' in str(step_size) else 0
        
        # 向下取整到步长的倍数
        steps = int(quantity / step_size)
        adjusted_quantity = steps * step_size
        
        # 确保不小于最小数量
        if adjusted_quantity < min_qty:
            adjusted_quantity = min_qty
        
        # 格式化
        return round(adjusted_quantity, qty_precision)
    
    def _format_price(self, symbol: str, symbol_info: dict, price: float, side: str) -> float:
        """
        格式化价格以符合交易规则
        
        Args:
            symbol: 交易对
            symbol_info: 交易对信息
            price: 原始价格
            side: 交易方向
            
        Returns:
            float: 格式化后的价格
        """
        tick_size = None
        
        # 获取价格步长
        for filter_item in symbol_info.get('filters', []):
            if filter_item['filterType'] == 'PRICE_FILTER':
                tick_size = float(filter_item['tickSize'])
                break
        
        # 使用默认值
        if not tick_size:
            tick_size = 0.01
        
        # 计算价格精度
        price_precision = len(str(tick_size).split('.')[-1].rstrip('0')) if '.' in str(tick_size) else 0
        
        # 调整价格到步长的倍数
        steps = int(price / tick_size)
        
        # 买入时价格稍高，卖出时价格稍低
        if side == 'BUY':
            adjusted_price = (steps + 1) * tick_size  # 提高一个步长
        else:
            adjusted_price = steps * tick_size  # 使用当前步长
        
        # 格式化
        return round(adjusted_price, price_precision)
    
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
    
    def place_order_with_level(self, symbol: str, side: str, quantity: float, level: int = 0) -> Dict:
        """
        根据当前市场的价格档位直接下单
        
        Args:
            symbol: 交易对
            side: 方向 ('BUY', 'SELL')
            quantity: 数量
            level: 价格档位，0表示最优价，1表示次优价，以此类推
            
        Returns:
            Dict: 下单结果
        """
        # 获取当前订单簿
        orderbook = self.get_orderbook(symbol)
        
        if 'error' in orderbook:
            return {'error': f'获取订单簿失败: {orderbook.get("error")}'}
        
        # 确保level在合理范围内
        available_levels = min(len(orderbook.get('bids', [])), len(orderbook.get('asks', [])))
        if available_levels == 0:
            return {'error': '订单簿为空'}
            
        level = max(0, min(level, available_levels - 1))
        
        # 根据交易方向选择价格
        if side == 'BUY':
            # 买入使用卖单价格(asks)
            price = float(orderbook['asks'][level][0])
            self.logger.info(f"买入 {symbol}，使用第{level}档卖价: {price}")
        else:
            # 卖出使用买单价格(bids)
            price = float(orderbook['bids'][level][0])
            self.logger.info(f"卖出 {symbol}，使用第{level}档买价: {price}")
        
        # 下限价单
        return self.place_order(
            symbol=symbol,
            side=side,
            order_type='LIMIT',
            quantity=quantity,
            price=price,
            time_in_force='GTC'  # 成交为止
        ) 
    
    def order_factor_with_level(self, symbol: str, factor: float, multiplier: float = 1.0, level: int = 0) -> Dict:
        """
        根据因子值和订单簿价格档位调整仓位
        
        Args:
            symbol: 交易对
            factor: 因子值
            multiplier: 乘数，用于计算目标仓位
            level: 价格档位，0表示最优价，1表示次优价，以此类推
            
        Returns:
            Dict: 操作结果
        """
        # 计算目标仓位（以USDT计价）
        target_value = factor * multiplier
        
        # 获取当前持仓量
        current_amount = self.get_position_amount(symbol)
        
        # 获取当前市场价格
        current_price = self.get_ticker_price(symbol)
        if current_price <= 0:
            return {'error': '无法获取当前价格'}
        
        # 计算当前持仓价值
        current_value = current_amount * current_price
        
        # 计算持仓差额
        value_diff = target_value - current_value
        
        # 如果差额很小，不进行操作
        if abs(value_diff) < 1:  # 小于1 USDT不操作
            return {'status': 'NO_CHANGE', 'message': '当前仓位已接近目标仓位'}
        
        # 根据调整方向确定买卖方向
        if value_diff > 0:
            side = 'BUY'
        else:
            side = 'SELL'
            value_diff = -value_diff  # 转为正数
        
        # 获取订单簿深度数据
        orderbook = self.get_orderbook(symbol)
        if 'error' in orderbook:
            return {'error': f'获取订单簿失败: {orderbook.get("error")}'}
        
        # 确保level在合理范围内
        available_levels = min(len(orderbook.get('bids', [])), len(orderbook.get('asks', [])))
        if available_levels == 0:
            return {'error': '订单簿为空'}
            
        level = max(0, min(level, available_levels - 1))
        
        # 根据交易方向选择价格
        if side == 'BUY':
            # 买入使用卖单价格(asks)
            price = float(orderbook['asks'][level][0])
        else:
            # 卖出使用买单价格(bids)
            price = float(orderbook['bids'][level][0])
        
        # 计算需要调整的数量
        quantity = value_diff / price
        
        # 获取交易对的价格精度和数量精度
        price_precision, quantity_precision = self.get_symbol_precision(symbol)
        
        # 四舍五入到合适精度
        quantity = round(quantity, quantity_precision)
        
        # 如果数量太小，不进行操作
        min_qty = 10 ** (-quantity_precision)
        if quantity < min_qty:
            return {
                'status': 'NO_CHANGE', 
                'message': '调整数量太小',
                'factor': factor,
                'target_value': target_value,
                'current_value': current_value,
                'quantity': quantity
            }
        
        # 下单
        result = self.place_order(
            symbol=symbol,
            side=side,
            order_type='LIMIT',
            quantity=quantity,
            price=price
        )
        
        # 添加因子信息到结果
        if 'error' not in result:
            result['factor'] = factor
            result['target_value'] = target_value
            result['current_value'] = current_value
            result['value_diff'] = value_diff
            result['price'] = price
            result['level'] = level
        
        return result