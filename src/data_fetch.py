#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
@Author:            hudoudou-dev
@Email:             humengnju@qq.com
@Create Time:       2025-11-20
@Last Modified:     2025-11-20
@Modified By:       hudoudou-dev
@Version:           1.0
@Description:       Responsible for fetching A-share stock data from multiple data sources (akshare, baostock, tushare), 
                    including stock lists, historical K-line data, and basic stock information. 
                    Supports batch fetching of historical data for all stocks and daily incremental data updates.
@Notes:             none.
@History:
                    v1.0, create. implemented multi-source stock data fetching functionality.
"""

import akshare as ak
import baostock as bs
import tushare as ts
import pandas as pd
import os
import time
from datetime import datetime, timedelta
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

raw_data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'raw_data')

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('data_fetch')

class DataFetcher:
    def __init__(self, config=None):
        """
        初始化数据获取器
        :param config: 配置字典, 可选
        """
        self.config = config or {}
        self.raw_data_dir = raw_data_dir
        os.makedirs(self.raw_data_dir, exist_ok=True)
        
        # 初始化 baostock 连接（如果需要）
        self.bs_connected = False
        
        # 尝试使用 tushare（如果有配置）
        self.ts_api = None
        if 'tushare_token' in self.config:
            try:
                self.ts_api = ts.pro_api(self.config['tushare_token'])
                logger.info('Tushare API 初始化成功')
            except Exception as e:
                logger.warning(f'Tushare API 初始化失败: {e}')
    
    def _is_bj_stock(self, stock_code):
        """
        判断是否为北交所或三板股票
        北交所和三板股票代码通常以 8, 4 或 920 等开头
        :param stock_code: 股票代码
        :return: bool
        """
        if not stock_code:
            return False
            
        # 提取核心6位代码
        clean_code = stock_code
        if '.' in stock_code:
            # 处理 sh.600000 或 600000.SH
            parts = stock_code.split('.')
            clean_code = parts[0] if len(parts[0]) == 6 else parts[1]
        elif len(stock_code) > 6:
            # 处理 sh600000
            clean_code = stock_code[-6:]
            
        return clean_code.startswith(('4', '8', '9'))

    def connect_baostock(self):
        """
        连接 Baostock API
        """
        if not self.bs_connected:
            try:
                lg = bs.login()
                if lg.error_code == '0':
                    self.bs_connected = True
                    logger.info('Baostock 连接成功')
                else:
                    logger.error(f'Baostock 连接失败: {lg.error_msg}')
            except Exception as e:
                logger.error(f'Baostock 连接异常: {e}')
        return self.bs_connected
    
    def disconnect_baostock(self):
        """
        断开 Baostock API 连接
        """
        if self.bs_connected:
            bs.logout()
            self.bs_connected = False
            logger.info('Baostock 连接已断开')

    def get_all_stock_codes(self):
        """
        获取所有A股股票代码并保存基本信息快照
        :return: 股票代码列表
        """
        try:
            # 优先使用 akshare 获取股票列表 (EM 接口包含更多有用信息)
            stock_zh_a_spot_df = ak.stock_zh_a_spot_em()
            
            # 保存股票基本信息快照（包含代码、名称、市值等）
            basics_path = os.path.join(self.base_dir, 'data', 'stock_basics.parquet')
            os.makedirs(os.path.dirname(basics_path), exist_ok=True)
            
            # 仅保留关键列并剔除北交所
            basics_df = stock_zh_a_spot_df[['代码', '名称', '总市值', '流通市值']].copy()
            basics_df = basics_df[~basics_df['代码'].apply(self._is_bj_stock)]
            basics_df.to_parquet(basics_path, index=False, compression='snappy')
            
            stock_codes = basics_df['代码'].tolist()
            logger.info(f'成功获取 {len(stock_codes)} 只A股股票代码并保存基本信息快照 (已剔除北交所)')
            return stock_codes
        except Exception as e:
            logger.error(f'使用 akshare 获取股票列表失败: {e}')
            
            # 尝试使用 baostock
            if self.connect_baostock():
                try:
                    rs = bs.query_stock_basic(code_type="1")  # A股
                    data_list = []
                    while (rs.error_code == '0') & rs.next():
                        data_list.append(rs.get_row_data())
                    result = pd.DataFrame(data_list, columns=rs.fields)
                    stock_codes = [code for code in result['code'].tolist() if not self._is_bj_stock(code)]
                    logger.info(f'使用 baostock 成功获取 {len(stock_codes)} 只A股股票代码 (已剔除北交所)')
                    return stock_codes
                except Exception as e:
                    logger.error(f'使用 baostock 获取股票列表失败: {e}')
            
            # 尝试使用 tushare
            if self.ts_api:
                try:
                    stock_basic = self.ts_api.stock_basic(exchange='', list_status='L')
                    stock_codes = [code for code in stock_basic['ts_code'].tolist() if not self._is_bj_stock(code)]
                    logger.info(f'使用 tushare 成功获取 {len(stock_codes)} 只A股股票代码 (已剔除北交所)')
                    return stock_codes
                except Exception as e:
                    logger.error(f'使用 tushare 获取股票列表失败: {e}')
                    
            logger.error('所有数据源均获取股票列表失败')
            return []
    
    def get_each_stock_kline_data(self, stock_code, start_date, end_date=None):
        """
        获取单个股票的历史K线数据
        :param stock_code: 股票代码, 6位数字, 如 '600000'
        :param start_date: 开始日期, 格式: YYYY-MM-DD
        :param end_date: 结束日期, 格式: YYYY-MM-DD, 默认为今天
        :return: 股票历史数据 DataFrame
        """
        if end_date is None:
            end_date = datetime.now().strftime('%Y-%m-%d')
        
        # 校验并剔除北交所股票
        if self._is_bj_stock(stock_code):
            logger.info(f'跳过北交所股票: {stock_code}')
            return None
        
        # 确保输入是6位数字字符串
        if len(stock_code) != 6:
            # 如果是带后缀的(如 600000.SH), 提取前6位
            if '.' in stock_code:
                stock_code = stock_code.split('.')[0]
            # 如果是带前缀的(如 sh600000), 提取后6位
            elif len(stock_code) > 6:
                stock_code = stock_code[-6:]
        
        # 判定市场
        # 沪市: 60, 688, 5xxx; 深市: 00, 30, 002
        market_lower = 'sh' if stock_code.startswith(('6', '5')) else 'sz'
        market_upper = market_lower.upper()
        
        # 1. 尝试使用 akshare
        try:
            # akshare 的 stock_zh_a_hist 通常直接使用 6 位代码
            df = ak.stock_zh_a_hist(symbol=stock_code, period="daily", start_date=start_date.replace('-', ''), 
                                   end_date=end_date.replace('-', ''), adjust="qfq")  # 前复权
            if df is not None and not df.empty:
                # 重命名列以保持一致性
                # akshare 返回: 日期, 开盘, 收盘, 最高, 最低, 成交量, 成交额, 振幅, 涨跌幅, 涨跌额, 换手率
                df.rename(columns={'日期': '日期', '开盘': '开盘价', '收盘': '收盘价', '最高': '最高价', 
                                  '最低': '最低价', '成交量': '成交量', '成交额': '成交额',
                                  '换手率': '换手率', '涨跌幅': '涨跌幅'}, inplace=True)
                
                logger.info(f'使用 akshare 成功获取 {stock_code} 历史数据')
                return df
        except Exception as e:
            logger.warning(f'使用 akshare 获取 {stock_code} 历史数据失败: {e}')
            
        # 2. 尝试使用 baostock
        if self.connect_baostock():
            try:
                # Baostock 股票代码格式为 sh.600000 或 sz.000001
                bs_code = f'{market_lower}.{stock_code}'
                rs = bs.query_history_k_data_plus(bs_code, 
                                                 "date, code, open, high, low, close, preclose, volume, amount, adjustflag, turn, tradestatus, pctChg, isST",
                                                 start_date=start_date, end_date=end_date,
                                                 frequency="d", adjustflag="2")  # 前复权
                
                data_list = []
                while (rs.error_code == '0') & rs.next():
                    data_list.append(rs.get_row_data())
                
                if data_list:
                    df = pd.DataFrame(data_list, columns=rs.fields)
                    # 转换数据类型
                    numeric_cols = ['open', 'high', 'low', 'close', 'preclose', 'volume', 'amount', 'adjustflag', 'turn', 'pctChg']
                    for col in numeric_cols:
                        if col in df.columns:
                            df[col] = pd.to_numeric(df[col], errors='coerce')
                    
                    # 重命名列以保持一致性
                    df.rename(columns={'date': '日期', 'code': '代码', 'open': '开盘价', 'high': '最高价', 
                                      'low': '最低价', 'close': '收盘价', 'preclose': '昨收价', 'volume': '成交量', 'amount': '成交额',
                                      'turn': '换手率', 'pctChg': '涨跌幅'}, inplace=True)
                    
                    logger.info(f'使用 baostock 成功获取 {stock_code} 历史数据')
                    return df
            except Exception as e:
                logger.error(f'使用 baostock 获取 {stock_code} 历史数据失败: {e}')
        
        # 3. 尝试使用 tushare
        if self.ts_api:
            try:
                # Tushare 股票代码格式为 600000.SH 或 000001.SZ
                ts_code = f'{stock_code}.{market_upper}'
                df = self.ts_api.daily(ts_code=ts_code, start_date=start_date.replace('-', ''), end_date=end_date.replace('-', ''))
                
                if df is not None and not df.empty:
                    # 重命名列以保持一致性
                    df.rename(columns={'trade_date': '日期', 'ts_code': '代码', 'open': '开盘价', 'high': '最高价', 
                                      'low': '最低价', 'close': '收盘价', 'vol': '成交量', 'amount': '成交额',
                                      'pct_chg': '涨跌幅'}, inplace=True)
                    
                    # 转换日期格式并排序
                    df['日期'] = pd.to_datetime(df['日期'])
                    df.sort_values('日期', inplace=True)
                    df['日期'] = df['日期'].dt.strftime('%Y-%m-%d')
                    
                    logger.info(f'使用 tushare 成功获取 {stock_code} 历史数据')
                    return df
            except Exception as e:
                logger.error(f'使用 tushare 获取 {stock_code} 历史数据失败: {e}')
        
        logger.error(f'所有数据源均获取 {stock_code} 历史数据失败')
        return None
    
    def _fetch_and_save_single_stock(self, code, start_date, end_date):
        """
        内部辅助方法：抓取并保存单只股票数据
        :param code: 股票代码
        :param start_date: 开始日期
        :param end_date: 结束日期
        :return: (code, success, status)
        """
        # 显式跳过北交所股票
        if self._is_bj_stock(code):
            return code, False, "SKIP_BJ"

        # 检查是否已存在（非重复下载策略）
        file_path = os.path.join(self.raw_data_dir, f'{code}.parquet')
        if os.path.exists(file_path):
            return code, True, "EXISTS"

        # 获取历史数据, 增加重试机制
        df = None
        max_retries = self.config.get('max_retries', 3)
        for attempt in range(max_retries):
            try:
                df = self.get_each_stock_kline_data(code, start_date, end_date)
                if df is not None and not df.empty:
                    break
            except Exception as e:
                logger.warning(f'获取 {code} 数据尝试 {attempt+1} 失败: {e}')
                if attempt < max_retries - 1:
                    time.sleep(1 * (attempt + 1))  # 并发时不宜暂停过久
        
        if df is not None and not df.empty:
            # 仅保留最近 180 个交易日的数据
            df.sort_values('日期', inplace=True)
            df = df.tail(180)
            
            # 保存数据
            df.to_parquet(file_path, index=False, compression='snappy')
            return code, True, "SUCCESS"
        else:
            return code, False, "FAILED"

    def get_all_stocks_kline_datas(self, start_date, end_date=None, max_workers=5):
        """
        并发获取所有股票的历史数据
        :param start_date: 开始日期
        :param end_date: 结束日期
        :param max_workers: 最大工作线程数，默认为5，避免触发接口频率限制
        :return: 成功获取的股票代码列表
        """
        stock_codes = self.get_all_stock_codes()
        success_count = 0
        fail_count = 0
        success_codes = []
        
        logger.info(f"开始并发抓取数据，线程数: {max_workers}，待处理股票总数: {len(stock_codes)}")
        
        # 使用线程池并发抓取
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交任务
            future_to_code = {executor.submit(self._fetch_and_save_single_stock, code, start_date, end_date): code for code in stock_codes}
            
            # 处理结果
            for future in as_completed(future_to_code):
                code = future_to_code[future]
                try:
                    code, success, status = future.result()
                    if success:
                        success_count += 1
                        success_codes.append(code)
                        if status == "SUCCESS":
                            logger.info(f'{code} 数据保存成功')
                        elif status == "EXISTS":
                            logger.info(f'{code} 数据已存在，跳过下载')
                    else:
                        if status == "SKIP_BJ":
                            logger.info(f'跳过北交所股票: {code}')
                        else:
                            fail_count += 1
                            logger.error(f'{code} 数据获取失败')
                except Exception as e:
                    logger.error(f'执行抓取任务时发生异常 ({code}): {e}')
                    fail_count += 1

        logger.info(f'全量数据抓取完成：成功 {success_count} 只, 失败 {fail_count} 只')
        return success_codes

    def fetch_all_stocks_kline_datas(self, start_date=None, end_date=None):
        """
        获取所有股票的历史数据（完整模式）
        :param start_date: 开始日期, 默认为空（从配置或默认值获取）
        :param end_date: 结束日期, 默认为今天
        :return: 成功获取的股票数量
        """

        # 如果未提供开始日期, 使用默认值
        if start_date is None:
            start_date = (datetime.now() - timedelta(days=self.config.get('duration_dates', 180))).strftime('%Y-%m-%d')
        if end_date is None:
            end_date = datetime.now().strftime('%Y-%m-%d')
        logger.info(f'开始全量获取所有股票数据, 日期范围：{start_date} 至 {end_date}')
        
        # 从配置中读取并发线程数，默认为 5
        max_workers = self.config.get('parallel_workers', 5)
        
        # 调用现有的get_all_stocks_kline_datas方法
        success_codes = self.get_all_stocks_kline_datas(start_date, end_date, max_workers=max_workers)
        
        logger.info(f'全量数据获取完成, 成功获取 {len(success_codes)} 只股票')
        return len(success_codes)
    
    def fetch_all_stocks_kline_datas_specific(self, stock_codes, start_date, end_date=None):
        """
        获取指定股票的历史数据
        :param stock_codes: 股票代码列表或字符串（多个代码用逗号分隔）
        :param start_date: 开始日期
        :param end_date: 结束日期, 默认为今天
        :return: 成功获取的股票数量
        """
        # 处理输入参数
        if isinstance(stock_codes, str):
            # 如果是字符串, 按逗号分隔
            stock_codes = [code.strip() for code in stock_codes.split(',')]
        
        if end_date is None:
            end_date = datetime.now().strftime('%Y-%m-%d')
        
        # 默认 180 天数据
        if start_date is None:
            start_date = (datetime.now() - timedelta(days=self.config.get('duration_dates', 180))).strftime('%Y-%m-%d')
        logger.info(f'开始获取指定股票数据, 股票数量：{len(stock_codes)}, 日期范围：{start_date} 至 {end_date}')
        
        success_count = 0
        for i, stock_code in enumerate(stock_codes):
            # 显式跳过北交所股票
            if self._is_bj_stock(stock_code):
                logger.info(f'跳过北交所股票: {stock_code}')
                continue
                
            logger.info(f'正在获取第 {i+1}/{len(stock_codes)} 只股票: {stock_code}')
            
            # 获取历史数据
            df = self.get_each_stock_kline_data(stock_code, start_date, end_date)
            
            if df is not None and not df.empty:
                # 保存数据
                file_path = os.path.join(self.raw_data_dir, f'{stock_code}.parquet')
                df.to_parquet(file_path, index=False, compression='snappy')
                success_count += 1
                logger.info(f'{stock_code} 数据保存成功')
            else:
                logger.error(f'{stock_code} 数据获取失败')
            
            # 避免请求过于频繁
            time.sleep(0.5)
            
            # 每处理10只股票, 暂停一段时间
            if (i + 1) % 10 == 0:
                logger.info(f'已处理 {i+1} 只股票, 休息5秒...')
                time.sleep(5)
        
        logger.info(f'指定股票数据获取完成：成功 {success_count} 只, 失败 {len(stock_codes) - success_count} 只')
        return success_count

    def fetch_all_stocks_kline_datas_incremental(self, start_date=None, end_date=None):
        """
        增量获取股票数据, 只获取最新的数据
        :param start_date: 开始日期, 默认为空（自动计算）
        :param end_date: 结束日期, 默认为今天
        :return: 成功更新的股票数量
        """
        # 如果未提供日期, 使用自动计算的方式
        if end_date is None:
            end_date = datetime.now().strftime('%Y-%m-%d')
        logger.info(f'开始增量更新股票数据, 日期范围：{start_date} 至 {end_date}')
        
        success_count = 0
        # 遍历所有已有的股票数据文件
        for filename in os.listdir(self.raw_data_dir):
            if filename.endswith('.parquet'):
                stock_code = filename[:-8]
                file_path = os.path.join(self.raw_data_dir, filename)
                
                try:
                    # 读取已有数据
                    existing_df = pd.read_parquet(file_path)
                    
                    # 确定增量开始日期
                    if start_date is None:
                        # 获取最后一条记录的日期
                        last_date = pd.to_datetime(existing_df['日期'].iloc[-1])
                        inc_start_date = (last_date + timedelta(days=1)).strftime('%Y-%m-%d')
                    else:
                        inc_start_date = start_date
                    
                    # 如果增量开始日期在结束日期之前, 需要更新
                    if inc_start_date <= end_date:
                        logger.info(f'增量更新 {stock_code} 数据, 从 {inc_start_date} 到 {end_date}')
                        
                        # 获取新数据
                        new_df = self.get_each_stock_kline_data(stock_code, inc_start_date, end_date)
                        
                        if new_df is not None and not new_df.empty:
                            # 合并数据并去重
                            combined_df = pd.concat([existing_df, new_df])
                            combined_df.drop_duplicates(subset=['日期'], keep='last', inplace=True)
                            
                            # 按日期排序
                            combined_df['日期'] = pd.to_datetime(combined_df['日期'])
                            combined_df.sort_values('日期', inplace=True)
                            
                            # 仅保留最近 180 个交易日的数据（滑动窗口策略）
                            combined_df = combined_df.tail(180)
                            
                            # 保存更新后的数据
                            combined_df.to_parquet(file_path, index=False, compression='snappy')
                            success_count += 1
                            logger.info(f'{stock_code} 数据增量更新成功')
                except Exception as e:
                    logger.error(f'增量更新 {stock_code} 数据失败: {e}')
                
                # 避免请求过于频繁
                time.sleep(0.5)
        
        logger.info(f'增量数据更新完成：成功更新 {success_count} 只股票')
        return success_count
    

    def fetch_all_stocks_kline_datas_daily_auto_update(self):
        """
        更新当日数据
        :return: 成功更新的股票数量
        """
        # 获取上一个交易日
        today = datetime.now()
        yesterday = today - timedelta(days=1)
        
        # 遍历所有已有的股票数据文件
        success_count = 0
        
        for filename in os.listdir(self.raw_data_dir):
            if filename.endswith('.parquet'):
                stock_code = filename[:-8]
                file_path = os.path.join(self.raw_data_dir, filename)
                
                try:
                    # 读取已有数据
                    existing_df = pd.read_parquet(file_path)
                    
                    # 获取最后一条记录的日期
                    last_date = pd.to_datetime(existing_df['日期'].iloc[-1]).strftime('%Y-%m-%d')
                    
                    # 如果最后日期不是昨天, 需要更新
                    if last_date != yesterday.strftime('%Y-%m-%d'):
                        logger.info(f'更新 {stock_code} 数据, 从 {last_date} 到 {yesterday.strftime("%Y-%m-%d")}')
                        
                        # 获取新数据
                        new_start_date = (pd.to_datetime(last_date) + timedelta(days=1)).strftime('%Y-%m-%d')
                        new_df = self.get_each_stock_kline_data(stock_code, new_start_date)
                        
                        if new_df is not None and not new_df.empty:
                            # 合并数据并去重
                            combined_df = pd.concat([existing_df, new_df])
                            combined_df.drop_duplicates(subset=['日期'], keep='last', inplace=True)
                            
                            # 按日期排序
                            combined_df['日期'] = pd.to_datetime(combined_df['日期'])
                            combined_df.sort_values('日期', inplace=True)
                            
                            # 仅保留最近 180 个交易日的数据（滑动窗口策略）
                            combined_df = combined_df.tail(180)
                            
                            # 保存更新后的数据
                            combined_df.to_parquet(file_path, index=False, compression='snappy')
                            success_count += 1
                            logger.info(f'{stock_code} 数据更新成功')
                except Exception as e:
                    logger.error(f'更新 {stock_code} 数据失败: {e}')
                
                # 避免请求过于频繁
                time.sleep(0.5)
        
        logger.info(f'每日数据更新完成：成功更新 {success_count} 只股票')
        return success_count

if __name__ == "__main__":
    # 创建数据获取器实例
    fetcher = DataFetcher()
    
    # 测试获取股票列表
    stock_codes = fetcher.get_all_stock_codes()
    print(f"获取到 {len(stock_codes)} 只股票代码")
    print(f"前10只股票: {stock_codes[:10]}")
    
    # 测试获取单只股票数据
    if stock_codes:
        sample_code = stock_codes[0]
        df = fetcher.get_each_stock_kline_data(sample_code, '2023-01-01')
        if df is not None:
            print(f"\n{sample_code} 股票数据样例:")
            print(df.head())
    
    # 断开连接
    fetcher.disconnect_baostock()