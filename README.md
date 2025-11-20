# FlexQuant Strategies

FlexQuant是一个灵活的A股量化交易策略框架，专注于基于涨停模式的股票选股和回测。该系统支持数据获取、处理、策略选股、回测、投资组合管理和自动调度等完整功能。

## 功能特点

### 1. 数据获取与处理
- 支持从多个数据源（akshare、baostock、tushare）获取A股数据
- 自动判断最近抓取日期，实现增量数据更新
- 支持获取特定股票数据或从文件读取股票列表
- 数据清洗、标准化和特征提取

### 2. 策略选股
- 基于涨停模式的选股策略
- 多维度评分系统（价格、市值、涨停次数、技术指标等）
- 可配置的选股条件和评分权重

### 3. 回测系统
- 支持全市场或特定股票回测
- 可配置初始资金、持仓上限和交易成本
- 完整的绩效指标计算（总收益、年化收益、夏普比率、最大回撤等）
- 可视化回测结果

### 4. 投资组合管理
- 实时监控持仓状态
- 自动记录交易历史
- 生成投资组合报告
- 支持投资组合再平衡

### 5. 自动化调度
- 每日定时执行数据更新和策略选股
- 灵活的配置管理
- 完整的日志记录

## 项目结构
flexquant_strategies/ ├── config/ # 配置文件目录 │ └── config.yaml # 主配置文件 ├── data/ # 数据存储目录 │ ├── raw_data/ # 原始数据 │ ├── processed_data/ # 处理后的数据 │ └── portfolio_data/ # 投资组合数据 ├── logs/ # 日志文件目录 ├── src/ # 源代码目录 │ ├── init.py │ ├── data_fetch.py # 数据获取模块 │ ├── data_processor.py # 数据处理模块 │ ├── strategy.py # 策略选股模块 │ ├── backtester.py # 回测模块 │ ├── portfolio.py # 投资组合管理模块 │ └── scheduler.py # 调度器模块 ├── backtest.py # 回测入口脚本 ├── main.py # 系统主入口 ├── requirements.txt # 依赖包列表 └── README.md # 项目说明文档



## 安装说明

### 1. 克隆仓库

```bash
git clone <repository-url>
cd flexquant_strategies
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

主要依赖包包括：
- pandas
- numpy
- akshare
- baostock
- tushare (可选)
- matplotlib
- scipy
- pyyaml
- apscheduler

### 3. 配置文件

复制并修改配置文件：

```bash
# 确保config目录存在
mkdir -p config

# 配置文件已包含在项目中，可根据需要修改
# config/config.yaml
```

## 使用方法

### 1. 数据获取

#### 全量数据获取
```bash
python main.py fetch --full
```

#### 每日数据更新
```bash
python main.py fetch --daily
```

#### 增量数据获取（自动判断最近日期）
```bash
python main.py fetch --incremental
```

#### 获取特定股票数据
```bash
python main.py fetch --stocks 000001 000002 600000
```

#### 从文件获取股票数据
```bash
python main.py fetch --stock-file stock_list.txt
```

#### 指定日期范围获取数据
```bash
python main.py fetch --stocks 000001 --start-date 2023-01-01 --end-date 2023-12-31
```

### 2. 策略选股

```bash
# 选出评分最高的前10只股票
python main.py select --top 10

# 将结果保存到文件
python main.py select --top 10 --output top_stocks.csv
```

### 3. 执行回测

```bash
# 执行全市场回测
python main.py backtest

# 指定回测日期范围
python main.py backtest --start-date 2023-01-01 --end-date 2023-12-31

# 对特定股票进行回测
python main.py backtest --stock 000001
```

### 4. 投资组合管理

```bash
# 查看投资组合状态
python main.py portfolio --status

# 生成投资组合报告
python main.py portfolio --report
```

### 5. 启动调度器

```bash
# 启动调度器
python main.py scheduler

# 立即执行一次任务并启动调度器
python main.py scheduler --run-now
```

### 6. 直接使用回测脚本

```bash
python backtest.py --mode full --start-date 2023-01-01 --end-date 2023-12-31
```

## 配置说明

配置文件 `config/config.yaml` 包含以下主要部分：

1. **调度器配置**：设置每日任务执行时间、日志级别等
2. **数据获取模块配置**：数据源优先级、路径设置、增量更新等
3. **数据处理模块配置**：涨停阈值、过滤条件、并行度等
4. **策略模块配置**：
   - 选股条件（价格上限、市值上限、涨停次数等）
   - 评分权重设置
   - 卖出规则（止盈止损、持股期限等）
5. **回测模块配置**：初始资金、最大持仓数、交易成本等
6. **投资组合管理配置**：自动更新、再平衡条件等
7. **日志配置**：日志路径、级别、保留策略等

## 策略说明

FlexQuant策略主要基于以下几个维度进行股票选择：

1. **基础条件过滤**：
   - 价格上限（默认20元）
   - 市值上限（默认500亿元）
   - 排除ST股票和停牌股票

2. **涨停模式**：
   - 近90天内有2-3次涨停
   - 涨停后的价格表现

3. **技术指标**：
   - 价格变化趋势
   - 成交量分析
   - 相对强弱指标

4. **评分系统**：
   - 基础条件（20%）
   - 涨停模式（30%）
   - 价格变化（25%）
   - 技术指标（25%）

## 注意事项

1. 数据获取可能受到数据源限制，请合理设置请求间隔
2. 回测结果仅供参考，不构成投资建议
3. 系统需要稳定的网络连接以获取最新数据
4. 对于大量数据的获取，建议在非交易时间执行
5. 定期清理日志文件以节省磁盘空间

## 许可证

[MIT License](LICENSE)

## 更新日志

### v1.0.0
- 初始版本发布
- 实现基础数据获取和处理功能
- 完成策略选股核心逻辑
- 实现回测系统和投资组合管理
- 添加调度器功能

## 联系方式

如有问题或建议，请联系开发团队。
