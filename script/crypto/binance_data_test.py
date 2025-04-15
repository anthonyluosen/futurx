#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Binance数据订阅测试脚本
简单演示如何订阅Binance交易所的行情数据并打印
"""

import time
import sys
import os
from datetime import datetime

# 添加项目根目录到系统路径
root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
if root_path not in sys.path:
    sys.path.append(root_path)

# 导入binance库
from binance.client import Client
from binance import ThreadedDepthCacheManager, ThreadedWebsocketManager

def main():
    """主函数"""
    print("开始测试Binance数据订阅...")
    
    # 初始化客户端 (使用空字符串表示不需要身份验证的公共API)
    client = Client("", "")
    print("Binance客户端初始化成功")
    
    # 要订阅的交易对
    symbol = 'btcusdt'  # 比特币/USDT，使用小写
    
    # 创建线程化websocket管理器
    twm = ThreadedWebsocketManager()
    # 启动线程化websocket管理器
    twm.start()
    print("线程化Websocket管理器已启动")
    
    def handle_socket_message(msg):
        """处理websocket消息的回调函数"""
        try:
            # 检查消息是否包含错误
            if 'error' in msg:
                print(f"接收到错误: {msg['error']}")
                return
                
            # 检查消息类型
            if 'e' in msg:
                print(f"消息类型: {msg['e']}")
                
                # 如果是K线数据
                if msg['e'] == 'kline':
                    kline = msg['k']
                    symbol = kline['s']
                    interval = kline['i']
                    is_closed = kline['x']  # 是否是已完成的K线
                    open_price = float(kline['o'])
                    high_price = float(kline['h'])
                    low_price = float(kline['l'])
                    close_price = float(kline['c'])
                    volume = float(kline['v'])
                    close_time = datetime.fromtimestamp(kline['T'] / 1000)
                    
                    print(f"收到 {symbol} {interval} K线数据:")
                    print(f"时间: {close_time}")
                    print(f"价格: 开={open_price}, 高={high_price}, 低={low_price}, 收={close_price}")
                    print(f"成交量: {volume}")
                    print(f"K线是否完成: {is_closed}")
                # 如果是行情深度数据
                elif msg['e'] == 'depthUpdate':
                    symbol = msg['s']
                    update_id = msg['u']
                    print(f"收到 {symbol} 深度数据更新 (ID: {update_id})")
                # 如果是逐笔交易数据
                elif msg['e'] == 'trade':
                    symbol = msg['s']
                    price = msg['p']
                    quantity = msg['q']
                    print(f"收到 {symbol} 交易: 价格={price}, 数量={quantity}")
                
            # 完整打印消息
            print(msg)
            print("-" * 50)
        except Exception as e:
            print(f"处理消息时发生错误: {e}")
    
    try:
        # 订阅逐笔交易数据 (这个通常比K线数据更轻量级，更容易获取)
        conn_key = twm.start_trade_socket(callback=handle_socket_message, symbol=symbol)
        print(f"成功订阅 {symbol.upper()} 的逐笔交易数据")
        
        # 等待数据接收
        print("正在接收数据，按Ctrl+C退出...")
        # 持续运行一段时间
        count = 0
        max_count = 30  # 最多运行30秒
        while count < max_count:
            time.sleep(1)
            count += 1
            
    except KeyboardInterrupt:
        print("\n用户中断，正在退出...")
    except Exception as e:
        print(f"运行过程中发生错误: {e}")
    finally:
        # 关闭连接并清理
        try:
            twm.stop()
            print("已停止websocket管理器")
        except Exception as e:
            print(f"关闭连接时发生错误: {e}")
        print("测试结束")

if __name__ == "__main__":
    main()
