#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
因子有效性分析模块
专注于组合层面的因子IC分析、稳定性评估和预测能力分析
"""

import os
# 设置环境变量以解决OpenMP重复初始化的错误
os.environ['KMP_DUPLICATE_LIB_OK'] = 'True'

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy import stats
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import warnings
import torch
warnings.filterwarnings('ignore')

import sys
import os
root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../'))
if root_path not in sys.path:
    sys.path.append(root_path)

from factor_crypto.write_mmap import *
from factor_crypto.calc_fac import *

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False

class FactorAnalysis:
    """
    因子有效性分析类
    专注于组合层面的因子分析
    """
    
    def __init__(self, start_time: str, end_time: str, codes: List[str], 
                 preload_fields: List[str] = ['Close', 'Open', 'High', 'Low', 'Volume']):
        """
        初始化因子分析器
        
        Args:
            start_time: 开始时间
            end_time: 结束时间
            codes: 币种代码列表
            preload_fields: 预加载的基础数据字段
        """
        self.start_time = start_time
        self.end_time = end_time
        self.codes = codes
        self.preload_fields = preload_fields
        
        # 获取时间和代码的位置索引
        self.start_loc = get_mmap_time_loc(start_time)
        self.end_loc = get_mmap_time_loc(end_time)
        self.code_locs = [get_mmap_code_loc(code) for code in codes]
        
        print(f"因子分析时间范围: {start_time} 到 {end_time}")
        print(f"时间位置: {self.start_loc} 到 {self.end_loc}, 共{self.end_loc - self.start_loc + 1}个15分钟")
        print(f"币种数量: {len(codes)}")
        
        # 预加载基础数据
        print(f"正在预加载基础数据: {preload_fields}")
        self.price_data = self._preload_price_data()
        print(f"基础数据加载完成，形状: {self.price_data['Close'].shape}")
        
        # 预计算常用收益率
        print(f"正在预计算收益率...")
        self.returns_data = self._precompute_returns()
        print(f"收益率计算完成，周期数: {len(self.returns_data)}")
        
    def _preload_price_data(self) -> Dict[str, np.ndarray]:
        """
        预加载基础价格数据
        """
        data = {}
        
        for field in self.preload_fields:
            try:
                # 直接从mmap切片获取数据，形状为 [time, code]
                field_data = mmap_dict[field][self.start_loc:self.end_loc+1, self.code_locs]
                data[field] = field_data.copy()
            except KeyError:
                print(f"警告: 字段 {field} 在mmap中不存在，跳过加载")
                continue
            except Exception as e:
                print(f"警告: 加载字段 {field} 时出错: {str(e)}")
                continue
                
        return data
    
    def _precompute_returns(self, periods: List[int] = [1, 4, 16, 96]) -> Dict[int, np.ndarray]:
        """
        预计算常用收益率
        
        Args:
            periods: 收益率周期列表 (15分钟为单位)
            
        Returns:
            各期收益率字典
        """
        if 'Close' not in self.price_data:
            raise("warn: no close data")
            return {}
            
        returns_dict = {}
        prices = self.price_data['Close']
        
        for period in periods:
            if period >= prices.shape[0]:
                continue

            # 计算period期后的收益率
            returns = np.full(prices.shape, np.nan)
            returns[:-period] = prices[period:] / prices[:-period] - 1
            returns_dict[period] = returns
            
        return returns_dict
        
    def load_price_data(self, field: str = 'Close') -> np.ndarray:
        """
        获取预加载的价格数据
        
        Args:
            field: 数据字段名
            
        Returns:
            价格数据数组
        """
        if field in self.price_data:
            return self.price_data[field]
        else:
            print(f"警告: 字段 {field} 未预加载，尝试实时加载...")
            try:
                field_data = mmap_dict[field][self.start_loc:self.end_loc+1, self.code_locs].copy()
                # 缓存到预加载数据中
                self.price_data[field] = field_data
                return field_data
            except Exception as e:
                print(f"错误: 无法加载字段 {field}: {str(e)}")
                return np.array([])
    
    def load_factor_data(self, factor_name: str) -> np.ndarray:
        """
        加载因子数据
        """
        try:
            factor_data = mmap_dict[factor_name][self.start_loc:self.end_loc+1, self.code_locs].copy()
            return factor_data
        except KeyError:
            print(f"错误: 因子 {factor_name} 在mmap中不存在")
            return np.array([])
        except Exception as e:
            print(f"错误: 加载因子 {factor_name} 时出错: {str(e)}")
            return np.array([])
    
    def calculate_returns(self, prices: np.ndarray = None, periods: List[int] = [1, 4, 16, 96]) -> Dict[int, np.ndarray]:
        """
        计算多期收益率（优先使用预计算的结果）
        
        Args:
            prices: 价格数组 [time, code]，如果为None则使用预加载的Close数据
            periods: 收益率周期列表 (15分钟为单位)
            
        Returns:
            各期收益率字典
        """
        # 如果没有提供价格数据且请求的是常用周期，直接返回预计算结果
        if prices is None and all(p in self.returns_data for p in periods):
            return {p: self.returns_data[p] for p in periods if p in self.returns_data}
        
        # 否则实时计算
        if prices is None:
            prices = self.load_price_data('Close')
            
        if prices.size == 0:
            return {}
            
        returns_dict = {}
        
        for period in periods:
            # 优先使用预计算结果
            if period in self.returns_data:
                returns_dict[period] = self.returns_data[period]
                continue
                
            # 实时计算
            if period >= prices.shape[0]:
                continue
                
            returns = np.full(prices.shape, np.nan)
            returns[:-period] = prices[period:] / prices[:-period] - 1
            
            returns_dict[period] = returns
            # 缓存结果
            self.returns_data[period] = returns
            
        return returns_dict
    
    def get_price_statistics(self) -> Dict[str, Dict]:
        """
        获取预加载价格数据的统计信息
        """
        stats_info = {}
        
        for field, data in self.price_data.items():
            valid_data = data[~np.isnan(data)]
            if len(valid_data) > 0:
                stats_info[field] = {
                    '数据量': data.size,
                    '有效数据量': len(valid_data),
                    '缺失率': (data.size - len(valid_data)) / data.size,
                    '最小值': valid_data.min(),
                    '最大值': valid_data.max(),
                    '均值': valid_data.mean(),
                    '标准差': valid_data.std()
                }
            else:
                stats_info[field] = {'数据量': data.size, '有效数据量': 0, '缺失率': 1.0}
                
        return stats_info
    
    def calculate_portfolio_weighted_ic(self, factor_values: np.ndarray, 
                                       returns: np.ndarray
                                       ) -> Tuple[float, float]:
        """
        计算组合加权IC (时序IC)
        
        Args:
            factor_values: 因子值数组 [time, code]
            returns: 收益率数组 [time, code]
            
        Returns:
            (IC均值, IC标准差)
        """
        print(f"因子数据形状: {factor_values.shape}, 收益率数据形状: {returns.shape}")
        
        n_time, n_code = factor_values.shape
        ic_list = []  # 存储每个币种的IC值
        
        # 对每个币种计算时序IC
        for code_idx in range(n_code):
            factor_series = factor_values[:, code_idx]
            return_series = returns[:, code_idx]
            
            # 找到有效数据点
            valid_mask = ~(np.isnan(factor_series) | np.isnan(return_series))
            
            if valid_mask.sum() >= 10:  # 至少需要10个有效样本
                factor_valid = factor_series[valid_mask]
                return_valid = return_series[valid_mask]
                
                # 计算该币种的时序IC (使用Spearman相关系数)
                if len(factor_valid) > 1:
                    ic, _ = stats.spearmanr(factor_valid, return_valid)
                    if not np.isnan(ic):
                        ic_list.append(ic)
        
        if len(ic_list) == 0:
            return 0.0, 0.0
            
        # 计算所有币种IC的均值和标准差
        ic_array = np.array(ic_list)
        ic_mean = round(float(ic_array.mean()), 4)  # 转换为Python float并保留4位小数
        ic_std = round(float(ic_array.std()), 4)    # 转换为Python float并保留4位小数
        
        print(f"有效币种数: {len(ic_list)}, IC均值: {ic_mean}, IC标准差: {ic_std}")
        
        return ic_mean, ic_std, ic_array
    
    def analyze_factor_ic(self, factor_name: str, 
                         return_periods: List[int] = [1, 4, 16, 96]) -> Dict:
        """
        分析因子IC
        
        Args:
            factor_name: 因子名称
            return_periods: 收益率周期列表
            
        Returns:
            IC分析结果
        """
        print(f"开始分析因子IC: {factor_name}")
        factor_data = self.load_factor_data(factor_name)
        # 计算各期IC
        ic_results = {}
        
        for period in return_periods:
            if period not in self.returns_data:
                continue
                
            returns = self.returns_data[period]
            
            # 计算组合加权IC
            ic_mean, ic_std, ic_array = self.calculate_portfolio_weighted_ic(factor_data, returns)
            
            period_name = self.get_period_name(period)
            
            ic_results[period_name] = {
                'IC均值': ic_mean,
                'IC标准差': ic_std,
                'IC_IR': round(ic_mean / ic_std, 4) if ic_std > 0 else 0,
                'IC绝对值均值': round(float(np.abs(ic_mean)), 4),  # 转换为Python float并保留4位小数
                # '有效币种数': len([ic for ic in ic_list if not np.isnan(ic)]) if 'ic_list' in locals() else 0
            }
        
        return ic_results
    
    def calculate_ic_time_series(self, factor_values: np.ndarray, returns: np.ndarray) -> List[float]:
        """
        计算IC时间序列
        """
        n_time = factor_values.shape[0]
        ic_series = []
        
        for t in range(n_time):
            factor_t = factor_values[t, :]
            return_t = returns[t, :]
            
            # 找到有效数据
            valid_mask = ~(np.isnan(factor_t) | np.isnan(return_t))
            
            if valid_mask.sum() >= 3:
                factor_valid = factor_t[valid_mask]
                return_valid = return_t[valid_mask]
                
                if len(factor_valid) > 1:
                    ic, _ = stats.spearmanr(factor_valid, return_valid)
                    if not np.isnan(ic):
                        ic_series.append(ic)
        
        return ic_series
    
    def analyze_factor_stability(self, factor_name: str, 
                                window_size: int = 96*30,  # 30天窗口
                                step_size: int = 96*7) -> Dict:    # 7天步长
        """
        分析因子稳定性
        
        Args:
            factor_name: 因子名称
            window_size: 滚动窗口大小
            step_size: 步长
            
        Returns:
            稳定性分析结果
        """
        print(f"开始分析因子稳定性: {factor_name}")
        
        # 加载因子数据
        factor_data = self.load_factor_data(factor_name)
        if factor_data.size == 0:
            return {}
        
        # 获取1期收益率（使用预计算结果）
        if 1 not in self.returns_data:
            print("错误: 缺少1期收益率数据")
            return {}
        
        returns_1 = self.returns_data[1]
        
        # 滚动窗口分析
        n_time = factor_data.shape[0]
        stability_results = []
        
        for start_idx in range(0, n_time - window_size, step_size):
            end_idx = start_idx + window_size
            
            # 提取窗口数据
            factor_window = factor_data[start_idx:end_idx]
            returns_window = returns_1[start_idx:end_idx]
            
            # 计算窗口IC
            ic_mean, ic_std = self.calculate_portfolio_weighted_ic(factor_window, returns_window)
            
            stability_results.append({
                '窗口开始': start_idx,
                '窗口结束': end_idx,
                'IC均值': ic_mean,
                'IC标准差': ic_std,
                'IC_IR': round(ic_mean / ic_std, 4) if ic_std > 0 else 0
            })
        
        # 计算稳定性指标
        if len(stability_results) > 0:
            ic_means = [r['IC均值'] for r in stability_results]
            ic_stds = [r['IC标准差'] for r in stability_results]
            ic_irs = [r['IC_IR'] for r in stability_results]
            
            stability_metrics = {
                'IC均值稳定性': round(np.std(ic_means), 4),
                'IC标准差稳定性': round(np.std(ic_stds), 4),
                'IC_IR稳定性': round(np.std(ic_irs), 4),
                'IC均值趋势': round(self.calculate_trend(ic_means), 4),
                'IC_IR趋势': round(self.calculate_trend(ic_irs), 4),
                '窗口数量': len(stability_results),
                '详细结果': stability_results
            }
        else:
            stability_metrics = {}
        
        return stability_metrics
    
    def analyze_factor_decay(self, factor_name: str, 
                            max_lag: int = 96) -> Dict:  # 最大滞后1天
        """
        分析因子衰减
        
        Args:
            factor_name: 因子名称
            max_lag: 最大滞后期数
            
        Returns:
            衰减分析结果
        """
        print(f"开始分析因子衰减: {factor_name}")
        
        # 加载因子数据
        factor_data = self.load_factor_data(factor_name)
        if factor_data.size == 0:
            return {}
        
        # 获取价格数据
        prices = self.load_price_data('Close')
        if prices.size == 0:
            return {}
        
        # 计算不同滞后期的IC
        decay_results = []
        
        for lag in range(1, min(max_lag + 1, prices.shape[0])):
            # 优先使用预计算的收益率
            if lag in self.returns_data:
                returns_lag = self.returns_data[lag]
            else:
                # 计算lag期收益率
                returns_lag = np.full(prices.shape, np.nan)
                returns_lag[:-lag] = prices[lag:] / prices[:-lag] - 1
                # 缓存结果
                self.returns_data[lag] = returns_lag
            
            # 计算IC
            ic_mean, ic_std = self.calculate_portfolio_weighted_ic(factor_data, returns_lag)
            
            period_name = self.get_period_name(lag)
            
            decay_results.append({
                '滞后期': lag,
                '周期名称': period_name,
                'IC均值': ic_mean,
                'IC标准差': ic_std,
                'IC_IR': round(ic_mean / ic_std, 4) if ic_std > 0 else 0,
                'IC绝对值': round(float(abs(ic_mean)), 4)  # 转换为Python float并保留4位小数
            })
        
        # 计算衰减系数
        if len(decay_results) >= 2:
            ic_abs_values = [r['IC绝对值'] for r in decay_results]
            lags = list(range(1, len(ic_abs_values) + 1))
            
            # 拟合指数衰减
            decay_coef = round(self.fit_decay_curve(lags, ic_abs_values), 4)
        else:
            decay_coef = 0
        
        return {
            '衰减系数': decay_coef,
            '详细结果': decay_results
        }
    
    def calculate_trend(self, values: List[float]) -> float:
        """
        计算趋势系数（线性回归斜率）
        """
        if len(values) < 2:
            return 0
        
        x = np.arange(len(values))
        y = np.array(values)
        
        # 去除nan值
        valid_mask = ~np.isnan(y)
        if valid_mask.sum() < 2:
            return 0
        
        x_valid = x[valid_mask]
        y_valid = y[valid_mask]
        
        slope, _, _, _, _ = stats.linregress(x_valid, y_valid)
        return slope
    
    def fit_decay_curve(self, lags: List[int], ic_values: List[float]) -> float:
        """
        拟合衰减曲线
        """
        if len(lags) < 2:
            return 0
        
        # 简单的线性衰减系数
        x = np.array(lags)
        y = np.array(ic_values)
        
        # 去除nan和零值
        valid_mask = ~(np.isnan(y) | (y == 0))
        if valid_mask.sum() < 2:
            return 0
        
        x_valid = x[valid_mask]
        y_valid = y[valid_mask]
        
        # 拟合 y = a * exp(-b * x)，取对数后线性拟合
        try:
            log_y = np.log(y_valid)
            slope, _, _, _, _ = stats.linregress(x_valid, log_y)
            return -slope  # 衰减系数为正数
        except:
            return 0
    
    def get_period_name(self, period: int) -> str:
        """
        获取周期名称
        """
        if period == 1:
            return '15分钟'
        elif period == 4:
            return '1小时'
        elif period == 16:
            return '4小时'
        elif period == 96:
            return '1天'
        elif period == 96 * 7:
            return '1周'
        elif period == 96 * 30:
            return '1月'
        else:
            return f'{period}期'
    
    def run_comprehensive_analysis(self, factor_name: str) -> Dict:
        """
        运行综合因子分析
        
        Args:
            factor_name: 因子名称
            
        Returns:
            综合分析结果
        """
        print(f"开始综合因子分析: {factor_name}")
        
        # IC分析
        ic_results = self.analyze_factor_ic(factor_name)
        
        # 稳定性分析
        stability_results = self.analyze_factor_stability(factor_name)
        
        # 衰减分析
        decay_results = self.analyze_factor_decay(factor_name)
        
        # 综合评分
        overall_score = self.calculate_overall_score(ic_results, stability_results, decay_results)
        
        return {
            'IC分析': ic_results,
            '稳定性分析': stability_results,
            '衰减分析': decay_results,
            '综合评分': overall_score,
            '因子名称': factor_name,
            '数据统计': self.get_price_statistics()
        }
    
    def calculate_overall_score(self, ic_results: Dict, 
                               stability_results: Dict, 
                               decay_results: Dict) -> Dict:
        """
        计算综合评分
        """
        scores = {}
        
        # IC得分 (基于1天期IC)
        if '1天' in ic_results:
            ic_1d = ic_results['1天']
            ic_score = min(abs(ic_1d['IC均值']) * 100, 10)  # 最高10分
            ir_score = min(abs(ic_1d['IC_IR']) * 2, 10)     # 最高10分
            
            scores['IC得分'] = ic_score
            scores['IR得分'] = ir_score
        
        # 稳定性得分
        if stability_results:
            stability_score = max(0, 10 - stability_results.get('IC均值稳定性', 1) * 50)
            scores['稳定性得分'] = stability_score
        
        # 衰减得分
        if decay_results and decay_results['衰减系数'] > 0:
            decay_score = min(decay_results['衰减系数'] * 20, 10)
            scores['衰减得分'] = decay_score
        
        # 总得分
        total_score = sum(scores.values())
        scores['总得分'] = total_score
        
        return scores
    
    def plot_factor_analysis(self, analysis_results: Dict, save_path: str = None):
        """
        绘制因子分析图表
        """
        factor_name = analysis_results['因子名称']
        ic_results = analysis_results['IC分析']
        stability_results = analysis_results['稳定性分析']
        decay_results = analysis_results['衰减分析']
        
        fig, axes = plt.subplots(2, 3, figsize=(18, 12))
        fig.suptitle(f'因子分析报告: {factor_name}', fontsize=16)
        
        # IC分析图
        ax1 = axes[0, 0]
        periods = list(ic_results.keys())
        ic_means = [ic_results[p]['IC均值'] for p in periods]
        ic_stds = [ic_results[p]['IC标准差'] for p in periods]
        
        x_pos = range(len(periods))
        ax1.bar(x_pos, ic_means, yerr=ic_stds, capsize=5, alpha=0.7)
        ax1.set_xticks(x_pos)
        ax1.set_xticklabels(periods, rotation=45)
        ax1.set_title('各期IC均值')
        ax1.set_ylabel('IC')
        ax1.grid(True)
        ax1.axhline(y=0, color='red', linestyle='--', alpha=0.5)
        
        # IC_IR分析图
        ax2 = axes[0, 1]
        ic_irs = [ic_results[p]['IC_IR'] for p in periods]
        ax2.bar(x_pos, ic_irs, alpha=0.7, color='green')
        ax2.set_xticks(x_pos)
        ax2.set_xticklabels(periods, rotation=45)
        ax2.set_title('各期IC_IR')
        ax2.set_ylabel('IC_IR')
        ax2.grid(True)
        
        # IC绝对值图
        ax3 = axes[0, 2]
        ic_abs_values = [ic_results[p]['IC绝对值均值'] for p in periods]
        ax3.bar(x_pos, ic_abs_values, alpha=0.7, color='orange')
        ax3.set_xticks(x_pos)
        ax3.set_xticklabels(periods, rotation=45)
        ax3.set_title('IC绝对值均值')
        ax3.set_ylabel('IC绝对值')
        ax3.grid(True)
        
        # 稳定性分析图
        ax4 = axes[1, 0]
        if stability_results and '详细结果' in stability_results:
            stability_data = stability_results['详细结果']
            windows = [r['窗口开始'] for r in stability_data]
            ic_means_stability = [r['IC均值'] for r in stability_data]
            
            ax4.plot(windows, ic_means_stability, 'b-', marker='o', markersize=4)
            ax4.set_title('IC稳定性(滚动窗口)')
            ax4.set_xlabel('时间窗口')
            ax4.set_ylabel('IC均值')
            ax4.grid(True)
            ax4.axhline(y=0, color='red', linestyle='--', alpha=0.5)
        
        # 衰减分析图
        ax5 = axes[1, 1]
        if decay_results and '详细结果' in decay_results:
            decay_data = decay_results['详细结果']
            lags = [r['滞后期'] for r in decay_data]
            ic_abs_values = [r['IC绝对值'] for r in decay_data]
            
            ax5.plot(lags, ic_abs_values, 'r-', marker='s', markersize=4)
            ax5.set_title('因子衰减曲线')
            ax5.set_xlabel('滞后期')
            ax5.set_ylabel('IC绝对值')
            ax5.grid(True)
        
        # 综合评分图
        ax6 = axes[1, 2]
        scores = analysis_results['综合评分']
        score_names = [k for k in scores.keys() if k != '总得分']
        score_values = [scores[k] for k in score_names]
        
        colors = plt.cm.Set3(np.linspace(0, 1, len(score_names)))
        ax6.pie(score_values, labels=score_names, colors=colors, autopct='%1.1f%%')
        ax6.set_title(f'综合评分: {scores.get("总得分", 0):.1f}分')
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.show()
    
    def print_analysis_summary(self, analysis_results: Dict):
        """
        打印分析摘要
        """
        factor_name = analysis_results['因子名称']
        ic_results = analysis_results['IC分析']
        stability_results = analysis_results['稳定性分析']
        decay_results = analysis_results['衰减分析']
        scores = analysis_results['综合评分']
        data_stats = analysis_results.get('数据统计', {})
        
        print(f"\n========== 因子分析摘要: {factor_name} ==========")
        
        # 数据统计摘要
        if data_stats:
            print(f"\n--- 数据统计 ---")
            for field, stats in data_stats.items():
                print(f"{field}: 有效率={1-stats['缺失率']:.2%}, 数据量={stats['有效数据量']}")
        
        # IC分析摘要
        print(f"\n--- IC分析结果 ---")
        for period, result in ic_results.items():
            print(f"{period}: IC={result['IC均值']:.4f}, IC_IR={result['IC_IR']:.4f}, IC标准差={result['IC标准差']:.4f}")
        
        # 稳定性分析摘要
        if stability_results:
            print(f"\n--- 稳定性分析结果 ---")
            print(f"IC均值稳定性: {stability_results.get('IC均值稳定性', 0):.4f}")
            print(f"IC_IR稳定性: {stability_results.get('IC_IR稳定性', 0):.4f}")
            print(f"IC均值趋势: {stability_results.get('IC均值趋势', 0):.4f}")
            print(f"IC_IR趋势: {stability_results.get('IC_IR趋势', 0):.4f}")
        
        # 衰减分析摘要
        if decay_results:
            print(f"\n--- 衰减分析结果 ---")
            print(f"衰减系数: {decay_results.get('衰减系数', 0):.4f}")
        
        # 综合评分
        print(f"\n--- 综合评分 ---")
        for score_name, score_value in scores.items():
            print(f"{score_name}: {score_value:.2f}")


