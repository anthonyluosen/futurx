# 多币种组合策略回测框架

## 概述

本框架专为多币种加密货币策略设计，重点关注：
- **整体组合PnL曲线**和绩效指标
- **每个币种对组合的贡献**分析
- **因子有效性**的组合层面评估
- **风险控制**和回撤管理

## 🚀 核心优化特性

### 预加载数据机制
- **初始化预加载**：在创建分析器时自动加载OHLCV等基础数据
- **智能缓存**：预计算常用收益率，避免重复计算
- **错误处理**：优雅处理缺失数据，提供详细统计信息
- **内存优化**：高效的向量化操作，基于mmap架构

### 数据统计功能
- **实时监控**：自动统计数据完整性和质量
- **缺失率分析**：识别数据缺失模式
- **基础统计**：提供最值、均值、标准差等统计信息

## 核心模块

### 1. 组合回测模块 (`portfolio_backtest.py`)
- 多币种组合策略回测
- 整体PnL曲线计算
- 币种贡献分析
- 多种仓位管理方法
- **预加载OHLCV数据**

### 2. 因子分析模块 (`factor_analysis.py`)
- 组合层面因子IC分析
- 因子稳定性评估
- 因子衰减分析
- 综合评分系统
- **预计算收益率数据**

### 3. 完整演示脚本 (`portfolio_factor_demo.py`)
- 因子分析 + 组合回测完整流程
- 策略对比分析
- 风险深度分析

## 快速开始

### 基础使用（预加载优化版）

```python
from bt_crypto.portfolio_backtest import PortfolioBacktest

# 初始化组合回测器（自动预加载基础数据）
portfolio_bt = PortfolioBacktest(
    start_time='2024-01-01 00:00:00',
    end_time='2024-06-30 23:45:00',
    codes=['BTCUSDT', 'ETHUSDT', 'ADAUSDT'],
    initial_capital=1000000.0,
    commission_rate=0.0005,
    preload_fields=['Close', 'Open', 'High', 'Low', 'Volume']  # 预加载字段
)

# 运行回测（使用预加载数据，速度更快）
results = portfolio_bt.run_portfolio_backtest(
    factor_name='your_factor_name',
    position_method='rank_weight',
    max_position=0.1,
    rebalance_freq=4
)

# 查看结果（包含数据统计信息）
portfolio_bt.print_portfolio_summary(results, 'your_factor_name')
portfolio_bt.plot_portfolio_analysis(results)
```

### 因子分析（预加载优化版）

```python
from bt_crypto.factor_analysis import FactorAnalysis

# 初始化因子分析器（自动预加载并预计算）
factor_analyzer = FactorAnalysis(
    start_time='2024-01-01 00:00:00',
    end_time='2024-06-30 23:45:00',
    codes=['BTCUSDT', 'ETHUSDT', 'ADAUSDT'],
    preload_fields=['Close', 'Open', 'High', 'Low', 'Volume']  # 可自定义预加载字段
)

# 运行因子分析（使用预计算收益率）
results = factor_analyzer.run_comprehensive_analysis('your_factor_name')

# 查看结果（包含数据质量统计）
factor_analyzer.print_analysis_summary(results)
factor_analyzer.plot_factor_analysis(results)
```

### 完整分析流程

```python
from script.crypto_backtest.portfolio_factor_demo import comprehensive_strategy_analysis

# 运行完整分析（自动优化数据加载）
results = comprehensive_strategy_analysis(
    factor_name='your_factor_name',
    start_time='2024-01-01 00:00:00',
    end_time='2024-06-30 23:45:00',
    codes=['BTCUSDT', 'ETHUSDT', 'ADAUSDT']
)
```

## 关键特性

### 组合层面分析
- **整体PnL**：关注组合整体表现，而非单币种
- **加权IC**：基于全币种的因子有效性评估
- **组合夏普比率**：整体风险调整收益
- **组合最大回撤**：整体风险控制

