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
        
        # 交易对信息缓存
        self.exchange_info = {}
        self.symbols_info = {}
        self.last_info_update = 0
        
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
        # self.logger.info(f"Binance{'模拟' if simulate_trading else ''}{'测试网' if use_testnet else ''}交易引擎初始化成功")
        
        # 初始化时获取交易对信息
        self.update_exchange_info()
    
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
            # self.logger.info(f"获取{symbol}价格成功: {price}")
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
        result = self._send_request('POST', '/fapi/v1/marginType', params)
        
        # 处理"无需更改保证金类型"的情况
        if isinstance(result, dict) and 'error' in result:
            error_text = result['error']
            if '"code":-4046' in error_text and '"msg":"No need to change margin type."' in error_text:
                self.logger.info(f"保证金类型已经是{margin_type}，无需更改")
                return {
                    'symbol': symbol,
                    'marginType': margin_type,
                    'message': '保证金类型无需更改'
                }
        
        return result
    
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

    def update_exchange_info(self) -> bool:
        """
        更新交易所信息，获取所有交易对的规格
        
        Returns:
            bool: 是否更新成功
        """
        try:
            # 只有在连接成功后才能获取信息
            if not self.connected:
                self.logger.error("未连接到Binance，无法获取交易所信息")
                return False
                
            # 获取交易所信息
            result = self._send_request('GET', '/fapi/v1/exchangeInfo')
            
            if 'error' in result:
                self.logger.error(f"获取交易所信息失败: {result['error']}")
                return False
                
            # 更新交易所信息缓存
            self.exchange_info = result
            self.last_info_update = int(time.time())
            
            # 整理交易对信息便于查询
            self.symbols_info = {}
            for symbol_data in result.get('symbols', []):
                symbol = symbol_data.get('symbol')
                if symbol:
                    self.symbols_info[symbol] = {
                        'baseAsset': symbol_data.get('baseAsset', ''),
                        'quoteAsset': symbol_data.get('quoteAsset', ''),
                        'status': symbol_data.get('status', ''),
                        'filters': {}
                    }
                    
                    # 整理过滤器信息
                    for filter_data in symbol_data.get('filters', []):
                        filter_type = filter_data.get('filterType')
                        if filter_type:
                            self.symbols_info[symbol]['filters'][filter_type] = filter_data
            
            # self.logger.info(f"成功更新交易所信息，共{len(self.symbols_info)}个交易对")
            return True
            
        except Exception as e:
            self.logger.error(f"更新交易所信息时发生错误: {e}")
            return False
            
    def get_symbol_info(self, symbol: str) -> Dict:
        """
        获取指定交易对的信息
        
        Args:
            symbol: 交易对名称
            
        Returns:
            Dict: 交易对信息
        """
        # 检查是否需要更新信息（每小时更新一次）
        if int(time.time()) - self.last_info_update > 3600:
            self.update_exchange_info()
            
        # 如果没有缓存信息，尝试获取
        if not self.symbols_info:
            self.update_exchange_info()
            
        # 返回交易对信息
        symbol = symbol.upper()
        if symbol in self.symbols_info:
            return self.symbols_info[symbol]
        else:
            self.logger.warning(f"未找到交易对{symbol}的信息")
            return {}
            
    def get_price_filter(self, symbol: str) -> Tuple[float, int]:
        """
        获取交易对的价格过滤器信息
        
        Args:
            symbol: 交易对名称
            
        Returns:
            Tuple[float, int]: (最小价格变动单位, 价格精度)
        """
        symbol_info = self.get_symbol_info(symbol)
        price_filter = symbol_info.get('filters', {}).get('PRICE_FILTER', {})
        
        if price_filter:
            tick_size = float(price_filter.get('tickSize', 0.1))
            
            # 计算精度（小数位数）
            tick_str = str(tick_size)
            if '.' in tick_str:
                precision = len(tick_str.split('.')[1].rstrip('0'))
            else:
                precision = 0
                
            return tick_size, precision
            
        # 返回默认值
        symbol = symbol.upper()
        if symbol.startswith('BTC'):
            return 0.1, 1
        elif symbol.startswith('ETH'):
            return 0.01, 2
        else:
            return 0.01, 2
            
    def get_lot_size_filter(self, symbol: str) -> Tuple[float, int]:
        """
        获取交易对的数量过滤器信息
        
        Args:
            symbol: 交易对名称
            
        Returns:
            Tuple[float, int]: (最小数量变动单位, 数量精度)
        """
        symbol_info = self.get_symbol_info(symbol)
        lot_size = symbol_info.get('filters', {}).get('LOT_SIZE', {})
        
        if lot_size:
            step_size = float(lot_size.get('stepSize', 0.001))
            
            # 计算精度（小数位数）
            step_str = str(step_size)
            if '.' in step_str:
                precision = len(step_str.split('.')[1].rstrip('0'))
            else:
                precision = 0
                
            return step_size, precision
            
        # 返回默认值
        symbol = symbol.upper()
        if symbol.startswith('BTC'):
            return 0.001, 3
        elif symbol.startswith('ETH'):
            return 0.001, 3
        else:
            return 0.1, 1
    
    def order_target_amount(self, symbol: str, target_margin: float, leverage: int, 
                           order_type: str = "MARKET") -> Dict:
        """
        根据目标保证金金额调整仓位
        
        Args:
            symbol: 交易对，如 "BTCUSDT"
            target_margin: 目标保证金金额(USDT)，正数表示做多，负数表示做空
            leverage: 杠杆倍数，范围1-125，根据具体交易对不同而不同
            order_type: 订单类型，"MARKET"或"LIMIT"
            
        Returns:
            Dict: 下单结果
        """
        try:
            # 获取交易对信息
            symbol_info = self.get_symbol_info(symbol)
            if not symbol_info:
                return {'error': f'获取{symbol}信息失败'}
            
            # 获取交易对价格
            price = self.get_ticker_price(symbol)
            if price <= 0:
                return {'error': f'获取{symbol}价格失败'}
            
            # self.logger.info(f"当前{symbol}价格: {price}")
            
            # 获取当前持仓
            positions = self.get_positions(symbol)
            
            # 查找当前持仓和杠杆信息
            current_position = 0.0
            current_leverage = 0
            for pos in positions:
                if pos.get('symbol') == symbol.upper():
                    current_position = float(pos.get('positionAmt', 0))
                    # 获取当前杠杆
                    current_leverage = int(pos.get('leverage', 0))
                    break
            
            # self.logger.info(f"当前持仓数量: {current_position}")
            
            # 检查杠杆是否一致
            if current_position != 0 and current_leverage != 0 and current_leverage != leverage:
                warning_msg = f"警告: 当前持仓杠杆({current_leverage})与目标杠杆({leverage})不一致，将使用目标杠杆({leverage})进行调整"
                self.logger.warning(warning_msg)
                print(warning_msg)
            
            # 设置杠杆
            leverage_result = self.set_leverage(symbol, leverage)
            # self.logger.info(f"设置杠杆倍数结果: {leverage_result}")
            
            # 设置保证金类型为逐仓
            margin_result = self.set_margin_type(symbol, "ISOLATED")
            # self.logger.info(f"设置保证金类型结果: {margin_result}")
            
            # 计算目标持仓数量
            # 目标持仓数量 = 目标保证金金额 * 杠杆倍数 / 价格
            # 如果目标保证金为负，表示做空
            target_position = (target_margin * leverage) / price
            
            # self.logger.info(f"目标持仓数量: {target_position}")
            
            # 计算需要调整的数量
            position_diff = target_position - current_position
            
            # 如果差额很小，不做调整
            precision = 5
            if abs(position_diff) < 10**(-precision):
                # self.logger.info("当前持仓已经接近目标持仓，无需调整")
                return {
                    'status': 'NO_CHANGE',
                    'message': '当前持仓已经接近目标持仓，无需调整',
                    'current_position': current_position,
                    'current_leverage': current_leverage,
                    'target_position': target_position,
                    'target_leverage': leverage,
                    'position_diff': position_diff
                }
            
            # 确定交易方向
            side = "BUY" if position_diff > 0 else "SELL"
            
            # 计算需要调整的合约数量
            contract_amount = abs(position_diff)
            
            # 币安的最小名义价值要求通常是5-10 USDT
            min_notional = 5.0
            
            # 检查名义价值是否满足最小要求
            notional_value = contract_amount * price
            if notional_value < min_notional:
                self.logger.warning(f"计算的调整名义价值 {notional_value:.2f} USDT 小于最小要求 {min_notional} USDT")
                # 如果调整量太小，考虑是否要强制调整
                if abs(position_diff) < (min_notional / price / leverage):
                    self.logger.warning("调整量太小，无法满足最小交易要求，跳过调整")
                    return {
                        'status': 'TOO_SMALL',
                        'message': '调整量太小，无法满足最小交易要求',
                        'current_position': current_position,
                        'current_leverage': current_leverage,
                        'target_position': target_position,
                        'target_leverage': leverage,
                        'position_diff': position_diff,
                        'min_required_diff': min_notional / price / leverage
                    }
                # 调整合约数量以满足最小名义价值要求
                contract_amount = min_notional / price
                notional_value = contract_amount * price
                # self.logger.info(f"调整后合约数量: {contract_amount}, 名义价值: {notional_value:.2f} USDT")
            
            # 获取数量精度和最小变动单位
            try:
                step_size, quantity_precision = self.get_lot_size_filter(symbol)
                # self.logger.info(f"获取到{symbol}数量精度: {quantity_precision}, 最小数量变动单位: {step_size}")
                
                # 确保数量符合最小变动单位
                contract_amount = math.floor(contract_amount / step_size) * step_size
            except Exception as e:
                self.logger.error(f"获取数量精度失败: {e}, 使用默认值")
                # 使用默认值
                symbol_lower = symbol.upper()
                if symbol_lower.startswith("BTC"):
                    quantity_precision = 3
                elif symbol_lower.startswith("ETH"):
                    quantity_precision = 3
                else:
                    quantity_precision = 1
            
            # 四舍五入到指定精度
            contract_amount = round(contract_amount, quantity_precision)
            
            trade_info = (
                f"下单信息:\n"
                f"交易对: {symbol}\n"
                f"方向: {side}\n"
                f"当前持仓: {current_position} (杠杆: {current_leverage if current_leverage > 0 else '未知'}倍)\n"
                f"目标持仓: {target_position} (杠杆: {leverage}倍)\n"
                f"调整数量: {contract_amount}\n"
                f"价格: {price}\n"
                f"名义价值: {contract_amount * price:.2f} USDT"
            )
            # self.logger.info(trade_info)
            
            # 检查调整数量是否为0，如果是则不发送下单请求
            if contract_amount <= 0:
                # self.logger.info("调整数量为0或负数，无需发送下单请求")
                return {
                    'status': 'NO_ACTION',
                    'message': '调整数量为0或负数，无需发送下单请求',
                    'current_position': current_position,
                    'current_leverage': current_leverage,
                    'target_position': target_position,
                    'target_leverage': leverage,
                    'position_diff': position_diff,
                    'adjusted_amount': contract_amount
                }
            
            # 执行下单
            if order_type == "MARKET":
                result = self.place_order(
                    symbol=symbol,
                    side=side,
                    order_type="MARKET",
                    quantity=contract_amount
                )
            else:
                # 对于限价单，需要提供价格
                # 这里可以设置比当前价格略低/高的价格，视交易策略而定
                price_offset = 0.005  # 价格偏移0.5%
                limit_price = price * (1 - price_offset) if side == "BUY" else price * (1 + price_offset)
                
                # 获取价格精度和最小价格变动单位
                try:
                    tick_size, price_precision = self.get_price_filter(symbol)
                    # self.logger.info(f"获取到{symbol}价格精度: {price_precision}, 最小价格变动单位: {tick_size}")
                    
                    # 确保价格符合最小价格变动单位
                    limit_price = math.floor(limit_price / tick_size) * tick_size
                except Exception as e:
                    self.logger.error(f"获取价格精度失败: {e}, 使用默认值")
                    # 使用默认值
                    symbol_lower = symbol.upper()
                    if symbol_lower.startswith("BTC"):
                        price_precision = 1
                        tick_size = 0.1
                    elif symbol_lower.startswith("ETH"):
                        price_precision = 2
                        tick_size = 0.01
                    else:
                        price_precision = 2
                        tick_size = 0.01
                    
                    # 处理价格
                    limit_price = math.floor(limit_price / tick_size) * tick_size
                    
                # 四舍五入到指定精度
                limit_price = round(limit_price, price_precision)
                
                # self.logger.info(f"限价单价格: {limit_price} (精度: {price_precision}, 最小变动单位: {tick_size})")
                
                result = self.place_order(
                    symbol=symbol,
                    side=side,
                    order_type="LIMIT",
                    quantity=contract_amount,
                    price=limit_price
                )
            
            # 添加调整信息到结果
            if isinstance(result, dict) and 'error' not in result:
                result.update({
                    'current_position': current_position,
                    'current_leverage': current_leverage,
                    'target_position': target_position,
                    'target_leverage': leverage,
                    'position_diff': position_diff,
                    'adjusted_amount': contract_amount,
                    'target_margin': target_margin
                })
            
            # self.logger.info(f"下单结果: {result}")
            return result
        except Exception as e:
            error_msg = f"调整仓位失败: {str(e)}"
            self.logger.error(error_msg)
            return {'error': error_msg}
            
    def order_by_margin(self, symbol: str, margin: float, leverage: int, side: str, 
                        order_type: str = "MARKET") -> Dict:
        """
        根据保证金金额下单
        
        Args:
            symbol: 交易对，如 "BTCUSDT"
            margin: 保证金金额(USDT)，正数表示做多，负数表示做空
            leverage: 杠杆倍数，范围1-125，根据具体交易对不同而不同
            side: 方向，"BUY"或"SELL"
            order_type: 订单类型，"MARKET"或"LIMIT"
            
        Returns:
            Dict: 下单结果
        """
        try:
            # 获取交易对信息
            symbol_info = self.get_symbol_info(symbol)
            if not symbol_info:
                return {'error': f'获取{symbol}信息失败'}
            
            # 获取交易对价格
            price = self.get_ticker_price(symbol)
            if price <= 0:
                return {'error': f'获取{symbol}价格失败'}
            
            # self.logger.info(f"当前{symbol}价格: {price}")
            
            # 设置杠杆
            leverage_result = self.set_leverage(symbol, leverage)
            # self.logger.info(f"设置杠杆倍数结果: {leverage_result}")
            
            # 设置保证金类型为逐仓
            margin_result = self.set_margin_type(symbol, "ISOLATED")
            # self.logger.info(f"设置保证金类型结果: {margin_result}")
            
            # 计算合约数量
            # 合约数量 = 保证金金额 * 杠杆倍数 / 价格
            abs_margin = abs(margin)  # 取保证金绝对值
            contract_amount = (abs_margin * leverage) / price
            
            # 币安的最小名义价值要求通常是5-10 USDT
            min_notional = 5.0
            
            # 检查名义价值是否满足最小要求
            notional_value = contract_amount * price
            if notional_value < min_notional:
                self.logger.warning(f"计算的名义价值 {notional_value:.2f} USDT 小于最小要求 {min_notional} USDT")
                # 调整合约数量以满足最小名义价值要求
                contract_amount = min_notional / price
                notional_value = contract_amount * price
                # self.logger.info(f"调整后合约数量: {contract_amount}, 名义价值: {notional_value:.2f} USDT")
            
            # 获取数量精度和最小变动单位
            try:
                step_size, quantity_precision = self.get_lot_size_filter(symbol)
                # self.logger.info(f"获取到{symbol}数量精度: {quantity_precision}, 最小数量变动单位: {step_size}")
                
                # 确保数量符合最小变动单位
                contract_amount = math.floor(contract_amount / step_size) * step_size
            except Exception as e:
                self.logger.error(f"获取数量精度失败: {e}, 使用默认值")
                # 使用默认值
                symbol_lower = symbol.upper()
                if symbol_lower.startswith("BTC"):
                    quantity_precision = 3
                elif symbol_lower.startswith("ETH"):
                    quantity_precision = 3
                else:
                    quantity_precision = 1
            
            # 四舍五入到指定精度
            contract_amount = round(contract_amount, quantity_precision)
            
            trade_info = (
                f"下单信息:\n"
                f"交易对: {symbol}\n"
                f"方向: {side}\n"
                f"保证金: {abs_margin} USDT\n"
                f"杠杆: {leverage}倍\n"
                f"价格: {price}\n"
                f"合约数量: {contract_amount}\n"
                f"名义价值: {contract_amount * price:.2f} USDT"
            )
            # self.logger.info(trade_info)
            
            # 检查数量是否为0或负数
            if contract_amount <= 0:
                return {
                    'status': 'NO_ACTION',
                    'message': '计算的交易数量为0或负数，无需发送下单请求',
                    'symbol': symbol,
                    'margin': margin,
                    'leverage': leverage,
                    'side': side,
                    'price': price,
                    'calculated_amount': contract_amount
                }
            
            # 执行下单
            if order_type == "MARKET":
                result = self.place_order(
                    symbol=symbol,
                    side=side,
                    order_type="MARKET",
                    quantity=contract_amount
                )
            else:
                # 对于限价单，需要提供价格
                # 这里可以设置比当前价格略低/高的价格，视交易策略而定
                price_offset = 0.005  # 价格偏移0.5%
                limit_price = price * (1 - price_offset) if side == "BUY" else price * (1 + price_offset)
                
                # 获取价格精度和最小价格变动单位
                try:
                    tick_size, price_precision = self.get_price_filter(symbol)
                    # self.logger.info(f"获取到{symbol}价格精度: {price_precision}, 最小价格变动单位: {tick_size}")
                    
                    # 确保价格符合最小价格变动单位
                    limit_price = math.floor(limit_price / tick_size) * tick_size
                except Exception as e:
                    self.logger.error(f"获取价格精度失败: {e}, 使用默认值")
                    # 使用默认值
                    symbol_lower = symbol.upper()
                    if symbol_lower.startswith("BTC"):
                        price_precision = 1
                        tick_size = 0.1
                    elif symbol_lower.startswith("ETH"):
                        price_precision = 2
                        tick_size = 0.01
                    else:
                        price_precision = 2
                        tick_size = 0.01
                    
                    # 处理价格
                    limit_price = math.floor(limit_price / tick_size) * tick_size
                    
                # 四舍五入到指定精度
                limit_price = round(limit_price, price_precision)
                
                # self.logger.info(f"限价单价格: {limit_price} (精度: {price_precision}, 最小变动单位: {tick_size})")
                
                result = self.place_order(
                    symbol=symbol,
                    side=side,
                    order_type="LIMIT",
                    quantity=contract_amount,
                    price=limit_price
                )
            
            # self.logger.info(f"下单结果: {result}")
            return result
        except Exception as e:
            error_msg = f"下单失败: {str(e)}"
            self.logger.error(error_msg)
            return {'error': error_msg}
