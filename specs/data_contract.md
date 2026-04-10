# 数据契约文档 (Data Contract) - FlexQuant Strategies

## 1. 概述

本文档定义了 FlexQuant Strategies 系统中所有数据源的统一数据契约，确保不同数据源（Akshare、Baostock、Tushare）的数据能够统一处理，减少因字段不一致导致的各类报错。

## 2. 核心原则

### 2.1 统一性原则
- 系统内部统一使用中文列名
- 所有数据源的数据必须映射到统一的标准化字段
- 保持数据类型的一致性

### 2.2 兼容性原则
- 支持多数据源的自动切换
- 确保字段映射的完整性
- 处理缺失字段的默认值

### 2.3 可扩展性原则
- 便于添加新的数据源
- 支持新字段的扩展
- 保持向后兼容性

## 3. 标准化数据结构

### 3.1 标准字段定义

| 标准字段名 | 数据类型 | 说明 | 必填 | 默认值 |
|-----------|---------|------|------|--------|
| 日期 | pd.Timestamp | 交易日期 | 是 | - |
| 开盘价 | float | 开盘价格 | 是 | - |
| 收盘价 | float | 收盘价格 | 是 | - |
| 最高价 | float | 最高价格 | 是 | - |
| 最低价 | float | 最低价格 | 是 | - |
| 成交量 | float | 成交量（手） | 是 | - |
| 成交额 | float | 成交额（元） | 否 | 0.0 |
| 涨跌幅 | float | 涨跌幅（%） | 否 | 0.0 |
| 换手率 | float | 换手率（%） | 否 | 0.0 |
| 昨收价 | float | 昨日收盘价 | 否 | 收盘价 |
| 总市值 | float | 总市值（元） | 否 | 0.0 |
| 流通市值 | float | 流通市值（元） | 否 | 0.0 |
| 代码 | str | 股票代码 | 否 | - |
| 股票名称 | str | 股票名称 | 否 | - |

### 3.2 技术指标扩展字段

| 标准字段名 | 数据类型 | 说明 | 计算方式 |
|-----------|---------|------|---------|
| ma5 | float | 5日移动平均线 | 收盘价5日均值 |
| ma10 | float | 10日移动平均线 | 收盘价10日均值 |
| ma20 | float | 20日移动平均线 | 收盘价20日均值 |
| ma60 | float | 60日移动平均线 | 收盘价60日均值 |
| rsi | float | 相对强弱指标 | 14日RSI |
| macd | float | MACD指标 | MACD线 |
| macd_signal | float | MACD信号线 | 信号线 |
| macd_hist | float | MACD柱状图 | MACD - Signal |
| kdj_k | float | KDJ指标K值 | K值 |
| kdj_d | float | KDJ指标D值 | D值 |
| kdj_j | float | KDJ指标J值 | J值 |
| is_limit_up | bool | 是否涨停 | 涨跌幅 >= 9.8% |
| limit_up_count | int | 涨停次数 | N日内涨停次数 |
| price_change_n_days | float | N日价格变化 | 当前价格/N日前价格 - 1 |

## 4. 数据源字段映射

### 4.1 Akshare 数据源映射

#### 4.1.1 股票列表数据
```python
AKSHARE_STOCK_LIST_MAPPING = {
    '代码': '代码',           # 股票代码
    '名称': '股票名称',       # 股票名称
    '总市值': '总市值',       # 总市值
    '流通市值': '流通市值'    # 流通市值
}
```

#### 4.1.2 K线数据
```python
AKSHARE_KLINE_MAPPING = {
    '日期': '日期',           # 交易日期
    '开盘': '开盘价',         # 开盘价
    '收盘': '收盘价',         # 收盘价
    '最高': '最高价',         # 最高价
    '最低': '最低价',         # 最低价
    '成交量': '成交量',       # 成交量
    '成交额': '成交额',       # 成交额
    '振幅': '振幅',           # 振幅（可选）
    '涨跌幅': '涨跌幅',       # 涨跌幅
    '涨跌额': '涨跌额',       # 涨跌额（可选）
    '换手率': '换手率'        # 换手率
}
```

