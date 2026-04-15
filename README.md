# FlexQuant Strategies

FlexQuant是一个灵活的A股量化交易策略框架，专注于基于涨停模式的股票选股和回测。该系统支持数据获取、处理、策略选股、回测、投资组合管理和自动调度等完整功能，并提供直观的 Web 交互界面。

## 功能特点

### 1. 可视化交互界面 (Web UI)
- 基于 Streamlit 构建的现代化 Web 界面
- **股票数据概览**: 支持 K 线图展示、市值快照及历史数据滚动预览
- **股票数据更新**: 提供全量、增量及指定股票的图形化更新操作
- **选股策略配置**: 支持在线调整策略超参、定时任务及通知 Webhook
- **选股生成排序**: 自动生成评分 Top 50 推荐清单，支持一键查看 K 线
- **回测分析**: 集成回测引擎，支持自定义参数运行并可视化展示资金曲线及交易记录

### 2. 高效数据管理
- **存储优化**: 采用 Parquet 格式配合 Snappy 压缩，大幅提升 I/O 效率并降低磁盘占用
- **滑动窗口**: 严格执行 180 交易日数据保留策略，确保存储空间可控
- **并发抓取**: 引入 `ThreadPoolExecutor` 实现多线程并发下载，显著提升数据获取速度
- **市场过滤**: 自动剔除北交所股票及 ST/停牌股票，专注于沪深两市 A 股、创业板、科创板股票

### 3. 策略选股与回测
- **涨停策略**: 深度优化基于涨停模式的选股逻辑
- **特征计算**: 自动计算 MA5/20/60、RSI、涨停计数、阶段涨幅等核心指标
- **回测引擎**: 修复日期比较及空交易容错，支持特征自动预计算，确保回测结果准确性

### 4. 自动化与通知推送
- **定时调度**: 每日定时执行数据抓取、特征计算、策略筛选及自动回测
- **多渠道推送**: 集成飞书 (Feishu) 和钉钉 (DingTalk) 机器人，自动发送每日推荐报告及回测总结

## 项目结构
```
flexquant_strategies/
├── config/               # 配置文件目录
│   └── config.yaml       # 主配置文件（含 Webhook 及策略超参）
├── data/                 # 数据存储目录
│   ├── raw_data/         # 股票 K 线数据 (Parquet 格式)
│   ├── processed_data/   # 处理后的中间数据
│   └── portfolio_data/   # 投资组合及回测历史数据
├── logs/                 # 日志文件目录
├── src/                  # 源代码目录
│   ├── data_fetch.py     # 多线程数据获取模块
│   ├── data_processor.py # 数据清洗与归一化模块
│   ├── strategy.py       # 核心策略逻辑与评分模块
│   ├── backtester.py     # 回测引擎模块
│   ├── portfolio.py      # 投资组合管理模块
│   └── scheduler.py      # 自动化调度与通知推送模块
├── app.py                # Streamlit Web UI 入口
├── main.py               # 命令行工具主入口
├── backtest.py           # 回测脚本
├── requirements.txt      # 依赖包列表
├── LICENSE               # MIT License
└── README.md             # 项目说明文档
```

```
ai-native coding skills，example：

“请基于 @product_spec.md 的策略框架，针对 @data_contract.md 定义的数据源，生成一份 proposal 来实现双均线逻辑。完成后请同步更新 @status.md。” 
```

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
- pandas, numpy, scipy: 数据处理
- akshare, baostock, tushare: 数据源
- streamlit, plotly: Web 交互与可视化
- pyyaml, requests: 配置管理与通知推送
- apscheduler: 任务调度
- pyarrow, fastparquet: Parquet 存储支持

### 3. 配置文件

复制并修改配置文件：

```bash
# 确保config目录存在
mkdir -p config

# 配置文件已包含在项目中，可根据需要修改
# 重点配置项：飞书/钉钉 Webhook URL、策略超参、回测初始资金等
# config/config.yaml
```

## 使用方法

### 1. Web 交互界面 (推荐)

启动可视化系统：
```bash
streamlit run app.py
```
启动后即可在浏览器中完成数据获取、策略配置、选股及回测等全流程操作。

### 2. 自动化调度

启动后台定时任务：
```bash
# 启动调度器（每日按配置时间自动执行选股及推送）
python main.py scheduler

# 立即执行一次任务并启动调度器
python main.py scheduler --run-now
```

### 3. 命令行操作 (CLI)

#### 数据获取
```bash
# 全量数据获取
python main.py fetch --full

# 增量数据获取
python main.py fetch --incremental
```

#### 策略选股
```bash
# 选出评分最高的前 50 只股票并保存
python main.py select --top 50 --output top_stocks.csv
```

#### 策略说明

FlexQuant 策略主要基于以下几个维度进行股票选择：

1. **基础过滤条件**：
   - 股价区间：默认 5.0 - 50.0 元（可配置）
   - 市值上限：默认 100 亿元（可配置）
   - 排除 ST、停牌及北交所股票
   - 要求公司最近一个季度非亏损

2. **涨停模式**：
   - 近 180 交易日内有 1-5 次涨停（可配置）
   - 涨停后的价格回调幅度及支撑位（可配置）

3. **技术指标与趋势**：
   - 均线系统：MA5 > MA20 的多头排列趋势
   - 动能指标：RSI 处于 40-70 的非过热区域
   - 成交量：相比前期有明显的放量迹象

4. **动态评分系统**：
   - 评分结果仅保留 Top 50 推荐，支持一键回测验证

### 4. 时间窗口参数说明

**重要提示**：系统中涉及多个时间窗口参数，请确保理解其含义和相互关系，以保证策略逻辑的一致性。

