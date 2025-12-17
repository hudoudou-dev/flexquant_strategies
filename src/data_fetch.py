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
        func: 获取所有A股股票代码列表
        :return: 股票代码列表
        """
        try:
            # 优先使用 akshare 获取股票列表
            stock_zh_a_spot_df = ak.stock_zh_a_spot()
            # 过滤出股票代码
            stock_codes = stock_zh_a_spot_df['代码'].tolist()
            logger.info(f'成功获取 {len(stock_codes)} 只A股股票代码')
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
                    stock_codes = result['code'].tolist()
                    logger.info(f'使用 baostock 成功获取 {len(stock_codes)} 只A股股票代码')
                    return stock_codes
                except Exception as e:
                    logger.error(f'使用 baostock 获取股票列表失败: {e}')
            
            # 尝试使用 tushare
            if self.ts_api:
                try:
                    stock_basic = self.ts_api.stock_basic(exchange='', list_status='L')
                    stock_codes = stock_basic['ts_code'].tolist()
                    logger.info(f'使用 tushare 成功获取 {len(stock_codes)} 只A股股票代码')
                    return stock_codes
                except Exception as e:
                    logger.error(f'使用 tushare 获取股票列表失败: {e}')
                    
            logger.error('所有数据源均获取股票列表失败')
            return []
    
    def get_stock_history_data(self, stock_code, start_date, end_date=None):
        """
        获取单个股票的历史K线数据
        :param stock_code: 股票代码
        :param start_date: 开始日期, 格式: YYYY-MM-DD
        :param end_date: 结束日期, 格式: YYYY-MM-DD, 默认为今天
        :return: 股票历史数据 DataFrame
        """
        if end_date is None:
            end_date = datetime.now().strftime('%Y-%m-%d')
        
        # 根据股票代码前缀判断市场类型, 用于 akshare
        market = 'sh' if stock_code.startswith(('6', '5')) else 'sz'
        full_code = f'{market}{stock_code}' if len(stock_code) == 6 else stock_code
        
        try:
            # 优先使用 akshare
            df = ak.stock_zh_a_hist(symbol=full_code, period="daily", start_date=start_date, 
                                   end_date=end_date, adjust="qfq")  # 前复权
            logger.info(f'使用 akshare 成功获取 {stock_code} 历史数据')
            return df
        except Exception as e:
            logger.error(f'使用 akshare 获取 {stock_code} 历史数据失败: {e}')
            
            # 尝试使用 baostock
            if self.connect_baostock():
                try:
                    # Baostock 股票代码格式为 000001.SZ 或 600000.SH
                    bs_code = f'{stock_code}.SH' if stock_code.startswith(('6', '5')) else f'{stock_code}.SZ'
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
                                          'low': '最低价', 'close': '收盘价', 'volume': '成交量', 'amount': '成交额',
                                          'turn': '换手率', 'pctChg': '涨跌幅'}, inplace=True)
                        
                        logger.info(f'使用 baostock 成功获取 {stock_code} 历史数据')
                        return df
                except Exception as e:
                    logger.error(f'使用 baostock 获取 {stock_code} 历史数据失败: {e}')
            
            # 尝试使用 tushare
            if self.ts_api:
                try:
                    # Tushare 股票代码格式为 000001.SZ 或 600000.SH
                    ts_code = f'{stock_code}.SH' if stock_code.startswith(('6', '5')) else f'{stock_code}.SZ'
                    df = self.ts_api.daily(ts_code=ts_code, start_date=start_date, end_date=end_date)
                    
                    # 重命名列以保持一致性
                    df.rename(columns={'trade_date': '日期', 'ts_code': '代码', 'open': '开盘价', 'high': '最高价', 
                                      'low': '最低价', 'close': '收盘价', 'vol': '成交量', 'amount': '成交额',
                                      'pct_chg': '涨跌幅'}, inplace=True)
                    
                    # 转换日期格式并排序
                    df['日期'] = pd.to_datetime(df['日期'])
                    df.sort_values('日期', inplace=True)
                    
                    logger.info(f'使用 tushare 成功获取 {stock_code} 历史数据')
                    return df
                except Exception as e:
                    logger.error(f'使用 tushare 获取 {stock_code} 历史数据失败: {e}')
            
            logger.error(f'所有数据源均获取 {stock_code} 历史数据失败')
            return None
    
    def get_stock_basic_info(self, stock_code):
        """
        获取股票基本信息, 包括市值、财务数据等
        :param stock_code: 股票代码
        :return: 基本信息字典
        """
        info = {}
        
        try:
            # 使用 akshare 获取股票基本信息
            stock_info = ak.stock_individual_info_em(stock_code)
            if not stock_info.empty:
                # 将 DataFrame 转换为字典
                for _, row in stock_info.iterrows():
                    info[row['item']] = row['value']
            
            # 获取市值信息
            stock_zh_a_spot_df = ak.stock_zh_a_spot()
            stock_data = stock_zh_a_spot_df[stock_zh_a_spot_df['代码'] == stock_code]
            if not stock_data.empty:
                info['总市值'] = stock_data['总市值'].values[0]
                info['流通市值'] = stock_data['流通市值'].values[0]
                info['市盈率-动态'] = stock_data['市盈率-动态'].values[0]
        except Exception as e:
            logger.error(f'获取 {stock_code} 基本信息失败: {e}')
        
        return info
    
    def fetch_all_stocks_history(self, start_date, end_date=None, max_workers=1):
        """
        获取所有股票的历史数据（此方法可能需要很长时间, 请谨慎使用）
        :param start_date: 开始日期
        :param end_date: 结束日期
        :param max_workers: 最大工作线程数
        :return: 成功获取的股票代码列表
        """
        stock_codes = self.get_all_stock_codes()
        success_count = 0
        fail_count = 0
        success_codes = []
        
        for i, code in enumerate(stock_codes):
            logger.info(f'正在获取第 {i+1}/{len(stock_codes)} 只股票: {code}')
            
            # 获取历史数据
            df = self.get_stock_history_data(code, start_date, end_date)
            
            if df is not None and not df.empty:
                # 保存数据
                file_path = os.path.join(self.raw_data_dir, f'{code}.csv')
                df.to_csv(file_path, index=False, encoding='utf-8-sig')
                success_count += 1
                success_codes.append(code)
                logger.info(f'{code} 数据保存成功')
            else:
                fail_count += 1
                logger.error(f'{code} 数据获取失败')
            
            # 避免请求过于频繁
            time.sleep(0.5)
            
            # 每处理20只股票, 暂停一段时间
            if (i + 1) % 20 == 0:
                logger.info(f'已处理 {i+1} 只股票, 休息10秒...')
                time.sleep(10)
        
        logger.info(f'数据获取完成：成功 {success_count} 只, 失败 {fail_count} 只')
        return success_codes
    
    def update_daily_data(self):
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
            if filename.endswith('.csv'):
                stock_code = filename[:-4]
                file_path = os.path.join(self.raw_data_dir, filename)
                
                try:
                    # 读取已有数据
                    existing_df = pd.read_csv(file_path)
                    
                    # 获取最后一条记录的日期
                    last_date = pd.to_datetime(existing_df['日期'].iloc[-1]).strftime('%Y-%m-%d')
                    
                    # 如果最后日期不是昨天, 需要更新
                    if last_date != yesterday.strftime('%Y-%m-%d'):
                        logger.info(f'更新 {stock_code} 数据, 从 {last_date} 到 {yesterday.strftime("%Y-%m-%d")}')
                        
                        # 获取新数据
                        new_start_date = (pd.to_datetime(last_date) + timedelta(days=1)).strftime('%Y-%m-%d')
                        new_df = self.get_stock_history_data(stock_code, new_start_date)
                        
                        if new_df is not None and not new_df.empty:
                            # 合并数据并去重
                            combined_df = pd.concat([existing_df, new_df])
                            combined_df.drop_duplicates(subset=['日期'], keep='last', inplace=True)
                            
                            # 按日期排序
                            combined_df['日期'] = pd.to_datetime(combined_df['日期'])
                            combined_df.sort_values('日期', inplace=True)
                            combined_df['日期'] = combined_df['日期'].dt.strftime('%Y-%m-%d')
                            
                            # 保存更新后的数据
                            combined_df.to_csv(file_path, index=False, encoding='utf-8-sig')
                            success_count += 1
                            logger.info(f'{stock_code} 数据更新成功')
                except Exception as e:
                    logger.error(f'更新 {stock_code} 数据失败: {e}')
                
                # 避免请求过于频繁
                time.sleep(0.5)
        
        logger.info(f'每日数据更新完成：成功更新 {success_count} 只股票')
        return success_count

    def fetch_all_data(self, start_date=None, end_date=None):
        """
        获取所有股票的历史数据（完整模式）
        :param start_date: 开始日期, 默认为空（从配置或默认值获取）
        :param end_date: 结束日期, 默认为今天
        :return: 成功获取的股票数量
        """

        # 如果未提供开始日期, 使用默认值
        if start_date is None:
            start_date = (datetime.now() - timedelta(days=self.config.get('duration_dates', 3650))).strftime('%Y-%m-%d')
        if end_date is None:
            end_date = datetime.now().strftime('%Y-%m-%d')
        logger.info(f'开始全量获取所有股票数据, 日期范围：{start_date} 至 {end_date}')
        
        # 调用现有的fetch_all_stocks_history方法
        success_codes = self.fetch_all_stocks_history(start_date, end_date)
        
        logger.info(f'全量数据获取完成, 成功获取 {len(success_codes)} 只股票')
        return len(success_codes)
    
    def fetch_incremental_data(self, start_date=None, end_date=None):
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
            if filename.endswith('.csv'):
                stock_code = filename[:-4]
                file_path = os.path.join(self.raw_data_dir, filename)
                
                try:
                    # 读取已有数据
                    existing_df = pd.read_csv(file_path)
                    
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
                        new_df = self.get_stock_history_data(stock_code, inc_start_date, end_date)
                        
                        if new_df is not None and not new_df.empty:
                            # 合并数据并去重
                            combined_df = pd.concat([existing_df, new_df])
                            combined_df.drop_duplicates(subset=['日期'], keep='last', inplace=True)
                            
                            # 按日期排序
                            combined_df['日期'] = pd.to_datetime(combined_df['日期'])
                            combined_df.sort_values('日期', inplace=True)
                            combined_df['日期'] = combined_df['日期'].dt.strftime('%Y-%m-%d')
                            
                            # 保存更新后的数据
                            combined_df.to_csv(file_path, index=False, encoding='utf-8-sig')
                            success_count += 1
                            logger.info(f'{stock_code} 数据增量更新成功')
                except Exception as e:
                    logger.error(f'增量更新 {stock_code} 数据失败: {e}')
                
                # 避免请求过于频繁
                time.sleep(0.5)
        
        logger.info(f'增量数据更新完成：成功更新 {success_count} 只股票')
        return success_count
    
    def fetch_specific_stocks(self, stock_codes, start_date, end_date=None):
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
        
        # 默认10年数据
        if start_date is None:
            start_date = (datetime.now() - timedelta(days=self.config.get('duration_dates', 3650))).strftime('%Y-%m-%d')
        logger.info(f'开始获取指定股票数据, 股票数量：{len(stock_codes)}, 日期范围：{start_date} 至 {end_date}')
        
        success_count = 0
        for i, stock_code in enumerate(stock_codes):
            logger.info(f'正在获取第 {i+1}/{len(stock_codes)} 只股票: {stock_code}')
            
            # 获取历史数据
            df = self.get_stock_history_data(stock_code, start_date, end_date)
            
            if df is not None and not df.empty:
                # 保存数据
                file_path = os.path.join(self.raw_data_dir, f'{stock_code}.csv')
                df.to_csv(file_path, index=False, encoding='utf-8-sig')
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
        df = fetcher.get_stock_history_data(sample_code, '2023-01-01')
        if df is not None:
            print(f"\n{sample_code} 股票数据样例:")
            print(df.head())
    
    # 断开连接
    fetcher.disconnect_baostock()