#### 4.1.3 数据获取接口
```python
# Akshare 股票列表
stock_zh_a_spot_df = ak.stock_zh_a_spot_em()

# Akshare K线数据
df = ak.stock_zh_a_hist(
    symbol=stock_code,           # 6位股票代码
    period="daily",             # 日线
    start_date=start_date,      # 开始日期
    end_date=end_date,          # 结束日期
    adjust="qfq"                # 前复权
)
```

### 4.2 Baostock 数据源映射

#### 4.2.1 股票列表数据
```python
BAOSTOCK_STOCK_LIST_MAPPING = {
    'code': '代码',             # 股票代码
    'code_name': '股票名称',    # 股票名称
    'ipoDate': '上市日期',      # 上市日期
    'outDate': '退市日期',      # 退市日期
    'type': '股票类型',         # 股票类型
    'status': '股票状态'        # 股票状态
}
```

#### 4.2.2 K线数据
```python
BAOSTOCK_KLINE_MAPPING = {
    'date': '日期',             # 交易日期
    'code': '代码',             # 股票代码
    'open': '开盘价',           # 开盘价
    'high': '最高价',           # 最高价
    'low': '最低价',            # 最低价
    'close': '收盘价',          # 收盘价
    'preclose': '昨收价',       # 昨收价
    'volume': '成交量',         # 成交量
    'amount': '成交额',         # 成交额
    'adjustflag': '复权类型',   # 复权类型
    'turn': '换手率',           # 换手率
    'tradestatus': '交易状态',  # 交易状态
    'pctChg': '涨跌幅',         # 涨跌幅
    'isST': '是否ST'           # 是否ST
}
```

#### 4.2.3 数据获取接口
```python
# Baostock 股票列表
rs = bs.query_stock_basic(code_type="1")  # A股

# Baostock K线数据
rs = bs.query_history_k_data_plus(
    bs_code,                     # 股票代码格式：sh.600000 或 sz.000001
    "date,code,open,high,low,close,preclose,volume,amount,adjustflag,turn,tradestatus,pctChg,isST",
    start_date=start_date,       # 开始日期
    end_date=end_date,           # 结束日期
    frequency="d",              # 日线
    adjustflag="2"               # 前复权
)
```

### 4.3 Tushare 数据源映射

#### 4.3.1 股票列表数据
```python
TUSHARE_STOCK_LIST_MAPPING = {
    'ts_code': '代码',          # 股票代码格式：600000.SH
    'symbol': '股票代码',       # 股票代码
    'name': '股票名称',         # 股票名称
    'area': '地域',             # 所在地域
    'industry': '行业',         # 所属行业
    'market': '市场',           # 交易市场
    'list_date': '上市日期',    # 上市日期
    'status': '股票状态'        # 股票状态
}
```

#### 4.3.2 K线数据
```python
TUSHARE_KLINE_MAPPING = {
    'trade_date': '日期',       # 交易日期
    'ts_code': '代码',          # 股票代码
    'open': '开盘价',           # 开盘价
    'high': '最高价',           # 最高价
    'low': '最低价',            # 最低价
    'close': '收盘价',          # 收盘价
    'pre_close': '昨收价',     # 昨收价
    'vol': '成交量',            # 成交量（手）
    'amount': '成交额',         # 成交额（千元）
    'pct_chg': '涨跌幅',       # 涨跌幅
    'change': '涨跌额'          # 涨跌额
}
```

#### 4.3.3 数据获取接口
```python
# Tushare 股票列表
stock_basic = ts_api.stock_basic(exchange='', list_status='L')

# Tushare K线数据
df = ts_api.daily(
    ts_code=ts_code,             # 股票代码格式：600000.SH
    start_date=start_date,      # 开始日期
    end_date=end_date           # 结束日期
)
```

## 5. 字段映射转换函数

