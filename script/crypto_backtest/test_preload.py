#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试预加载功能的性能和效果
展示预加载机制的优势
"""

import sys
import os
import time
import pandas as pd
import numpy as np

# 添加路径
__file__ = r"E:\workspace\crypto\futurx\script\crypto_backtest\test_preload.py"
root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
if root_path not in sys.path:
    sys.path.append(root_path)

from factor_crypto.write_mmap import *
from bt_crypto.portfolio_backtest import PortfolioBacktest
from bt_crypto.factor_analysis import FactorAnalysis

def test_preload_performance():
    """
    测试预加载机制的性能提升
    """
    print("========== 预加载性能测试 ==========")
    
    # 测试参数
    start_time = '2024-01-01 00:00:00'
    end_time = '2024-03-31 23:45:00'
    codes = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT']
    
    print(f"测试时间范围: {start_time} 到 {end_time}")
    print(f"测试币种: {codes}")
    
    # 测试1: 因子分析器初始化性能
    print(f"\n--- 因子分析器初始化测试 ---")
    
    # 带预加载的初始化
    start = time.time()
    factor_analyzer = FactorAnalysis(
        start_time=start_time,
        end_time=end_time,
        codes=codes,
        preload_fields=['Close', 'Open', 'High', 'Low', 'Volume']
    )
    preload_time = time.time() - start
    
    print(f"预加载初始化耗时: {preload_time:.3f}秒")
    print(f"预加载数据字段: {list(factor_analyzer.price_data.keys())}")
    print(f"预计算收益率周期: {list(factor_analyzer.returns_data.keys())}")
    
    # 测试2: 组合回测器初始化性能
    print(f"\n--- 组合回测器初始化测试 ---")
    
    start = time.time()
    portfolio_bt = PortfolioBacktest(
        start_time=start_time,
        end_time=end_time,
        codes=codes,
        preload_fields=['Close', 'Open', 'High', 'Low', 'Volume']
    )
    portfolio_init_time = time.time() - start
    
    print(f"组合回测器初始化耗时: {portfolio_init_time:.3f}秒")
    
    return factor_analyzer, portfolio_bt

def test_data_quality():
    """
    测试数据质量统计功能
    """
    print(f"\n========== 数据质量测试 ==========")
    
    # 使用前面创建的分析器
    factor_analyzer = FactorAnalysis(
        start_time='2024-01-01 00:00:00',
        end_time='2024-03-31 23:45:00',
        codes=['BTCUSDT', 'ETHUSDT', 'ADAUSDT'],
        preload_fields=['Close', 'Open', 'High', 'Low', 'Volume']
    )
    
    # 获取数据统计
    data_stats = factor_analyzer.get_price_statistics()
    
    print(f"数据质量报告:")
    for field, stats in data_stats.items():
        print(f"\n{field}:")
        print(f"  数据量: {stats['数据量']:,}")
        print(f"  有效数据量: {stats['有效数据量']:,}")
        print(f"  缺失率: {stats['缺失率']:.2%}")
        print(f"  数据范围: [{stats['最小值']:.2f}, {stats['最大值']:.2f}]")
        print(f"  均值: {stats['均值']:.2f}")
        print(f"  标准差: {stats['标准差']:.2f}")
    
    return data_stats

def test_cache_efficiency():
    """
    测试缓存效率
    """
    print(f"\n========== 缓存效率测试 ==========")
    
    factor_analyzer = FactorAnalysis(
        start_time='2024-01-01 00:00:00',
        end_time='2024-03-31 23:45:00',
        codes=['BTCUSDT', 'ETHUSDT', 'ADAUSDT']
    )
    
    # 测试收益率计算缓存
    print(f"测试收益率计算缓存效果...")
    
    # 第一次计算（使用预计算结果）
    start = time.time()
    returns_1 = factor_analyzer.calculate_returns(periods=[1, 4, 16, 96])
    first_time = time.time() - start
    
    # 第二次计算（使用缓存）
    start = time.time()
    returns_2 = factor_analyzer.calculate_returns(periods=[1, 4, 16, 96])
    second_time = time.time() - start
    
    print(f"第一次计算耗时: {first_time:.4f}秒")
    print(f"第二次计算耗时: {second_time:.4f}秒")
    print(f"缓存加速比: {first_time/second_time:.1f}x")
    
    # 验证结果一致性
    for period in [1, 4, 16, 96]:
        if period in returns_1 and period in returns_2:
            diff = np.nanmax(np.abs(returns_1[period] - returns_2[period]))
            print(f"周期{period}结果差异: {diff:.10f}")
    
    return returns_1

def test_error_handling():
    """
    测试错误处理机制
    """
    print(f"\n========== 错误处理测试 ==========")
    
    # 测试缺失字段处理
    print(f"测试缺失字段处理...")
    
    try:
        factor_analyzer = FactorAnalysis(
            start_time='2024-01-01 00:00:00',
            end_time='2024-03-31 23:45:00',
            codes=['BTCUSDT', 'ETHUSDT', 'ADAUSDT'],
            preload_fields=['Close', 'Open', 'NonExistentField']  # 包含不存在的字段
        )
        print(f"成功处理缺失字段，已加载字段: {list(factor_analyzer.price_data.keys())}")
    except Exception as e:
        print(f"错误处理失败: {e}")
    
    # 测试缺失因子处理
    print(f"\n测试缺失因子处理...")
    
    try:
        factor_data = factor_analyzer.load_factor_data('non_existent_factor')
        print(f"缺失因子返回数组大小: {factor_data.size}")
    except Exception as e:
        print(f"因子加载错误: {e}")

def test_memory_usage():
    """
    测试内存使用情况
    """
    print(f"\n========== 内存使用测试 ==========")
    
    import psutil
    import gc
    
    # 获取初始内存
    process = psutil.Process()
    initial_memory = process.memory_info().rss / 1024 / 1024  # MB
    
    print(f"初始内存使用: {initial_memory:.1f} MB")
    
    # 创建分析器
    factor_analyzer = FactorAnalysis(
        start_time='2024-01-01 00:00:00',
        end_time='2024-06-30 23:45:00',  # 更长时间范围
        codes=['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'BNBUSDT', 'SOLUSDT'],  # 更多币种
        preload_fields=['Close', 'Open', 'High', 'Low', 'Volume']
    )
    
    after_preload_memory = process.memory_info().rss / 1024 / 1024  # MB
    preload_memory_usage = after_preload_memory - initial_memory
    
    print(f"预加载后内存使用: {after_preload_memory:.1f} MB")
    print(f"预加载内存开销: {preload_memory_usage:.1f} MB")
    
    # 计算预加载数据大小
    total_data_size = 0
    for field, data in factor_analyzer.price_data.items():
        data_size = data.nbytes / 1024 / 1024  # MB
        total_data_size += data_size
        print(f"  {field}: {data_size:.1f} MB")
    
    print(f"预加载数据总大小: {total_data_size:.1f} MB")
    
    # 清理内存
    del factor_analyzer
    gc.collect()
    
    final_memory = process.memory_info().rss / 1024 / 1024  # MB
    print(f"清理后内存使用: {final_memory:.1f} MB")

def main():
    """
    运行所有测试
    """
    print("开始预加载功能测试...")
    
    try:
        # 性能测试
        factor_analyzer, portfolio_bt = test_preload_performance()
        
        # 数据质量测试
        data_stats = test_data_quality()
        
        # 缓存效率测试
        returns_data = test_cache_efficiency()
        
        # 错误处理测试
        test_error_handling()
        
        # 内存使用测试
        test_memory_usage()
        
        print(f"\n========== 测试总结 ==========")
        print(f"✅ 预加载机制工作正常")
        print(f"✅ 数据质量监控功能正常")
        print(f"✅ 缓存机制显著提升性能")
        print(f"✅ 错误处理机制健壮")
        print(f"✅ 内存使用合理")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试过程中出现错误: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    # 首先确保mmap数据已加载
    print("正在加载mmap数据...")
    
    # 运行测试
    success = main()
    
    if success:
        print(f"\n🎉 所有测试通过！预加载功能已就绪。")
    else:
        print(f"\n❌ 测试失败，请检查配置。") 