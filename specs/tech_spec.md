# 技术设计文档 (Tech Design) - FlexQuant Strategies

## 1. 架构概述
系统采用模块化设计，分为数据获取层、处理层、策略层、应用层和调度层。

- **应用层 (Streamlit)**: 处理用户交互，调用各模块 API。
- **调度层 (APScheduler)**: 负责后台定时任务的管理。
- **策略层 (Strategy & Backtester)**: 实现核心逻辑与验证逻辑。
- **处理层 (DataProcessor)**: 负责数据清洗、特征工程及 Parquet 读写。
- **数据层 (DataFetcher)**: 封装 Akshare/Baostock 等 API 调用。

## 2. 关键技术栈
- **语言**: Python 3.8+
- **存储**: Apache Parquet (Snappy 压缩)
- **UI**: Streamlit
- **可视化**: Plotly (Candlestick & Line Charts)
- **并发**: `concurrent.futures.ThreadPoolExecutor`
- **任务管理**: `schedule` 库与 `APScheduler`

## 3. 数据结构定义

### 3.1 Bar 数据格式
Bar 数据是系统中最基础的数据结构，表示单个股票在单个交易日的完整信息。

#### 3.1.1 标准化字段定义
```python
# 标准化 Bar 数据结构（DataFrame 格式）
BarData = {
    'date': pd.Timestamp,           # 交易日期
    'open': float,                  # 开盘价
    'high': float,                  # 最高价
    'low': float,                   # 最低价
    'close': float,                 # 收盘价
    'volume': float,                # 成交量（手）
    'amount': float,                # 成交额（元）
    'pct_chg': float,               # 涨跌幅（%）
    'turn': float,                  # 换手率（%）
    'preclose': float,              # 昨收价
    'total_market_cap': float,      # 总市值（元）
    'circulating_market_cap': float, # 流通市值（元）
    'code': str,                    # 股票代码
    'name': str                     # 股票名称
}
```

#### 3.1.2 中文列名映射
```python
# 系统内部统一使用中文列名
COLUMN_MAPPING = {
    'date': '日期',
    'open': '开盘价',
    'high': '最高价',
    'low': '最低价',
    'close': '收盘价',
    'volume': '成交量',
    'amount': '成交额',
    'pct_chg': '涨跌幅',
    'turn': '换手率',
    'preclose': '昨收价',
    'total_market_cap': '总市值',
    'circulating_market_cap': '流通市值',
    'code': '代码',
    'name': '股票名称'
}
```

#### 3.1.3 技术指标扩展字段
```python
# 计算后的技术指标字段
TECHNICAL_INDICATORS = {
    'ma5': float,                   # 5日移动平均线
    'ma10': float,                  # 10日移动平均线
    'ma20': float,                  # 20日移动平均线
    'ma60': float,                  # 60日移动平均线
    'rsi': float,                   # 相对强弱指标
    'macd': float,                  # MACD指标
    'macd_signal': float,           # MACD信号线
    'macd_hist': float,             # MACD柱状图
    'kdj_k': float,                 # KDJ指标K值
    'kdj_d': float,                 # KDJ指标D值
    'kdj_j': float,                 # KDJ指标J值
    'is_limit_up': bool,            # 是否涨停
    'limit_up_count': int,          # 涨停次数
    'price_change_n_days': float    # N日价格变化
}
```

### 3.2 持仓数据结构
```python
# 单个持仓信息
Position = {
    'code': str,                    # 股票代码
    'shares': int,                  # 持仓数量
    'avg_price': float,             # 平均买入价格
    'buy_date': pd.Timestamp,       # 买入日期
    'name': str                     # 股票名称
}

# 持仓字典
Positions = Dict[str, Position]     # key: 股票代码
```

### 3.3 交易记录数据结构
```python
# 单笔交易记录
Transaction = {
    'date': pd.Timestamp,           # 交易日期
    'code': str,                    # 股票代码
    'name': str,                    # 股票名称
    'action': str,                  # 交易类型：'BUY' 或 'SELL'
    'price': float,                 # 交易价格
    'shares': int,                  # 交易数量
    'amount': float,                # 交易金额
    'cost': float,                  # 买入成本（仅卖出时）
    'profit': float,                # 盈亏（仅卖出时）
    'profit_percent': float,         # 盈亏百分比（仅卖出时）
    'remaining_capital': float      # 剩余资金
}

# 交易记录列表
Transactions = List[Transaction]
```