### 5.1 统一字段映射函数
```python
def normalize_column_names(df: pd.DataFrame, source: str) -> pd.DataFrame:
    """
    统一字段名称映射
    
    参数:
        df: 原始数据DataFrame
        source: 数据源类型 ('akshare', 'baostock', 'tushare')
        
    返回:
        标准化后的DataFrame
    """
    mapping_dict = {
        'akshare': AKSHARE_KLINE_MAPPING,
        'baostock': BAOSTOCK_KLINE_MAPPING,
        'tushare': TUSHARE_KLINE_MAPPING
    }
    
    if source in mapping_dict:
        df = df.rename(columns=mapping_dict[source])
    
    return df
```

### 5.2 数据类型转换函数
```python
def convert_data_types(df: pd.DataFrame) -> pd.DataFrame:
    """
    转换数据类型
    
    参数:
        df: 数据DataFrame
        
    返回:
        类型转换后的DataFrame
    """
    # 日期转换
    if '日期' in df.columns:
        df['日期'] = pd.to_datetime(df['日期'])
    
    # 数值类型转换
    numeric_columns = ['开盘价', '收盘价', '最高价', '最低价', '成交量', '成交额', 
                      '涨跌幅', '换手率', '昨收价', '总市值', '流通市值']
    
    for col in numeric_columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    return df
```

### 5.3 数据验证函数
```python
def validate_standard_data(df: pd.DataFrame) -> tuple[bool, str]:
    """
    验证标准化数据的有效性
    
    参数:
        df: 数据DataFrame
        
    返回:
        (是否有效, 错误信息)
    """
    # 检查必填字段
    required_columns = ['日期', '开盘价', '收盘价', '最高价', '最低价', '成交量']
    missing_columns = [col for col in required_columns if col not in df.columns]
    
    if missing_columns:
        return False, f"缺少必填字段: {', '.join(missing_columns)}"
    
    # 检查数据是否为空
    if df.empty:
        return False, "数据为空"
    
    # 检查价格合理性
    if (df['收盘价'] <= 0).any() or (df['开盘价'] <= 0).any():
        return False, "价格数据异常（存在非正值）"
    
    # 检查成交量合理性
    if (df['成交量'] < 0).any():
        return False, "成交量数据异常（存在负值）"
    
    return True, "数据验证通过"
```

## 6. 数据质量保证

### 6.1 数据完整性检查
```python
def check_data_completeness(df: pd.DataFrame, stock_code: str) -> dict:
    """
    检查数据完整性
    
    参数:
        df: 数据DataFrame
        stock_code: 股票代码
        
    返回:
        完整性检查结果字典
    """
    result = {
        'stock_code': stock_code,
        'total_records': len(df),
        'missing_values': {},
        'date_range': None,
        'is_complete': True
    }
    
    # 检查缺失值
    for col in df.columns:
        missing_count = df[col].isna().sum()
        if missing_count > 0:
            result['missing_values'][col] = missing_count
            result['is_complete'] = False
    
    # 检查日期范围
    if '日期' in df.columns and not df.empty:
        result['date_range'] = {
            'start': df['日期'].min(),
            'end': df['日期'].max(),
            'days': (df['日期'].max() - df['日期'].min()).days
        }
    
    return result
```

### 6.2 数据一致性检查
```python
def check_data_consistency(df: pd.DataFrame) -> dict:
    """
    检查数据一致性
    
    参数:
        df: 数据DataFrame
        
    返回:
        一致性检查结果字典
    """
    result = {
        'price_consistency': True,
        'volume_consistency': True,
        'date_consistency': True,
        'issues': []
    }
    
    # 检查价格一致性（最高价 >= 收盘价 >= 最低价）
    if '最高价' in df.columns and '收盘价' in df.columns and '最低价' in df.columns:
        price_issues = df[(df['最高价'] < df['收盘价']) | (df['收盘价'] < df['最低价'])]
        if not price_issues.empty:
            result['price_consistency'] = False
            result['issues'].append(f"价格不一致记录数: {len(price_issues)}")
    
    # 检查成交量一致性
    if '成交量' in df.columns:
        volume_issues = df[df['成交量'] < 0]
        if not volume_issues.empty:
            result['volume_consistency'] = False
            result['issues'].append(f"成交量异常记录数: {len(volume_issues)}")
    
    # 检查日期一致性（按日期排序）
    if '日期' in df.columns:
        df_sorted = df.sort_values('日期')
        if not df['日期'].equals(df_sorted['日期']):
            result['date_consistency'] = False
            result['issues'].append("日期未按顺序排列")
    
    return result
```

