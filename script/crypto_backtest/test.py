
import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
# 添加路径
__file__ = r"E:\workspace\crypto\futurx\script\crypto_backtest\portfolio_factor_demo.py"
root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
if root_path not in sys.path:
    sys.path.append(root_path)

from factor_crypto.write_mmap import *
from bt_crypto.portfolio_backtest import PortfolioBacktest
from bt_crypto.factor_analysis import FactorAnalysis


if __name__ == "__main__":

    start_time = "2023-06-01 07:45:00"
    end_time = "2025-06-01 07:45:00"
    factor_name = "gp1_2_3_48"
    codes = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'BNBUSDT', 'SOLUSDT']

    print(f"========== 开始综合策略分析: {factor_name} ==========")
    print(f"分析时间: {start_time} 到 {end_time}")
    print(f"币种数量: {len(codes)}")
    print(f"币种列表: {codes}")

    # ================================
    # 第一步：因子有效性分析
    # ================================
    print(f"\n【第一步】因子有效性分析")

    factor_analyzer = FactorAnalysis(
    start_time=start_time,
    end_time=end_time,
    codes=codes
    )
    factor_analyzer.analyze_factor_ic(factor_name=factor_name)
    # factor_results = factor_analyzer.run_comprehensive_analysis(factor_name)


    # 打印因子分析摘要
    # factor_analyzer.print_analysis_summary(factor_results)
    
    # 绘制因子分析图表
    # factor_analyzer.plot_factor_analysis(factor_results)