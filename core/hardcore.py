import os
import numpy as np
from datetime import datetime, time, date
from typing import Dict, List, Union, Optional, Tuple, Any

class OrderBookMMP:
    def __init__(self, 
                 base_path: str,
                 symbol: str,
                 levels: int = 5):
        """
        初始化订单簿MMP存储
        
        Args:
            base_path: 基础存储路径
            symbol: 股票代码
            levels: 订单簿深度
        """
        self.base_path = base_path
        self.symbol = symbol
        self.levels = levels
        
        # 定义基础字段
        self.fields = [
            # 基础行情字段
            'price', 'volume', 'amount', 'open', 'high', 'low', 
            
            # 买卖档位
            'bid1', 'bidvol1', 'ask1', 'askvol1',
            'bid2', 'bidvol2', 'ask2', 'askvol2',
            'bid3', 'bidvol3', 'ask3', 'askvol3',
            'bid4', 'bidvol4', 'ask4', 'askvol4',
            'bid5', 'bidvol5', 'ask5', 'askvol5'
        ]
        
        # 定义交易时间
        self.trading_start = time(9, 30)
        self.trading_end = time(15, 0)
        self.ticks_per_day = 4801  # 固定tick数量
        
    def time_to_index(self, time_point: time) -> int:
        """
        将时间转换为索引位置
        
        Args:
            time_point: 时间点
            
        Returns:
            对应的索引位置
        """
        if time_point < self.trading_start:
            return 0
        if time_point > self.trading_end:
            return self.ticks_per_day - 1
            
        # 计算从开始时间到当前时间的秒数
        total_seconds = (time_point.hour - self.trading_start.hour) * 3600 + \
                       (time_point.minute - self.trading_start.minute) * 60 + \
                       (time_point.second - self.trading_start.second)
        
        # 转换为3秒间隔的索引
        index = total_seconds // 3
        return min(index, self.ticks_per_day - 1)
    
    def index_to_time(self, index: int) -> time:
        """
        将索引位置转换为时间
        
        Args:
            index: 索引位置
            
        Returns:
            对应的时间点
        """
        if index < 0:
            return self.trading_start
        if index >= self.ticks_per_day:
            return self.trading_end
            
        total_seconds = index * 3
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        
        return time(
            self.trading_start.hour + hours,
            self.trading_start.minute + minutes,
            self.trading_start.second + seconds
        )
    
    def save_tick_data(self, tick_data: Dict[str, Any]) -> None:
        """
        保存单个tick数据，基于字典格式的tick数据
        
        Args:
            tick_data: 包含tick数据的字典，需要包含date和time字段
        """
        # 解析日期和时间
        if isinstance(tick_data['date'], str):
            tick_date = datetime.strptime(tick_data['date'], '%Y-%m-%d').date()
        elif isinstance(tick_data['date'], date):
            tick_date = tick_data['date']
        else:
            raise ValueError("date格式不正确")
            
        if isinstance(tick_data['time'], str):
            tick_time = datetime.strptime(tick_data['time'], '%H:%M:%S').time()
        elif isinstance(tick_data['time'], time):
            tick_time = tick_data['time']
        else:
            raise ValueError("time格式不正确")
        
        # 创建日期文件夹
        day_str = tick_date.strftime('%Y%m%d')
        day_path = os.path.join(self.base_path, day_str)
        os.makedirs(day_path, exist_ok=True)
        
        # 计算tick的索引位置
        tick_index = self.time_to_index(tick_time)
        
        # 内存映射字段字典 - 提高性能，避免重复打开关闭文件
        memmaps = {}
        
        # 为每个字段单独存储
        for field in self.fields:
            if field not in tick_data:
                continue
                
            # 确定数据类型
            if field in ['volume', 'amount'] or 'vol' in field:
                dtype = np.int64
                value = int(tick_data[field])
            else:
                dtype = np.float64
                value = float(tick_data[field])
            
            # 创建或打开存储文件
            field_path = os.path.join(day_path, f"{self.symbol}_{field}.npy")
            
            # 使用内存映射方式读取或创建
            if field_path not in memmaps:
                if os.path.exists(field_path):
                    try:
                        # 尝试直接使用memmap打开文件
                        memmaps[field_path] = np.memmap(
                            field_path, 
                            dtype=dtype, 
                            mode='r+', 
                            shape=(self.ticks_per_day,)
                        )
                    except Exception:
                        # 如果打开失败，创建新文件
                        memmaps[field_path] = np.memmap(
                            field_path,
                            dtype=dtype,
                            mode='w+',
                            shape=(self.ticks_per_day,)
                        )
                else:
                    # 文件不存在，创建新文件
                    memmaps[field_path] = np.memmap(
                        field_path,
                        dtype=dtype,
                        mode='w+',
                        shape=(self.ticks_per_day,)
                    )
            
            # 更新数据
            memmaps[field_path][tick_index] = value
        
        # # 确保所有memmap都刷新到磁盘
        # for memmap in memmaps.values():
        #     memmap.flush()
    
    def read_day_data(self, 
                     date_str: str,
                     fields: Optional[List[str]] = None,
                     start_time: Optional[time] = None,
                     end_time: Optional[time] = None) -> Dict[str, np.ndarray]:
        """
        读取单日数据
        
        Args:
            date_str: 日期字符串，格式为'YYYYMMDD'
            fields: 需要读取的字段列表，如果为None则读取所有字段
            start_time: 开始时间
            end_time: 结束时间
            
        Returns:
            字段名到numpy数组的字典，形状为(bars,)
        """
        day_path = os.path.join(self.base_path, date_str)
        
        if not os.path.exists(day_path):
            return {}
        
        # 如果没有指定字段，使用所有字段
        fields_to_read = fields if fields is not None else self.fields
        
        # 计算索引范围
        start_idx = 0 if start_time is None else self.time_to_index(start_time)
        end_idx = self.ticks_per_day - 1 if end_time is None else self.time_to_index(end_time)
        
        # 读取数据
        result = {}
        for field in fields_to_read:
            field_path = os.path.join(day_path, f"{self.symbol}_{field}.npy")
            if not os.path.exists(field_path):
                continue
                
            try:
                # 使用memmap直接读取数据
                if field in ['volume', 'amount'] or 'vol' in field:
                    dtype = np.int64
                else:
                    dtype = np.float64
                    
                # 使用内存映射打开文件
                mmap_data = np.memmap(
                    field_path, 
                    dtype=dtype, 
                    mode='r', 
                    shape=(self.ticks_per_day,)
                )
                
                # 截取指定时间范围，并复制到新数组返回
                # 复制是必要的，因为我们需要返回一个独立的数组，而不是memmap的引用
                result[field] = np.array(mmap_data[start_idx:end_idx+1])
            except Exception as e:
                print(f"读取字段 {field} 出错: {e}")
        
        return result