### 6.3 数据清洗函数
```python
def clean_standard_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    清洗标准化数据
    
    参数:
        df: 原始数据DataFrame
        
    返回:
        清洗后的DataFrame
    """
    # 删除重复行
    df = df.drop_duplicates(subset=['日期'])
    
    # 删除缺失值（必填字段）
    required_columns = ['日期', '开盘价', '收盘价', '最高价', '最低价', '成交量']
    df = df.dropna(subset=required_columns)
    
    # 删除异常数据
    df = df[(df['收盘价'] > 0) & (df['开盘价'] > 0) & (df['成交量'] >= 0)]
    
    # 按日期排序
    df = df.sort_values('日期')
    
    # 重置索引
    df = df.reset_index(drop=True)
    
    return df
```

## 7. 数据源切换策略

### 7.1 数据源优先级
```python
DATA_SOURCE_PRIORITY = ['akshare', 'baostock', 'tushare']
```

### 7.2 自动切换逻辑
```python
def fetch_with_fallback(stock_code: str, start_date: str, end_date: str, 
                        data_fetcher: DataFetcher) -> pd.DataFrame:
    """
    带自动切换的数据获取函数
    
    参数:
        stock_code: 股票代码
        start_date: 开始日期
        end_date: 结束日期
        data_fetcher: 数据获取器实例
        
    返回:
        股票数据DataFrame
    """
    for source in DATA_SOURCE_PRIORITY:
        try:
            df = data_fetcher.get_each_stock_kline_data(
                stock_code, start_date, end_date, source=source
            )
            if df is not None and not df.empty:
                # 标准化数据
                df = normalize_column_names(df, source)
                df = convert_data_types(df)
                
                # 验证数据
                is_valid, error_msg = validate_standard_data(df)
                if is_valid:
                    logger.info(f"使用 {source} 成功获取 {stock_code} 数据")
                    return df
                else:
                    logger.warning(f"{source} 数据验证失败: {error_msg}")
        except Exception as e:
            logger.warning(f"使用 {source} 获取 {stock_code} 数据失败: {e}")
            continue
    
    logger.error(f"所有数据源均无法获取 {stock_code} 数据")
    return None
```

## 8. 错误处理和日志记录

### 8.1 错误类型定义
```python
class DataContractError(Exception):
    """数据契约错误基类"""
    pass

class FieldMappingError(DataContractError):
    """字段映射错误"""
    pass

class DataTypeConversionError(DataContractError):
    """数据类型转换错误"""
    pass

class DataValidationError(DataContractError):
    """数据验证错误"""
    pass

class DataQualityError(DataContractError):
    """数据质量错误"""
    pass
```

### 8.2 错误处理函数
```python
def handle_data_error(error: Exception, stock_code: str, source: str) -> None:
    """
    处理数据错误
    
    参数:
        error: 异常对象
        stock_code: 股票代码
        source: 数据源
    """
    error_type = type(error).__name__
    error_message = str(error)
    
    logger.error(f"数据错误 [{stock_code}] [{source}] [{error_type}]: {error_message}")
    
    # 根据错误类型采取不同处理策略
    if isinstance(error, FieldMappingError):
        logger.warning(f"字段映射失败，尝试使用备用映射")
    elif isinstance(error, DataValidationError):
        logger.warning(f"数据验证失败，尝试使用备用数据源")
    elif isinstance(error, DataQualityError):
        logger.warning(f"数据质量问题，尝试清洗数据")
```

## 9. 性能优化