### 3.4 投资组合状态数据结构
```python
# 投资组合状态
PortfolioState = {
    'date': pd.Timestamp,           # 日期
    'capital': float,               # 可用资金
    'positions_value': float,        # 持仓市值
    'total_value': float,           # 总资产
    'daily_return': float,          # 日收益率
    'num_positions': int,           # 持仓数量
    'positions': Positions           # 持仓详情
}

# 投资组合历史
PortfolioHistory = List[PortfolioState]
```

### 3.5 回测结果数据结构
```python
# 回测结果指标
BacktestResults = {
    'initial_capital': float,       # 初始资金
    'final_capital': float,         # 最终资金
    'total_return': float,         # 总收益率
    'annual_return': float,         # 年化收益率
    'sharpe_ratio': float,         # 夏普比率
    'max_drawdown': float,          # 最大回撤
    'num_trades': int,             # 交易次数
    'num_buys': int,               # 买入次数
    'num_sells': int,              # 卖出次数
    'win_rate': float,             # 胜率
    'avg_profit': float,           # 平均盈利
    'avg_loss': float,             # 平均亏损
    'backtest_period': str         # 回测期间
}
```

## 4. 回测引擎接口规范

### 4.1 Backtester 类接口

#### 4.1.1 初始化接口
```python
class Backtester:
    def __init__(self, 
                 start_date: str,           # 回测开始日期 'YYYY-MM-DD'
                 end_date: str,             # 回测结束日期 'YYYY-MM-DD'
                 initial_capital: float = 1000000,  # 初始资金
                 max_stocks: int = 5,       # 最大持仓股票数量
                 strategy: FlexStrategy = None,     # 策略对象
                 data_processor: DataProcessor = None)  # 数据处理器
```

#### 4.1.2 核心方法接口
```python
def load_data(self, stock_codes: List[str] = None) -> Dict[str, pd.DataFrame]:
    """
    加载回测所需的数据
    
    参数:
        stock_codes: 股票代码列表，None表示全市场回测
        
    返回:
        股票数据字典 {code: DataFrame}
    """

def run_backtest(self, stock_codes: List[str] = None) -> Dict:
    """
    运行回测
    
    参数:
        stock_codes: 股票代码列表，None表示全市场回测
        
    返回:
        回测结果指标字典
    """

def _execute_daily_trading(self, date: pd.Timestamp, stock_data: Dict[str, pd.DataFrame]):
    """
    执行单日交易（内部方法）
    
    参数:
        date: 交易日期
        stock_data: 股票数据字典
    """

def _process_sell_signals(self, date: pd.Timestamp, daily_stocks: Dict[str, pd.DataFrame]):
    """
    处理卖出信号（内部方法）
    
    参数:
        date: 交易日期
        daily_stocks: 当日有数据的股票字典
    """

def _process_buy_signals(self, date: pd.Timestamp, daily_stocks: Dict[str, pd.DataFrame]):
    """
    处理买入信号（内部方法）
    
    参数:
        date: 交易日期
        daily_stocks: 当日有数据的股票字典
    """

def _buy_stock(self, code: str, date: pd.Timestamp, daily_data: pd.Series, available_capital: float):
    """
    买入股票（内部方法）
    
    参数:
        code: 股票代码
        date: 交易日期
        daily_data: 当日股票数据
        available_capital: 可用于购买的资金
    """

def _sell_stock(self, code: str, date: pd.Timestamp, stock_data: pd.DataFrame):
    """
    卖出股票（内部方法）
    
    参数:
        code: 股票代码
        date: 交易日期
        stock_data: 股票数据
    """

def _record_portfolio_state(self, date: pd.Timestamp):
    """
    记录每日投资组合状态（内部方法）
    
    参数:
        date: 日期
    """

def _calculate_performance_metrics(self) -> Dict:
    """
    计算回测指标（内部方法）
    
    返回:
        回测指标字典
    """

def _save_results(self):
    """
    保存回测结果到文件（内部方法）
    """

def plot_results(self):
    """
    绘制回测结果图表
    """
```

