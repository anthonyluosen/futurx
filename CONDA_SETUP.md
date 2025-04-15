# Futurx Python 3.10 环境设置指南

本文档介绍如何为Futurx项目创建和配置基于Python 3.10的Conda环境。

## 方法一：使用环境配置文件（推荐）

使用环境配置文件是最简单的方法：

```bash
# 创建环境
conda env create -f environment.yml

# 激活环境
conda activate futurx
```

## 方法二：使用Python脚本

我们提供了一个简单的Python脚本来创建环境：

```bash
# 运行创建环境脚本
python create_env.py
```

## 方法三：手动创建

如果您希望手动创建环境，可以使用以下命令：

```bash
# 创建环境
conda create -y -n futurx python=3.10

# 激活环境
conda activate futurx
```