### 9.1 批量数据处理
```python
def batch_normalize_data(data_list: list, source: str) -> list:
    """
    批量标准化数据
    
    参数:
        data_list: 数据列表 [(stock_code, df), ...]
        source: 数据源类型
        
    返回:
        标准化后的数据列表
    """
    normalized_list = []
    
    for stock_code, df in data_list:
        try:
            # 标准化字段名
            df = normalize_column_names(df, source)
            
            # 转换数据类型
            df = convert_data_types(df)
            
            # 验证数据
            is_valid, error_msg = validate_standard_data(df)
            if is_valid:
                # 清洗数据
                df = clean_standard_data(df)
                normalized_list.append((stock_code, df))
            else:
                logger.warning(f"{stock_code} 数据验证失败: {error_msg}")
        except Exception as e:
            logger.error(f"标准化 {stock_code} 数据时出错: {e}")
    
    return normalized_list
```

### 9.2 缓存机制
```python
class DataCache:
    """数据缓存类"""
    
    def __init__(self, cache_dir: str = 'data/cache'):
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)
    
    def get_cache_key(self, stock_code: str, start_date: str, end_date: str) -> str:
        """生成缓存键"""
        return f"{stock_code}_{start_date}_{end_date}"
    
    def get_cached_data(self, stock_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """获取缓存数据"""
        cache_key = self.get_cache_key(stock_code, start_date, end_date)
        cache_file = os.path.join(self.cache_dir, f"{cache_key}.parquet")
        
        if os.path.exists(cache_file):
            try:
                return pd.read_parquet(cache_file)
            except Exception as e:
                logger.warning(f"读取缓存失败: {e}")
        
        return None
    
    def set_cached_data(self, stock_code: str, start_date: str, end_date: str, df: pd.DataFrame):
        """设置缓存数据"""
        cache_key = self.get_cache_key(stock_code, start_date, end_date)
        cache_file = os.path.join(self.cache_dir, f"{cache_key}.parquet")
        
        try:
            df.to_parquet(cache_file, index=False, compression='snappy')
        except Exception as e:
            logger.warning(f"写入缓存失败: {e}")
```

## 10. 监控和统计

### 10.1 数据质量监控
```python
class DataQualityMonitor:
    """数据质量监控类"""
    
    def __init__(self):
        self.quality_stats = {
            'total_stocks': 0,
            'successful_fetches': 0,
            'failed_fetches': 0,
            'data_quality_issues': 0,
            'source_usage': {
                'akshare': 0,
                'baostock': 0,
                'tushare': 0
            }
        }
    
    def record_fetch(self, stock_code: str, source: str, success: bool, quality_issues: int = 0):
        """记录数据获取情况"""
        self.quality_stats['total_stocks'] += 1
        
        if success:
            self.quality_stats['successful_fetches'] += 1
            self.quality_stats['source_usage'][source] += 1
        else:
            self.quality_stats['failed_fetches'] += 1
        
        self.quality_stats['data_quality_issues'] += quality_issues
    
    def get_quality_report(self) -> dict:
        """获取质量报告"""
        return {
            'success_rate': self.quality_stats['successful_fetches'] / self.quality_stats['total_stocks'] if self.quality_stats['total_stocks'] > 0 else 0,
            'quality_issue_rate': self.quality_stats['data_quality_issues'] / self.quality_stats['successful_fetches'] if self.quality_stats['successful_fetches'] > 0 else 0,
            'source_distribution': self.quality_stats['source_usage'],
            'total_stats': self.quality_stats
        }
```

## 11. 总结

本文档定义了 FlexQuant Strategies 系统的完整数据契约，包括：

1. **标准化数据结构**：定义了统一的数据字段和类型
2. **数据源映射**：提供了不同数据源的字段映射关系
3. **数据转换函数**：实现了字段映射、类型转换、数据验证等功能
4. **质量保证机制**：确保数据的完整性、一致性和准确性
5. **错误处理策略**：定义了完善的错误处理和日志记录机制
6. **性能优化方案**：提供了批量处理和缓存机制

遵循本文档的规范，可以确保系统在处理多数据源时的稳定性和可靠性，减少因字段不一致导致的各类报错。