### 4.2 策略接口规范

#### 4.2.1 FlexStrategy 类接口
```python
class FlexStrategy:
    def __init__(self, data_processor: DataProcessor = None, config: Dict = {}):
        """
        初始化策略对象
        
        参数:
            data_processor: 数据处理器对象
            config: 策略配置字典
        """

    def _calculate_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        计算股票的技术特征
        
        参数:
            df: 股票数据
            
        返回:
            添加了特征的股票数据
        """

    def should_buy(self, code: str, daily_data: pd.Series) -> bool:
        """
        判断是否应该买入股票
        
        参数:
            code: 股票代码
            daily_data: 当日股票数据
            
        返回:
            是否应该买入
        """

    def should_sell(self, code: str, daily_data: pd.Series, position: Dict) -> bool:
        """
        判断是否应该卖出股票
        
        参数:
            code: 股票代码
            daily_data: 当日股票数据
            position: 持仓信息
            
        返回:
            是否应该卖出
        """

    def score_stock(self, code: str, daily_data: pd.Series) -> float:
        """
        对股票进行评分，用于排序选股
        
        参数:
            code: 股票代码
            daily_data: 当日股票数据
            
        返回:
            股票评分，越高越好
        """

    def score_and_rank_stocks(self, candidates: Union[Dict, List]) -> List[Dict]:
        """
        对候选股票进行评分和排序
        
        参数:
            candidates: 候选股票数据字典或列表
            
        返回:
            排序后的股票列表
        """
```

## 5. 数据库连接规范

### 5.1 数据存储规范

#### 5.1.1 文件存储结构
```
data/
├── raw_data/                    # 原始数据目录
│   ├── {stock_code}.parquet    # 单个股票的K线数据
│   └── stock_basics.parquet   # 股票基本信息
├── processed_data/              # 处理后数据目录
│   └── {stock_code}.parquet   # 处理后的股票数据
├── portfolio_data/             # 投资组合数据目录
│   ├── current_portfolio.json  # 当前投资组合状态
│   ├── portfolio_history.csv   # 投资组合历史
│   └── transactions.csv       # 交易记录
└── cache/                      # 缓存目录
    └── stock_list.json         # 股票列表缓存
```

#### 5.1.2 数据文件命名规范
- **股票K线数据**: `{stock_code}.parquet`，如 `000001.parquet`
- **股票基本信息**: `stock_basics.parquet`
- **投资组合状态**: `current_portfolio.json`
- **投资组合历史**: `portfolio_history.csv`
- **交易记录**: `transactions.csv`

### 5.2 数据读写规范

#### 5.2.1 Parquet 文件读写
```python
# 读取 Parquet 文件
def read_parquet(file_path: str) -> pd.DataFrame:
    """
    读取 Parquet 文件
    
    参数:
        file_path: 文件路径
        
    返回:
        DataFrame
    """
    return pd.read_parquet(file_path)

# 写入 Parquet 文件
def write_parquet(df: pd.DataFrame, file_path: str):
    """
    写入 Parquet 文件
    
    参数:
        df: 数据框
        file_path: 文件路径
    """
    df.to_parquet(file_path, engine='pyarrow', compression='snappy')
```

#### 5.2.2 CSV 文件读写
```python
# 读取 CSV 文件
def read_csv(file_path: str, encoding: str = 'utf-8') -> pd.DataFrame:
    """
    读取 CSV 文件
    
    参数:
        file_path: 文件路径
        encoding: 文件编码
        
    返回:
        DataFrame
    """
    return pd.read_csv(file_path, encoding=encoding)

# 写入 CSV 文件
def write_csv(df: pd.DataFrame, file_path: str, encoding: str = 'utf-8'):
    """
    写入 CSV 文件
    
    参数:
        df: 数据框
        file_path: 文件路径
        encoding: 文件编码
    """
    df.to_csv(file_path, index=False, encoding=encoding)
```