#### 4.1 数据获取与存储窗口

| 参数名称 | 默认值 | 说明 |
|---------|-------|------|
| `data_fetch.duration_dates` | 180 | 数据获取时默认获取的历史数据天数 |
| `data_processor.price_data_days` | 180 | 本地存储的价格数据保留天数 |

**注意**：数据获取窗口应 >= 最长技术指标周期（如MA60需要60天），建议设置为180天以支持完整的回测和评估。

#### 4.2 回测窗口

| 参数名称 | 默认值 | 说明 |
|---------|-------|------|
| `backtester.max_backtest_period` | 180 | 回测时使用的历史数据天数 |
| `backtester.warm_up_period` | 60 | 预热期天数（用于建立技术指标初始状态） |

**关键概念**：
- **回测周期**：实际模拟交易的时间范围，如180天表示模拟过去180天的交易
- **预热期**：回测开始前不进行交易的时期，用于计算技术指标（如MA60需要60天历史数据）
- **实际交易期** = 回测周期 - 预热期

**示例**：
```
回测周期: 180天
预热期: 60天
实际交易期: 120天（第61天开始交易）
```

#### 4.3 选股评估窗口

| 参数名称 | 默认值 | 说明 |
|---------|-------|------|
| `data_processor.price_change_period` | 90 | 统计涨停次数和价格变化的评估周期 |
| `strategy.stock_selection.limit_up_period` | 20 | 涨停统计周期（近20日涨停次数） |

**关键概念**：
- **评估窗口**：用于计算因子、评估股票的时间范围
- **涨停统计周期**：统计涨停次数的具体周期

**示例**：
```
评估窗口: 90天（基于过去90天数据评估股票）
涨停统计: 近20日内涨停次数
```

#### 4.4 技术指标窗口

| 参数名称 | 默认值 | 说明 |
|---------|-------|------|
| `strategy.technical_indicators.ma_short_window` | 5 | 短期均线周期（MA5） |
| `strategy.technical_indicators.ma_medium_window` | 20 | 中期均线周期（MA20） |
| `strategy.technical_indicators.ma_long_window` | 60 | 长期均线周期（MA60） |
| `strategy.technical_indicators.rsi_window` | 14 | RSI计算周期 |

**重要**：技术指标窗口决定了预热期的最小值：
- 使用MA60时，预热期应 >= 60天
- 使用RSI(14)时，预热期应 >= 14天
- **建议**：预热期 >= 最长技术指标周期

#### 4.5 持仓管理窗口

| 参数名称 | 默认值 | 说明 |
|---------|-------|------|
| `strategy.stock_selection.holding_period_limit` | 30 | 最大持股天数 |
| `strategy.stock_selection.profit_target` | 20.0 | 目标收益率（%） |
| `strategy.stock_selection.stop_loss_ratio` | 10.0 | 止损比例（%） |

#### 4.6 窗口参数关系图

```
时间线示例（以180天回测为例）：

|----预热期(60天)----|--------实际交易期(120天)--------|
|                    |                                |
| 不进行交易         | 进行买卖操作                   |
| 计算MA60等指标     | 基于评估窗口选股               |
|                    | 评估窗口=过去90天数据          |
|                    | 涨停统计=过去20天数据          |
```

#### 4.7 参数配置建议

1. **数据获取窗口 >= 回测周期 + 预热期**
   - 示例：回测180天 + 预热60天 = 需要至少240天数据
   - 建议：`duration_dates` 设置为 180-365 天

2. **预热期 >= 最长技术指标周期**
   - 使用MA60时，预热期 >= 60天
   - 使用MA20时，预热期 >= 20天

3. **评估窗口 <= 回测周期**
   - 评估窗口用于选股，应小于等于回测周期
   - 建议：评估窗口 = 60-90天

4. **涨停统计周期 <= 评估窗口**
   - 涨停统计是评估窗口的一部分
   - 建议：涨停统计周期 = 20-30天

#### 4.8 常见配置组合

**保守型配置**（适合长期投资）：
```yaml
backtester:
  max_backtest_period: 360  # 1年回测
  warm_up_period: 60        # MA60预热
strategy:
  stock_selection:
    limit_up_period: 30     # 30日涨停统计
data_processor:
  price_change_period: 90   # 90日评估窗口
```

**激进型配置**（适合短期交易）：
```yaml
backtester:
  max_backtest_period: 90   # 3个月回测
  warm_up_period: 20        # MA20预热
strategy:
  stock_selection:
    limit_up_period: 10     # 10日涨停统计
data_processor:
  price_change_period: 30   # 30日评估窗口
```

**推荐配置**（平衡型）：
```yaml
backtester:
  max_backtest_period: 180  # 半年回测
  warm_up_period: 60        # MA60预热
strategy:
  stock_selection:
    limit_up_period: 20     # 20日涨停统计
data_processor:
  price_change_period: 90   # 90日评估窗口
```

## 更新日志

### v1.1.0
- **UI 重构**: 推出基于 Streamlit 的全中文可视化界面。
- **回测升级**: 集成回测引擎至 Web 端，支持资金曲线与交易明细展示。
- **存储优化**: 全面转向 Parquet 存储，数据保留窗口调整为 180 交易日。
- **性能提升**: 引入多线程并发抓取，大幅缩短全量下载时间。
- **推送集成**: 支持飞书与钉钉 Webhook 自动推送每日任务报告。
- **Bug 修复**: 修复了日期类型比较、空交易处理及北交所代码识别等问题。

### v1.0.0
- 初始版本发布，实现基础数据获取与命令行选股逻辑。

## 联系方式

如有问题或建议，请联系开发团队。