class MultiSymbolMMP:
    def __init__(self, 
                 base_path: str,
                 symbols: List[str]):
        """
        初始化多股票数据存储
        
        Args:
            base_path: 基础存储路径
            symbols: 股票代码列表
        """
        self.base_path = base_path
        self.symbols = symbols
        
        # 定义基础字段
        self.fields = [
            # 基础行情字段
            'price', 'volume', 'amount', 'open', 'high', 'low', 
            
            # 买卖档位
            'bid1', 'bidvol1', 'ask1', 'askvol1',
            'bid2', 'bidvol2', 'ask2', 'askvol2',
            'bid3', 'bidvol3', 'ask3', 'askvol3',
            'bid4', 'bidvol4', 'ask4', 'askvol4',
            'bid5', 'bidvol5', 'ask5', 'askvol5'
        ]
        
        # 定义字段映射关系
        self.field_mapping = {
            # 基础行情字段映射
            'last_price': 'price',
            'lastPrice': 'price',
            'last': 'price',
            'closePrice': 'price',
            'highest': 'high',
            'lowest': 'low',
            'open_interest': 'open_interest',
            
            # 买卖档位映射
            'bid_price1': 'bid1',
            'bid_volume1': 'bidvol1',
            'ask_price1': 'ask1',
            'ask_volume1': 'askvol1',
            
            'bid_price2': 'bid2',
            'bid_volume2': 'bidvol2',
            'ask_price2': 'ask2',
            'ask_volume2': 'askvol2',
            
            'bid_price3': 'bid3',
            'bid_volume3': 'bidvol3',
            'ask_price3': 'ask3',
            'ask_volume3': 'askvol3',
            
            'bid_price4': 'bid4',
            'bid_volume4': 'bidvol4',
            'ask_price4': 'ask4',
            'ask_volume4': 'askvol4',
            
            'bid_price5': 'bid5',
            'bid_volume5': 'bidvol5',
            'ask_price5': 'ask5',
            'ask_volume5': 'askvol5',
        }
        
        # 定义交易时间
        self.trading_start = time(9, 15)
        self.trading_end = time(15, 0)
        self.ticks_per_day = 4801  # 固定tick数量
    
    def time_to_index(self, time_point: time) -> int:
        """
        将时间转换为索引位置
        
        Args:
            time_point: 时间点
            
        Returns:
            对应的索引位置
        """
        if time_point < self.trading_start:
            return 0
        if time_point > self.trading_end:
            return self.ticks_per_day - 1
            
        # 计算从开始时间到当前时间的秒数
        total_seconds = (time_point.hour - self.trading_start.hour) * 3600 + \
                       (time_point.minute - self.trading_start.minute) * 60 + \
                       (time_point.second - self.trading_start.second)
        
        # 转换为3秒间隔的索引
        index = total_seconds // 3
        return min(index, self.ticks_per_day - 1)
    
    def save_tick_data(self, tick_data: Dict[str, Any]) -> None:
        """
        保存单个tick数据
        
        Args:
            tick_data: 包含tick数据的字典，需要包含symbol, date和time字段
        """
        # 检查股票是否在列表中
        symbol = tick_data['symbol']
        if symbol not in self.symbols:
            raise ValueError(f"股票 {symbol} 不在初始化的股票列表中")
        
        # 解析日期和时间
        if isinstance(tick_data['date'], str):
            tick_date = datetime.strptime(tick_data['date'], '%Y-%m-%d').date()
        elif isinstance(tick_data['date'], date):
            tick_date = tick_data['date']
        else:
            raise ValueError("date格式不正确")
            
        if isinstance(tick_data['time'], str):
            tick_time = datetime.strptime(tick_data['time'], '%H:%M:%S').time()
        elif isinstance(tick_data['time'], time):
            tick_time = tick_data['time']
        else:
            raise ValueError("time格式不正确")
        
        # 创建日期文件夹
        day_str = tick_date.strftime('%Y%m%d')
        day_path = os.path.join(self.base_path, day_str)
        os.makedirs(day_path, exist_ok=True)
        
        # 计算tick索引
        tick_idx = self.time_to_index(tick_time)
        
        # 获取symbol的索引
        symbol_idx = self.symbols.index(symbol)
        
        # 内存映射字段字典 - 提高性能，避免重复打开关闭文件
        memmaps = {}
        
        # 准备处理的字段和值
        processed_data = {}
        
        # 应用字段映射
        for src_field, value in tick_data.items():
            if src_field in self.field_mapping:
                dest_field = self.field_mapping[src_field]
                processed_data[dest_field] = value
            else:
                # 保留原始字段
                processed_data[src_field] = value
        
        # 为每个字段单独存储
        for field in self.fields:
            # 检查是否有该字段的数据
            if field not in processed_data:
                continue
                
            # 确定数据类型
            if field in ['volume', 'amount'] or 'vol' in field:
                dtype = np.int64
                # 确保是整数
                value = int(float(processed_data[field])) if processed_data[field] is not None else 0
            else:
                dtype = np.float64
                # 确保是浮点数
                value = float(processed_data[field]) if processed_data[field] is not None else 0.0
            
            # 创建或打开存储文件 (每个字段一个npy文件)
            field_path = os.path.join(day_path, f"{field}.npy")
            
            # 使用内存映射方式读取或创建
            if field_path not in memmaps:
                if os.path.exists(field_path):
                    try:
                        # 尝试直接使用memmap打开文件
                        data = np.memmap(
                            field_path, 
                            dtype=dtype, 
                            mode='r+', 
                            shape=(self.ticks_per_day, len(self.symbols))
                        )
                        memmaps[field_path] = data
                    except Exception:
                        # 如果打开失败，创建新文件
                        data = np.memmap(
                            field_path,
                            dtype=dtype,
                            mode='w+',
                            shape=(self.ticks_per_day, len(self.symbols))
                        )
                        # 初始化为0
                        data[:] = 0
                        memmaps[field_path] = data
                else:
                    # 文件不存在，创建新文件
                    data = np.memmap(
                        field_path,
                        dtype=dtype,
                        mode='w+',
                        shape=(self.ticks_per_day, len(self.symbols))
                    )
                    # 初始化为0
                    data[:] = 0
                    memmaps[field_path] = data
            
            # 更新数据
            memmaps[field_path][tick_idx, symbol_idx] = value
        
        # 确保所有memmap都刷新到磁盘
        for memmap in memmaps.values():
            memmap.flush()
    
    def read_day_data(self, 
                     date_str: str,
                     fields: Optional[List[str]] = None,
                     symbols: Optional[List[str]] = None,
                     start_time: Optional[time] = None,
                     end_time: Optional[time] = None) -> Dict[str, np.ndarray]:
        """
        读取单日数据
        
        Args:
            date_str: 日期字符串，格式为'YYYYMMDD'
            fields: 需要读取的字段列表，如果为None则读取所有字段
            symbols: 需要读取的股票列表，如果为None则读取所有股票
            start_time: 开始时间
            end_time: 结束时间
            
        Returns:
            字段名到numpy数组的字典，每个数组形状为(bars, symbols)
        """
        day_path = os.path.join(self.base_path, date_str)
        
        if not os.path.exists(day_path):
            return {}
        
        # 如果没有指定字段，使用所有字段
        fields_to_read = fields if fields is not None else self.fields
        
        # 计算索引范围
        start_idx = 0 if start_time is None else self.time_to_index(start_time)
        end_idx = self.ticks_per_day - 1 if end_time is None else self.time_to_index(end_time)
        
        # 如果指定了股票，获取股票索引
        symbol_indices = None
        if symbols is not None:
            symbol_indices = [self.symbols.index(s) for s in symbols if s in self.symbols]
        
        # 读取数据
        result = {}
        for field in fields_to_read:
            field_path = os.path.join(day_path, f"{field}.npy")
            if not os.path.exists(field_path):
                continue
                
            try:
                field_data = np.load(field_path)
                
                # 截取时间范围
                field_data = field_data[start_idx:end_idx+1]
                
                # 如果指定了股票，截取股票
                if symbol_indices is not None:
                    field_data = field_data[:, symbol_indices]
                
                result[field] = field_data
            except Exception as e:
                print(f"读取字段 {field} 出错: {e}")
        
        return result
    
    def get_available_fields(self, date_str: str) -> List[str]:
        """获取指定日期的所有可用特征"""
        day_path = os.path.join(self.base_path, date_str)
        
        if not os.path.exists(day_path):
            return []
        
        fields = []
        for file in os.listdir(day_path):
            if file.endswith('.npy'):
                fields.append(file[:-4])  # 移除.npy后缀
        
        return fields


