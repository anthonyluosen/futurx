import os
import pandas as pd
import numpy as np
from datetime import datetime, time
import sys
# 导入OrderBookMMP类
from orderbookmmp import OrderBookMMP

base_path = "F:/workspace/data/TICK"
def clean_column_names(df):
    """清理列名，移除前缀"""
    # 清理列名，移除如"SSE.513200."这样的前缀
    cleaned_columns = {}
    for col in df.columns:
        if '.' in col:
            cleaned_name = col.split('.')[-1]
            cleaned_columns[col] = cleaned_name
    
    # 重命名列
    if cleaned_columns:
        df = df.rename(columns=cleaned_columns)
    
    return df

def process_single_day(csv_file, symbol, target_date=None):
    """
    处理CSV文件中的单日数据并保存到MMP格式
    
    Args:
        csv_file: CSV文件路径
        symbol: 股票代码
        target_date: 要处理的特定日期，如果为None则处理第一个日期
    """

    # 读取CSV文件
    df = pd.read_csv(csv_file)
    # 清理列名
    df = clean_column_names(df)
         # 定义字段映射关系
    field_mapping = {
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
    df.rename(columns=field_mapping,inplace=True)
    # 转换datetime列为日期和时间
    if 'datetime' in df.columns:
        # 确保datetime列被正确解析
        df['datetime'] = pd.to_datetime(df['datetime'])
        df['date'] = df['datetime'].dt.strftime('%Y-%m-%d')
        df['time'] = df['datetime'].dt.strftime('%H:%M:%S')
    
    # 检查必要字段
    required_fields = ['date', 'time']
    for field in required_fields:
        if field not in df.columns:
            print(f"错误: CSV文件缺少必要字段 '{field}'")
            return
    
    # 创建存储目录
    os.makedirs(base_path, exist_ok=True)
    
    # 创建单股票存储实例
    mmp_storage = OrderBookMMP(
        base_path=base_path,
        symbol=symbol
    )
    
    # 确定要处理的日期
    if target_date is None:
        # 如果没有指定日期，使用第一个日期
        target_date = df['date'].iloc[0]
    
    print(f"处理日期: {target_date}")
    
    # 过滤单日数据
    day_data = df[df['date'] == target_date].copy()
    
    if len(day_data) == 0:
        print(f"错误: 未找到日期 {target_date} 的数据")
        return
    
    # 添加symbol字段 (如果不存在)
    if 'symbol' not in day_data.columns:
        day_data['symbol'] = symbol
    # 统计要保存的记录数
    total_records = len(day_data)
    # 初始化进度计数器
    processed = 0
    
    # 保存每条记录
    for tick_idx, tick_row in day_data.iterrows():
        # 创建tick数据字典
        tick_data = tick_row.to_dict()
        # 处理nan值
        for k, v in tick_data.items():
            if pd.isna(v):
                if k in ['volume', 'amount', 'bid_volume1', 'ask_volume1'] or 'vol' in k:
                    tick_data[k] = 0
                else:
                    tick_data[k] = 0.0
        
        # 存储到MMP
        try:
            mmp_storage.save_tick_data(tick_data)
            processed += 1
            
            # 显示进度
            if processed % 100 == 0 or processed == total_records:
                progress = (processed / total_records) * 100
                print(f"进度: {processed}/{total_records} ({progress:.1f}%)")
                
        except Exception as e:
            print(f"错误: {e}")
    
    # 格式化日期字符串为YYYYMMDD格式 (用于读取)
    formatted_date = target_date.replace('-', '')
    
    print(f"\n数据处理完成!")
    print(f"存储路径: {os.path.join(mmp_storage.base_path, formatted_date)}")
    
    return mmp_storage, formatted_date

def process_all_days(csv_file, symbol):
    """
    处理CSV文件中的所有日期数据并保存到MMP格式
    
    Args:
        csv_file: CSV文件路径
        symbol: 股票代码
    """
    print(f"开始处理所有日期的数据，来源: {csv_file}")
    
    # 读取CSV文件
    df = pd.read_csv(csv_file)
    # 清理列名
    df = clean_column_names(df)
    # 定义字段映射关系
    field_mapping = {
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
    df.rename(columns=field_mapping, inplace=True)
    
    # 转换datetime列为日期和时间
    if 'datetime' in df.columns:
        # 确保datetime列被正确解析
        df['datetime'] = pd.to_datetime(df['datetime'])
        df['date'] = df['datetime'].dt.strftime('%Y-%m-%d')
        df['time'] = df['datetime'].dt.strftime('%H:%M:%S')
    
    # 检查必要字段
    required_fields = ['date', 'time']
    for field in required_fields:
        if field not in df.columns:
            print(f"错误: CSV文件缺少必要字段 '{field}'")
            return
    
    # 获取唯一的日期列表
    unique_dates = df['date'].unique()
    print(f"找到 {len(unique_dates)} 个交易日")
    
    # 创建存储目录
    os.makedirs(base_path, exist_ok=True)
    
    # 创建单股票存储实例
    mmp_storage = OrderBookMMP(
        base_path=base_path,
        symbol=symbol
    )
    
    processed_dates = []
    
    # 处理每个日期
    for date_idx, current_date in enumerate(unique_dates):
        print(f"\n处理日期 [{date_idx+1}/{len(unique_dates)}]: {current_date}")
        
        # 过滤单日数据
        day_data = df[df['date'] == current_date].copy()
        
        if len(day_data) == 0:
            print(f"错误: 未找到日期 {current_date} 的数据")
            continue
        
        # 添加symbol字段 (如果不存在)
        if 'symbol' not in day_data.columns:
            day_data['symbol'] = symbol
            
        # 统计要保存的记录数
        total_records = len(day_data)
        print(f"找到 {total_records} 条记录")
        
        # 初始化进度计数器
        processed = 0
        
        # 保存每条记录
        for tick_idx, tick_row in day_data.iterrows():
            # 创建tick数据字典
            tick_data = tick_row.to_dict()
            
            # 处理nan值
            for k, v in tick_data.items():
                if pd.isna(v):
                    if k in ['volume', 'amount'] or 'vol' in k:
                        tick_data[k] = 0
                    else:
                        tick_data[k] = 0.0
            
            # 存储到MMP
            try:
                mmp_storage.save_tick_data(tick_data)
                processed += 1
                
                # 显示进度
                if processed % 500 == 0 or processed == total_records:
                    progress = (processed / total_records) * 100
                    print(f"进度: {processed}/{total_records} ({progress:.1f}%)")
                    
            except Exception as e:
                print(f"错误: {e}")
        
        # 格式化日期字符串为YYYYMMDD格式 (用于读取)
        formatted_date = current_date.replace('-', '')
        processed_dates.append(formatted_date)
        
        print(f"完成日期 {current_date} 的处理")
        print(f"存储路径: {os.path.join(mmp_storage.base_path, formatted_date)}")
    
    print(f"\n已完成所有 {len(unique_dates)} 个日期的数据处理!")
    return mmp_storage, processed_dates

def validate_data(mmp_storage, date_str):
    """验证存储的数据"""
    print(f"\n验证日期 {date_str} 的数据...")
    
    # 读取存储的数据
    data = mmp_storage.read_day_data(
        date_str,
        fields=['price', 'volume']
    )
    
    if data and 'price' in data and len(data['price']) > 0:
        print(f"价格数据形状: {data['price'].shape}")
        if 'volume' in data:
            print(f"成交量数据形状: {data['volume'].shape}")
        
        # 显示一些数据点
        sample_size = min(5, len(data['price']))
        print("\n示例数据:")
        for i in range(sample_size):
            price_str = f"价格={data['price'][i]}"
            vol_str = f", 成交量={data['volume'][i]}" if 'volume' in data else ""
            print(f"Tick {i}: {price_str}{vol_str}")
            
        # 尝试获取不同时间区间的数据
        print("\n不同时间区间的数据:")
        time_ranges = [
            ('上午盘前', time(9, 15), time(9, 30)),
            ('上午交易', time(9, 30), time(11, 30)),
            ('下午交易', time(13, 0), time(15, 0))
        ]
        
        for name, start, end in time_ranges:
            try:
                start_idx = mmp_storage.time_to_index(start)
                end_idx = mmp_storage.time_to_index(end)
                count = end_idx - start_idx + 1
                print(f"{name}: 从索引 {start_idx} 到 {end_idx}, 共 {count} 个数据点")
            except Exception as e:
                print(f"计算 {name} 时间范围出错: {e}")
    else:
        print("无法读取数据或数据为空")

if __name__ == "__main__":
    # 文件路径和股票代码
    csv_file = r"F:\workspace\data\csv\TICK\513200_tick.csv"
    symbol = "513200"  # 从文件名提取股票代码
    
    # 处理所有日期数据
    mmp_storage, processed_dates = process_all_days(csv_file, symbol)
    
    # 如果有处理的日期，验证第一个日期的数据
    if processed_dates:
        validate_data(mmp_storage, processed_dates[0])
        print(f"\n已处理的所有日期: {processed_dates}")
    else:
        print("没有处理任何日期数据") 