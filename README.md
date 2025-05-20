# Futurx 量化交易平台

Futurx是一个多市场量化交易平台，支持A股、数字货币等市场的交易策略开发和自动化交易。

## 环境设置

### 方法一：使用conda配置文件

如果你已经安装了Anaconda或Miniconda，可以直接使用环境配置文件创建环境：

```bash
# 克隆仓库
git clone https://your-repository-url/futurx.git
cd futurx

# 使用环境配置文件创建conda环境
conda env create -f environment.yml

# 激活环境
conda activate futurx
```

### 方法二：使用安装脚本

我们提供了一个自动化安装脚本，可以帮助你快速设置开发环境：

```bash
# 克隆仓库
git clone https://your-repository-url/futurx.git
cd futurx

# 运行安装脚本（基础安装）
python setup_conda_env.py

# 运行安装脚本（带可选功能）
python setup_conda_env.py --data-science --qmt --install-dev
```

可用的选项：
- `--env-name`: 指定conda环境名称（默认: "futurx"）
- `--python-version`: 指定Python版本（默认: "3.8"）
- `--data-science`: 安装数据科学相关包
- `--qmt`: 安装QMT相关包
- `--install-dev`: 安装开发工具
- `--repo-url`: 指定要克隆的代码库URL
- `--repo-dir`: 指定代码库保存目录

### 手动安装特殊依赖

某些依赖项（如TA-Lib）可能需要手动安装：

#### TA-Lib安装

**Windows**:
1. 从[这里](http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-msvc.zip)下载TA-Lib预编译库
2. 解压到`C:\ta-lib`
3. 安装Python包装器: `pip install TA-Lib`

**macOS**:
```bash
brew install ta-lib
pip install TA-Lib
```

**Linux**:
```bash
wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz
tar -xzf ta-lib-0.4.0-src.tar.gz
cd ta-lib/
./configure --prefix=/usr
make
sudo make install
pip install TA-Lib
```

## 项目结构

```
futurx/
├── core/                   # 核心功能模块
│   ├── engine/             # 交易引擎
│   ├── strategy/           # 策略框架
│   └── utils/              # 工具函数
├── futurx_qmt/             # QMT集成模块
├── examples/               # 示例代码
├── script/                 # 脚本工具
│   ├── crypto/             # 加密货币相关脚本
│   └── stock/              # 股票相关脚本
├── tests/                  # 测试代码
├── environment.yml         # Conda环境配置
├── setup_conda_env.py      # 环境安装脚本
└── README.md               # 项目说明
```

## 使用示例

### 运行Binance数据订阅测试

```bash
# 激活环境
conda activate futurx

# 运行测试脚本
python script/crypto/binance_data_test.py
```

## 开发指南

1. 激活conda环境：`conda activate futurx`
2. 安装开发模式：`pip install -e .`
3. 运行测试：`pytest tests/`

## 许可证

[许可证信息] 