# 使用示例
if __name__ == "__main__":
    # 单股票存储，每个特征单独保存
    mmp_storage = OrderBookMMP(
        base_path="F:/workspace/data/mmp",
        symbol="518880"
    )
    
    # 多股票存储，每个特征单独保存
    multi_storage = MultiSymbolMMP(
        base_path="F:/workspace/data/multi_mmp",
        symbols=["518880", "510300", "510500", "510050"]
    )
    
    # 示例数据
    sample_tick = {
        'symbol': '518880',
        'name': '黄金ETF',
        'price': 7.273,
        'preclose': 7.164,
        'open': 7.34,
        'high': 7.34,
        'low': 7.225,
        'volume': 969046516,
        'amount': 7073077660,
        'date': '2025-04-11',
        'time': '15:00:01',
        'bid1': 7.272,
        'bid2': 7.271,
        'bid3': 7.27,
        'bid4': 7.269,
        'bid5': 7.268,
        'bidvol1': 9600,
        'bidvol2': 91000,
        'bidvol3': 378200,
        'bidvol4': 105400,
        'bidvol5': 61900,
        'ask1': 7.273,
        'ask2': 7.274,
        'ask3': 7.275,
        'ask4': 7.276,
        'ask5': 7.277,
        'askvol1': 113900,
        'askvol2': 111100,
        'askvol3': 134700,
        'askvol4': 63600,
        'askvol5': 12500
    }
    
    # 保存单个tick数据
    # mmp_storage.save_tick_data(sample_tick)
    
    # 保存到多股票存储
    # multi_storage.save_tick_data(sample_tick)
    
    # 读取单股票特定字段数据
    # price_data = mmp_storage.read_day_data(
    #     '20250411',
    #     fields=['price', 'volume', 'bid1', 'ask1'],
    #     start_time=time(9, 30),
    #     end_time=time(11, 30)
    # )
    # if price_data:
    #     print(f"Price data shape: {price_data['price'].shape}")  # (bars,)
    
    # 读取多股票特定字段数据
    # multi_data = multi_storage.read_day_data(
    #     '20250411',
    #     fields=['price'],
    #     symbols=['518880', '510300'],
    #     start_time=time(9, 30),
    #     end_time=time(11, 30)
    # )
    # if multi_data:
    #     print(f"Multi-stock price data shape: {multi_data['price'].shape}")  # (bars, 2)