### 币种贡献分析
- **PnL贡献**：每个币种对总PnL的贡献
- **权重分布**：各币种在组合中的权重变化
- **贡献稳定性**：币种贡献的时间稳定性
- **风险贡献**：各币种对组合风险的贡献

### 仓位管理方法
- **rank_weight**：基于因子排名的权重分配
- **equal_weight**：等权重多空策略
- **factor_weight**：基于因子值的权重分配

### 时间周期定义
- 1期 = 15分钟
- 4期 = 1小时
- 16期 = 4小时
- 96期 = 1天
- 672期 = 1周

## 性能优化

### 预加载机制
```python
# 自定义预加载字段
portfolio_bt = PortfolioBacktest(
    # ... 其他参数
    preload_fields=['Close', 'Open', 'High', 'Low', 'Volume', 'Amount']  # 可扩展
)

# 查看数据统计
data_stats = portfolio_bt.get_price_statistics()
print(data_stats)
```

### 智能缓存
```python
# 因子分析器自动预计算常用收益率
factor_analyzer = FactorAnalysis(
    # ... 参数
)
# 1, 4, 16, 96期收益率已预计算完成

# 访问预计算结果
returns_1h = factor_analyzer.returns_data[4]  # 1小时收益率
returns_1d = factor_analyzer.returns_data[96] # 1天收益率
```

### 错误处理
```python
# 框架自动处理缺失数据
try:
    results = factor_analyzer.run_comprehensive_analysis('non_existent_factor')
except Exception as e:
    print(f"分析失败: {e}")
    
# 查看数据质量报告
if 'Close' in factor_analyzer.price_data:
    print("Close数据加载成功")
else:
    print("Close数据加载失败")
```

## 输出指标

### 组合绩效指标
- 总收益率、年化收益率
- 夏普比率、卡尔玛比率
- 最大回撤、平均回撤
- 胜率、波动率
- 交易成本分析

### 因子分析指标
- IC均值、IC_IR、IC胜率
- 因子稳定性、衰减系数
- 多期IC分析
- 综合评分

### 风险分析指标
- VaR、下行波动率
- 索提诺比率
- 回撤持续期
- 收益率分布特征

### 数据质量指标
- **数据完整性**：各字段的缺失率统计
- **数据范围**：最值、均值、标准差
- **有效样本**：实际参与计算的数据量

## 注意事项

1. **数据要求**：确保mmap中有所需的因子数据和价格数据
2. **预加载字段**：可根据需要自定义预加载字段列表
3. **内存管理**：预加载会占用一定内存，但显著提升计算速度
4. **错误处理**：框架会自动处理缺失字段，但建议检查数据质量
5. **缓存机制**：计算结果会自动缓存，重复调用速度更快

## 扩展功能

### 自定义预加载字段
```python
# 根据策略需要定制预加载字段
custom_fields = ['Close', 'Volume', 'Amount', 'custom_indicator']
analyzer = FactorAnalysis(
    # ... 其他参数
    preload_fields=custom_fields
)
```

### 数据质量监控
```python
# 获取详细的数据统计信息
stats = portfolio_bt.get_price_statistics()
for field, stat in stats.items():
    if stat['缺失率'] > 0.1:  # 缺失率超过10%
        print(f"警告: {field} 数据缺失率较高: {stat['缺失率']:.2%}")
```

### 性能监控
```python
import time

start_time = time.time()
results = factor_analyzer.run_comprehensive_analysis('factor_name')
end_time = time.time()

print(f"分析耗时: {end_time - start_time:.2f}秒")
print(f"预加载收益率数量: {len(factor_analyzer.returns_data)}")
```

这个优化后的框架在保持功能完整性的同时，显著提升了性能和用户体验。预加载机制和智能缓存让重复分析变得更加高效，而完善的错误处理确保了框架的稳定性。 