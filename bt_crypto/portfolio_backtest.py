#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
多币种组合策略回测框架
专注于整体组合的PnL曲线、夏普比率、回撤分析
以及每个币种对整体的仓位和PnL贡献分析
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import warnings
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

class PortfolioBacktest:
    """
    多币种组合策略回测类
    专注于整体组合效果和币种贡献分析
    """
    
    def __init__(self, start_time: str, end_time: str, codes: List[str], 
                 initial_capital: float = 1000000.0, commission_rate: float = 0.0005,
                 preload_fields: List[str] = ['Close', 'Open', 'High', 'Low', 'Volume']):
        """
        初始化组合回测器
        
        Args:
            start_time: 开始时间
            end_time: 结束时间
            codes: 币种代码列表
            initial_capital: 初始资金
            commission_rate: 手续费率
            preload_fields: 预加载的基础数据字段
        """
        self.start_time = start_time
        self.end_time = end_time
        self.codes = codes
        self.initial_capital = initial_capital
        self.commission_rate = commission_rate
        self.preload_fields = preload_fields
        
        # 获取时间和代码的位置索引
        self.start_loc = get_mmap_time_loc(start_time)
        self.end_loc = get_mmap_time_loc(end_time)
        self.code_locs = [get_mmap_code_loc(code) for code in codes]
        
        print(f"组合回测时间范围: {start_time} 到 {end_time}")
        print(f"时间位置: {self.start_loc} 到 {self.end_loc}, 共{self.end_loc - self.start_loc + 1}个15分钟")
        print(f"币种数量: {len(codes)}")
        print(f"初始资金: {initial_capital:,.0f}")
        
        # 预加载基础数据
        print(f"正在预加载基础数据: {preload_fields}")
        self.price_data = self._preload_price_data()
        if 'Close' in self.price_data:
            print(f"基础数据加载完成，形状: {self.price_data['Close'].shape}")
        else:
            print("警告: 未成功加载Close价格数据")
        
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
                print(f"  {field}: 加载完成")
            except KeyError:
                print(f"  警告: 字段 {field} 在mmap中不存在，跳过加载")
                continue
            except Exception as e:
                print(f"  警告: 加载字段 {field} 时出错: {str(e)}")
                continue
                
        return data
        
    def load_data(self, fields: List[str] = None) -> Dict[str, np.ndarray]:
        """
        获取预加载的数据或加载新数据
        
        Args:
            fields: 需要的字段列表，如果为None则返回所有预加载的数据
            
        Returns:
            数据字典
        """
        if fields is None:
            return self.price_data.copy()
        
        data = {}
        
        for field in fields:
            if field in self.price_data:
                data[field] = self.price_data[field]
            else:
                print(f"警告: 字段 {field} 未预加载，尝试实时加载...")
                try:
                    field_data = mmap_dict[field][self.start_loc:self.end_loc+1, self.code_locs]
                    data[field] = field_data.copy()
                    # 缓存到预加载数据中
                    self.price_data[field] = data[field]
                except Exception as e:
                    print(f"错误: 无法加载字段 {field}: {str(e)}")
                    continue
        
        return data
    
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
    
    def calculate_positions(self, factor_values: np.ndarray, 
                           position_method: str = 'rank_weight',
                           max_position: float = 0.1,
                           min_position: float = -0.1) -> np.ndarray:
        """
        根据因子值计算仓位
        
        Args:
            factor_values: 因子值数组 [time, code]
            position_method: 仓位计算方法 'rank_weight'/'equal_weight'/'factor_weight'
            max_position: 最大仓位
            min_position: 最小仓位
            
        Returns:
            仓位数组 [time, code]，每行和为0（多空平衡）
        """
        n_time, n_code = factor_values.shape
        positions = np.full((n_time, n_code), np.nan)
        
        for t in range(n_time):
            factor_t = factor_values[t, :]
            valid_mask = ~np.isnan(factor_t)
            
            if valid_mask.sum() >= 2:  # 至少需要2个有效币种
                factor_valid = factor_t[valid_mask]
                
                if position_method == 'rank_weight':
                    # 基于排名的权重分配
                    ranks = pd.Series(factor_valid).rank(pct=True) - 0.5  # 转换为[-0.5, 0.5]
                    weights = ranks * 2  # 转换为[-1, 1]
                    
                elif position_method == 'equal_weight':
                    # 等权重多空
                    n_long = len(factor_valid) // 2
                    sorted_idx = np.argsort(factor_valid)
                    weights = np.zeros_like(factor_valid)
                    weights[sorted_idx[-n_long:]] = 1.0 / n_long  # 做多前50%
                    weights[sorted_idx[:n_long]] = -1.0 / n_long  # 做空后50%
                    
                elif position_method == 'factor_weight':
                    # 基于因子值的权重
                    factor_std = factor_valid / np.std(factor_valid)
                    weights = np.tanh(factor_std)  # 使用tanh函数限制权重范围
                    
                else:
                    weights = np.zeros_like(factor_valid)
                
                # 确保权重和为0（多空平衡）
                weights = weights - weights.mean()
                
                # 限制仓位范围
                weights = np.clip(weights, min_position, max_position)
                
                # 重新平衡使和为0
                weights = weights - weights.mean()
                
                positions[t, valid_mask] = weights
        
        return positions
    
    def simulate_portfolio(self, positions: np.ndarray, prices: np.ndarray,
                          rebalance_freq: int = 1) -> Dict:
        """
        模拟组合交易
        
        Args:
            positions: 仓位数组 [time, code]
            prices: 价格数组 [time, code]
            rebalance_freq: 调仓频率（每几个时间点调仓一次）
            
        Returns:
            回测结果字典
        """
        n_time, n_code = positions.shape
        
        # 初始化结果数组
        portfolio_value = np.full(n_time, np.nan)
        portfolio_weights = np.full((n_time, n_code), np.nan)
        portfolio_pnl = np.full(n_time, np.nan)
        coin_pnl = np.full((n_time, n_code), np.nan)
        coin_contributions = np.full((n_time, n_code), np.nan)
        transaction_costs = np.full(n_time, 0.0)
        
        # 初始化
        portfolio_value[0] = self.initial_capital
        current_weights = np.zeros(n_code)
        
        for t in range(1, n_time):
            # 计算价格变化
            price_change = prices[t] / prices[t-1] - 1
            price_change = np.nan_to_num(price_change, 0)
            
            # 计算当期收益
            period_return = np.sum(current_weights * price_change)
            portfolio_value[t] = portfolio_value[t-1] * (1 + period_return)
            
            # 计算每个币种的PnL贡献
            coin_pnl[t] = current_weights * price_change * portfolio_value[t-1]
            coin_contributions[t] = coin_pnl[t] / portfolio_value[t-1] if portfolio_value[t-1] > 0 else 0
            
            # 检查是否需要调仓
            if t % rebalance_freq == 0:
                target_weights = positions[t]
                target_weights = np.nan_to_num(target_weights, 0)
                
                # 计算权重变化和交易成本
                weight_change = np.abs(target_weights - current_weights)
                transaction_costs[t] = np.sum(weight_change) * self.commission_rate * portfolio_value[t]
                
                # 更新权重
                current_weights = target_weights.copy()
                
                # 扣除交易成本
                portfolio_value[t] -= transaction_costs[t]
            
            # 记录当前权重
            portfolio_weights[t] = current_weights.copy()
            
            # 计算当期PnL
            portfolio_pnl[t] = portfolio_value[t] - portfolio_value[t-1] if t > 0 else 0
        
        # 计算收益率
        portfolio_returns = np.diff(portfolio_value) / portfolio_value[:-1]
        portfolio_returns = np.concatenate([[0], portfolio_returns])
        
        return {
            'portfolio_value': portfolio_value,
            'portfolio_returns': portfolio_returns,
            'portfolio_weights': portfolio_weights,
            'portfolio_pnl': portfolio_pnl,
            'coin_pnl': coin_pnl,
            'coin_contributions': coin_contributions,
            'transaction_costs': transaction_costs,
            'prices': prices
        }
    
    def calculate_portfolio_metrics(self, results: Dict) -> Dict:
        """
        计算组合绩效指标
        """
        portfolio_returns = results['portfolio_returns']
        portfolio_value = results['portfolio_value']
        
        # 去除nan值
        valid_mask = ~np.isnan(portfolio_returns)
        returns_clean = portfolio_returns[valid_mask]
        
        if len(returns_clean) == 0:
            return {}
        
        # 累计收益
        cum_returns = portfolio_value / portfolio_value[0] - 1
        
        # 年化收益率 (15分钟数据，一年约35040个15分钟)
        periods_per_year = 35040
        total_days = len(returns_clean) / 96  # 转换为天数
        annual_return = (portfolio_value[-1] / portfolio_value[0]) ** (365.25 / total_days) - 1
        
        # 年化波动率
        annual_vol = returns_clean.std() * np.sqrt(periods_per_year)
        
        # 夏普比率
        sharpe_ratio = annual_return / annual_vol if annual_vol > 0 else 0
        
        # 最大回撤
        rolling_max = np.maximum.accumulate(portfolio_value)
        drawdown = (portfolio_value - rolling_max) / rolling_max
        max_drawdown = drawdown.min()
        
        # 胜率
        win_rate = (returns_clean > 0).mean()
        
        # 卡尔玛比率
        calmar_ratio = annual_return / abs(max_drawdown) if max_drawdown != 0 else 0
        
        # 总交易成本
        total_transaction_costs = np.sum(results['transaction_costs'])
        
        # 收益分布
        returns_skew = pd.Series(returns_clean).skew()
        returns_kurt = pd.Series(returns_clean).kurtosis()
        
        return {
            '总收益率': cum_returns[-1],
            '年化收益率': annual_return,
            '年化波动率': annual_vol,
            '夏普比率': sharpe_ratio,
            '最大回撤': max_drawdown,
            '胜率': win_rate,
            '卡尔玛比率': calmar_ratio,
            '总交易成本': total_transaction_costs,
            '交易成本占比': total_transaction_costs / portfolio_value[0],
            '收益率偏度': returns_skew,
            '收益率峰度': returns_kurt,
            '样本数': len(returns_clean),
            '交易天数': total_days,
        }
    
    def analyze_coin_contributions(self, results: Dict) -> pd.DataFrame:
        """
        分析每个币种的贡献
        """
        coin_contributions = results['coin_contributions']
        coin_pnl = results['coin_pnl']
        portfolio_weights = results['portfolio_weights']
        
        contribution_stats = []
        
        for i, code in enumerate(self.codes):
            coin_contrib = coin_contributions[:, i]
            coin_pnl_series = coin_pnl[:, i]
            coin_weights = portfolio_weights[:, i]
            
            # 去除nan值
            valid_mask = ~np.isnan(coin_contrib)
            if valid_mask.sum() == 0:
                continue
                
            contrib_clean = coin_contrib[valid_mask]
            pnl_clean = coin_pnl_series[valid_mask]
            weights_clean = coin_weights[valid_mask]
            
            stats = {
                '币种': code,
                '总PnL贡献': np.sum(pnl_clean),
                '平均PnL贡献': np.mean(pnl_clean),
                'PnL贡献标准差': np.std(pnl_clean),
                '平均权重': np.mean(np.abs(weights_clean)),
                '最大权重': np.max(np.abs(weights_clean)),
                '权重标准差': np.std(weights_clean),
                '贡献夏普比率': np.mean(contrib_clean) / np.std(contrib_clean) if np.std(contrib_clean) > 0 else 0,
                '正贡献比例': (contrib_clean > 0).mean(),
                '有效交易次数': valid_mask.sum(),
            }
            
            contribution_stats.append(stats)
        
        return pd.DataFrame(contribution_stats).set_index('币种')
    
    def run_portfolio_backtest(self, factor_name: str,
                              position_method: str = 'rank_weight',
                              max_position: float = 0.1,
                              rebalance_freq: int = 4) -> Dict:
        """
        运行完整的组合回测
        
        Args:
            factor_name: 因子名称
            position_method: 仓位计算方法
            max_position: 最大仓位
            rebalance_freq: 调仓频率（每几个15分钟调仓一次）
            
        Returns:
            完整回测结果
        """
        print(f"开始组合回测: {factor_name}")
        
        # 获取价格数据（使用预加载数据）
        if 'Close' not in self.price_data:
            print("错误: 缺少Close价格数据")
            return {}
        
        close_prices = self.price_data['Close']
        
        # 加载因子数据
        factor_data = self.load_factor_data(factor_name)
        if factor_data.size == 0:
            print(f"错误: 无法加载因子数据 {factor_name}")
            return {}
        
        print(f"计算仓位...")
        # 计算仓位
        positions = self.calculate_positions(
            factor_data, 
            position_method=position_method,
            max_position=max_position,
            min_position=-max_position
        )
        
        print(f"模拟交易...")
        # 模拟交易
        simulation_results = self.simulate_portfolio(
            positions, 
            close_prices,
            rebalance_freq=rebalance_freq
        )
        
        print(f"计算绩效指标...")
        # 计算绩效指标
        portfolio_metrics = self.calculate_portfolio_metrics(simulation_results)
        
        print(f"分析币种贡献...")
        # 分析币种贡献
        coin_analysis = self.analyze_coin_contributions(simulation_results)
        
        print(f"组合回测完成")
        
        return {
            'simulation_results': simulation_results,
            'portfolio_metrics': portfolio_metrics,
            'coin_analysis': coin_analysis,
            'positions': positions,
            'factor_data': factor_data,
            'price_data': close_prices,
            '数据统计': self.get_price_statistics()
        }
    
    def plot_portfolio_analysis(self, backtest_results: Dict, save_path: str = None):
        """
        绘制组合分析图表
        """
        simulation_results = backtest_results['simulation_results']
        coin_analysis = backtest_results['coin_analysis']
        
        fig, axes = plt.subplots(2, 3, figsize=(18, 12))
        fig.suptitle('组合策略回测分析', fontsize=16)
        
        # 组合净值曲线
        ax1 = axes[0, 0]
        portfolio_value = simulation_results['portfolio_value']
        time_index = range(len(portfolio_value))
        ax1.plot(time_index, portfolio_value, 'b-', linewidth=2)
        ax1.set_title('组合净值曲线')
        ax1.set_ylabel('组合价值')
        ax1.grid(True)
        
        # 累计收益率
        ax2 = axes[0, 1]
        cum_returns = portfolio_value / portfolio_value[0] - 1
        ax2.plot(time_index, cum_returns * 100, 'g-', linewidth=2)
        ax2.set_title('累计收益率')
        ax2.set_ylabel('收益率 (%)')
        ax2.grid(True)
        
        # 回撤曲线
        ax3 = axes[0, 2]
        rolling_max = np.maximum.accumulate(portfolio_value)
        drawdown = (portfolio_value - rolling_max) / rolling_max * 100
        ax3.fill_between(time_index, drawdown, 0, alpha=0.3, color='red')
        ax3.plot(time_index, drawdown, 'r-', linewidth=1)
        ax3.set_title('回撤曲线')
        ax3.set_ylabel('回撤 (%)')
        ax3.grid(True)
        
        # 每日PnL分布
        ax4 = axes[1, 0]
        portfolio_pnl = simulation_results['portfolio_pnl']
        pnl_clean = portfolio_pnl[~np.isnan(portfolio_pnl)]
        ax4.hist(pnl_clean, bins=50, alpha=0.7, edgecolor='black')
        ax4.axvline(x=0, color='red', linestyle='--', alpha=0.7)
        ax4.set_title('每期PnL分布')
        ax4.set_xlabel('PnL')
        ax4.set_ylabel('频数')
        ax4.grid(True)
        
        # 币种PnL贡献
        ax5 = axes[1, 1]
        pnl_contrib = coin_analysis['总PnL贡献'].sort_values(ascending=True)
        colors = ['red' if x < 0 else 'green' for x in pnl_contrib.values]
        ax5.barh(range(len(pnl_contrib)), pnl_contrib.values, color=colors, alpha=0.7)
        ax5.set_yticks(range(len(pnl_contrib)))
        ax5.set_yticklabels(pnl_contrib.index, fontsize=8)
        ax5.set_title('币种PnL贡献')
        ax5.set_xlabel('总PnL贡献')
        ax5.grid(True)
        
        # 币种平均权重
        ax6 = axes[1, 2]
        avg_weights = coin_analysis['平均权重'].sort_values(ascending=False)
        ax6.bar(range(len(avg_weights)), avg_weights.values, alpha=0.7)
        ax6.set_xticks(range(len(avg_weights)))
        ax6.set_xticklabels(avg_weights.index, rotation=45, fontsize=8)
        ax6.set_title('币种平均权重')
        ax6.set_ylabel('平均权重')
        ax6.grid(True)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.show()
    
    def print_portfolio_summary(self, backtest_results: Dict, factor_name: str):
        """
        打印组合回测摘要
        """
        portfolio_metrics = backtest_results['portfolio_metrics']
        coin_analysis = backtest_results['coin_analysis']
        data_stats = backtest_results.get('数据统计', {})
        
        print(f"\n========== 组合策略回测摘要: {factor_name} ==========")
        
        # 数据统计摘要
        if data_stats:
            print(f"\n--- 数据统计 ---")
            for field, stats in data_stats.items():
                print(f"{field}: 有效率={1-stats['缺失率']:.2%}, 数据量={stats['有效数据量']}")
        
        # 整体绩效
        print(f"\n--- 整体绩效指标 ---")
        print(f"总收益率: {portfolio_metrics['总收益率']:.4f} ({portfolio_metrics['总收益率']*100:.2f}%)")
        print(f"年化收益率: {portfolio_metrics['年化收益率']:.4f} ({portfolio_metrics['年化收益率']*100:.2f}%)")
        print(f"年化波动率: {portfolio_metrics['年化波动率']:.4f} ({portfolio_metrics['年化波动率']*100:.2f}%)")
        print(f"夏普比率: {portfolio_metrics['夏普比率']:.4f}")
        print(f"最大回撤: {portfolio_metrics['最大回撤']:.4f} ({portfolio_metrics['最大回撤']*100:.2f}%)")
        print(f"卡尔玛比率: {portfolio_metrics['卡尔玛比率']:.4f}")
        print(f"胜率: {portfolio_metrics['胜率']:.4f} ({portfolio_metrics['胜率']*100:.2f}%)")
        print(f"交易成本占比: {portfolio_metrics['交易成本占比']:.4f} ({portfolio_metrics['交易成本占比']*100:.2f}%)")
        
        # 币种贡献分析
        print(f"\n--- 币种贡献分析 (Top 5) ---")
        print("PnL贡献最大的币种:")
        top_contributors = coin_analysis.nlargest(5, '总PnL贡献')
        for idx, row in top_contributors.iterrows():
            print(f"  {idx}: PnL贡献={row['总PnL贡献']:.2f}, 平均权重={row['平均权重']:.4f}")
        
        print("\nPnL贡献最小的币种:")
        bottom_contributors = coin_analysis.nsmallest(5, '总PnL贡献')
        for idx, row in bottom_contributors.iterrows():
            print(f"  {idx}: PnL贡献={row['总PnL贡献']:.2f}, 平均权重={row['平均权重']:.4f}")
        
        # 权重分析
        print(f"\n--- 权重分析 ---")
        print(f"平均权重最大的币种: {coin_analysis['平均权重'].idxmax()} ({coin_analysis['平均权重'].max():.4f})")
        print(f"权重波动最大的币种: {coin_analysis['权重标准差'].idxmax()} ({coin_analysis['权重标准差'].max():.4f})")
        print(f"贡献夏普比率最高: {coin_analysis['贡献夏普比率'].idxmax()} ({coin_analysis['贡献夏普比率'].max():.4f})")