#### 5.2.3 JSON 文件读写
```python
# 读取 JSON 文件
def read_json(file_path: str, encoding: str = 'utf-8') -> Dict:
    """
    读取 JSON 文件
    
    参数:
        file_path: 文件路径
        encoding: 文件编码
        
    返回:
        字典
    """
    import json
    with open(file_path, 'r', encoding=encoding) as f:
        return json.load(f)

# 写入 JSON 文件
def write_json(data: Dict, file_path: str, encoding: str = 'utf-8'):
    """
    写入 JSON 文件
    
    参数:
        data: 字典数据
        file_path: 文件路径
        encoding: 文件编码
    """
    import json
    with open(file_path, 'w', encoding=encoding) as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)
```

### 5.3 数据访问接口规范

#### 5.3.1 DataProcessor 类接口
```python
class DataProcessor:
    def __init__(self, config: Dict = {}):
        """
        初始化数据处理器
        
        参数:
            config: 配置字典
        """

    def load_stock_data(self, stock_code: str, start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """
        加载股票数据
        
        参数:
            stock_code: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            
        返回:
            股票数据DataFrame
        """

    def save_stock_data(self, stock_code: str, df: pd.DataFrame):
        """
        保存股票数据
        
        参数:
            stock_code: 股票代码
            df: 股票数据DataFrame
        """

    def get_all_available_stocks(self) -> List[str]:
        """
        获取所有可用的股票代码
        
        返回:
            股票代码列表
        """

    def get_latest_price(self, stock_code: str) -> float:
        """
        获取股票最新价格
        
        参数:
            stock_code: 股票代码
            
        返回:
            最新价格
        """
```

### 5.4 数据质量规范

#### 5.4.1 数据验证规则
```python
def validate_bar_data(df: pd.DataFrame) -> bool:
    """
    验证 Bar 数据的有效性
    
    参数:
        df: 股票数据DataFrame
        
    返回:
        是否有效
    """
    # 检查必要字段是否存在
    required_columns = ['日期', '开盘价', '收盘价', '最高价', '最低价', '成交量']
    if not all(col in df.columns for col in required_columns):
        return False
    
    # 检查数据类型
    if df.empty:
        return False
    
    # 检查价格合理性
    if (df['收盘价'] <= 0).any() or (df['开盘价'] <= 0).any():
        return False
    
    # 检查成交量合理性
    if (df['成交量'] < 0).any():
        return False
    
    return True
```

#### 5.4.2 数据清洗规则
```python
def clean_bar_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    清洗 Bar 数据
    
    参数:
        df: 原始数据DataFrame
        
    返回:
        清洗后的DataFrame
    """
    # 删除重复行
    df = df.drop_duplicates(subset=['日期'])
    
    # 删除缺失值
    df = df.dropna(subset=['日期', '开盘价', '收盘价', '最高价', '最低价', '成交量'])
    
    # 按日期排序
    df = df.sort_values('日期')
    
    # 重置索引
    df = df.reset_index(drop=True)
    
    return df
```

## 6. 开发规范 (Coding Standards)

### 6.1 代码风格规范
- **PEP 8**: 遵循 Python PEP 8 代码风格指南
- **命名规范**: 
  - 类名使用大驼峰命名法（PascalCase）
  - 函数和变量名使用小写加下划线（snake_case）
  - 常量使用全大写加下划线（UPPER_SNAKE_CASE）
- **文档字符串**: 所有公共方法必须有文档字符串
- **类型注解**: 重要函数参数和返回值建议添加类型注解

### 6.2 日志规范
- **日志级别**: 
  - DEBUG: 详细的调试信息
  - INFO: 一般信息
  - WARNING: 警告信息
  - ERROR: 错误信息
  - CRITICAL: 严重错误
- **日志格式**: 统一使用 `logging` 模块，各模块应有对应的 Logger 名称
- **日志内容**: 包含时间、模块名、级别、消息

### 6.3 异常处理规范
- **核心循环**: 选股、数据获取等核心循环必须使用 `try-except` 包裹
- **单点故障**: 确保单只股票报错不中断全局任务
- **错误记录**: 详细记录错误信息，便于问题排查
- **用户友好**: 对用户显示友好的错误提示

### 6.4 性能优化规范
- **并发处理**: 使用多线程加速数据获取和处理
- **内存管理**: 及时释放不再使用的大数据对象
- **缓存机制**: 合理使用缓存减少重复计算
- **批量操作**: 尽量使用批量操作代替循环操作

### 6.5 测试规范
- **单元测试**: 核心功能必须有单元测试
- **集成测试**: 重要模块之间必须有集成测试
- **测试覆盖率**: 核心模块测试覆盖率不低于 80%
- **测试数据**: 使用独立的测试数据，不影响生产数据

## 7. 部署与环境

### 7.1 目录依赖
系统运行时需要以下目录结构：
```
flexquant_strategies/
├── config/                      # 配置文件目录
│   └── config.yaml             # 主配置文件
├── data/                       # 数据目录
│   ├── raw_data/               # 原始数据
│   ├── processed_data/         # 处理后数据
│   └── portfolio_data/        # 投资组合数据
├── logs/                       # 日志目录
│   ├── backtest.log           # 回测日志
│   ├── scheduler.log          # 调度日志
│   └── strategy.log          # 策略日志
├── src/                        # 源代码目录
│   ├── backtester.py          # 回测模块
│   ├── data_fetch.py          # 数据获取模块
│   ├── data_processor.py      # 数据处理模块
│   ├── portfolio.py           # 投资组合模块
│   ├── scheduler.py           # 调度模块
│   └── strategy.py            # 策略模块
├── specs/                      # 规范文档目录
│   ├── product_spec.md        # 产品需求文档
│   ├── tech_spec.md           # 技术设计文档
│   ├── system_prompt.md       # 系统提示文档
│   └── data_contract.md       # 数据契约文档
├── app.py                      # Streamlit 应用
├── main.py                     # 主程序入口
├── backtest.py                 # 回测脚本
└── requirements.txt            # 依赖包列表
```

### 7.2 配置管理
- **配置文件**: 所有可变参数必须从 `config/config.yaml` 读取
- **环境变量**: 敏感信息（如 API Token）建议使用环境变量
- **配置验证**: 启动时验证配置的有效性
- **配置热更新**: 支持配置文件的动态更新

### 7.3 依赖管理
- **Python 版本**: Python 3.8+
- **依赖文件**: 使用 `requirements.txt` 管理依赖包
- **虚拟环境**: 建议使用虚拟环境隔离项目依赖
- **依赖更新**: 定期更新依赖包，确保安全性

### 7.4 安全规范
- **敏感信息**: 不将敏感信息提交到版本控制系统
- **API 密钥**: 使用环境变量或配置文件管理 API 密钥
- **数据安全**: 确保数据文件的访问权限设置正确
- **日志安全**: 避免在日志中记录敏感信息

## 8. 版本控制规范

### 8.1 Git 规范
- **分支策略**: 使用 Git Flow 分支模型
- **提交信息**: 使用清晰的提交信息，格式为 `[type] description`
- **代码审查**: 重要功能必须经过代码审查
- **版本标签**: 使用语义化版本号（Semantic Versioning）

### 8.2 文档同步
- **文档更新**: 新功能必须同步更新 `specs/` 目录下的文档
- **README 更新**: 重要变更必须更新 README.md
- **变更日志**: 维护 CHANGELOG.md 记录重要变更

## 9. 监控与维护

### 9.1 系统监控
- **日志监控**: 定期检查日志文件，发现异常情况
- **性能监控**: 监控系统运行性能，及时优化
- **数据监控**: 监控数据质量，确保数据完整性

### 9.2 维护计划
- **定期备份**: 定期备份重要数据和配置文件
- **数据清理**: 定期清理过期数据，释放存储空间
- **系统更新**: 定期更新依赖包和系统组件

### 9.3 故障处理
- **故障检测**: 建立故障检测机制，及时发现系统问题
- **故障恢复**: 制定故障恢复计划，确保系统快速恢复
- **故障分析**: 分析故障原因，制定预防措施