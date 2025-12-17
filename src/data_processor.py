#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
@Author:            hudoudou-dev
@Email:             humengnju@qq.com
@Create Time:       2025-11-20
@Last Modified:     2025-11-20
@Modified By:       hudoudou-dev
@Version:           1.0
@Description:       Responsible for processing and analyzing stock data, including loading historical data, 
                    calculating limit-up days, calculating price change percentages, batch processing all stock data, 
                    and filtering stocks that meet the preset strategy criteria. Supports data saving and loading functions.
@Notes:             none.
@History:
                    v1.0, create. implemented data processing and strategy filtering functionality.
"""


import pandas as pd
import numpy as np
import os
import logging
from datetime import datetime, timedelta
import glob

# 导入数据获取器
from data_fetch import DataFetcher

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('data_processor')


class DataProcessor:
    def __init__(self, config=None):
        """
        初始化数据处理器
        """
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.raw_data_dir = os.path.join(self.base_dir, 'data', 'raw_data')
        self.processed_data_dir = os.path.join(self.base_dir, 'data', 'processed_data')
        self.portfolio_data_dir = os.path.join(self.base_dir, 'data', 'portfolio_data')
        
        if config is not None:
            self.config = config

        # 创建必要的目录
        os.makedirs(self.processed_data_dir, exist_ok=True)
        os.makedirs(self.portfolio_data_dir, exist_ok=True)
        
        # 初始化数据获取器（用于获取实时数据）
        self.data_fetcher = DataFetcher(config)
    
    def load_stock_data(self, stock_code, start_date=None, end_date=None):
        """
        加载单只股票的历史数据
        :param stock_code: 股票代码
        :param start_date: 开始日期, 格式: YYYY-MM-DD, 默认为None(加载全部)
        :param end_date: 结束日期, 格式: YYYY-MM-DD, 默认为None(加载全部)
        :return: 股票数据 DataFrame
        """
        file_path = os.path.join(self.raw_data_dir, f'{stock_code}.csv')
        if not os.path.exists(file_path):
            logger.error(f'文件不存在: {file_path}')
            return None
        
        try:
            df = pd.read_csv(file_path, encoding='utf-8-sig')
            
            # 确保日期列格式正确
            if '日期' in df.columns:
                df['日期'] = pd.to_datetime(df['日期'])
                
                # 按日期筛选
                if start_date:
                    df = df[df['日期'] >= pd.to_datetime(start_date)]
                if end_date:
                    df = df[df['日期'] <= pd.to_datetime(end_date)]
            return df
        except Exception as e:
            logger.error(f'加载 {stock_code} 数据失败: {e}')
            return None
    
    def get_all_available_stocks(self):
        """
        获取所有可用的股票代码(基于已有的CSV文件)
        :return: 股票代码列表
        """
        stock_files = glob.glob(os.path.join(self.raw_data_dir, '*.csv'))
        stock_codes = [os.path.basename(f).split('.')[0] for f in stock_files]
        return sorted(stock_codes)
    
    def calculate_limit_up_days(self, df, period_days=90):
        """
        计算指定时间段内的涨停天数
        :param df: 股票数据
        :param period_days: 时间段(天), 默认90天(约3个月)
        :return: 涨停天数
        """
        if df is None or df.empty:
            return 0
        
        # 确保日期列存在并排序
        if '日期' not in df.columns:
            logger.error('数据中缺少日期列')
            return 0
        
        df_sorted = df.sort_values('日期', ascending=False)
        
        # 获取最近period_days天的数据
        recent_data = df_sorted.head(period_days)
        
        # 计算涨跌幅列, 如果没有则尝试从其他列计算
        if '涨跌幅' in recent_data.columns:
            # 涨停条件：涨跌幅 >= 9.8%（考虑到四舍五入)
            limit_up_threshold = self.config.get("limit_up_threshold", 9.8)
            limit_up_days = len(recent_data[recent_data['涨跌幅'] >= limit_up_threshold])
        elif '收盘价' in recent_data.columns and '开盘价' in recent_data.columns:
            # 计算涨跌幅
            recent_data['涨跌幅计算'] = (recent_data['收盘价'] - recent_data['开盘价']) / recent_data['开盘价'] * 100
            limit_up_days = len(recent_data[recent_data['涨跌幅计算'] >= 9.8])
        else:
            logger.warning('无法计算涨跌幅, 缺少必要的价格数据')
            limit_up_days = 0
        
        return limit_up_days
    
    def calculate_price_change(self, df, period_days=90):
        """
        计算指定时间段内的价格变化百分比
        :param df: 股票数据
        :param period_days: 时间段（天), 默认90天（约3个月)
        :return: 价格变化百分比
        """
        if df is None or df.empty:
            return 0
        
        # 确保日期列存在并排序
        if '日期' not in df.columns or '收盘价' not in df.columns:
            logger.error('数据中缺少必要的列')
            return 0
        
        df_sorted = df.sort_values('日期', ascending=True)
        
        # 获取最近period_days天的数据
        recent_data = df_sorted.tail(period_days)
        if len(recent_data) < 2:
            return 0
        
        # 计算价格变化百分比
        start_price = recent_data['收盘价'].iloc[0]
        end_price = recent_data['收盘价'].iloc[-1]
        price_change_pct = (end_price - start_price) / start_price * 100
        
        return price_change_pct
    
    def save_processed_data(self, df, filename, directory='processed'):
        """
        保存处理后的数据
        :param df: 要保存的数据
        :param filename: 文件名
        :param directory: 目录类型 ('processed' 或 'portfolio')
        :return: 是否保存成功
        """
        if directory == 'processed':
            save_dir = self.processed_data_dir
        elif directory == 'portfolio':
            save_dir = self.portfolio_data_dir
        else:
            logger.error(f'无效的目录类型: {directory}')
            return False
        
        try:
            file_path = os.path.join(save_dir, filename)
            df.to_csv(file_path, index=False, encoding='utf-8-sig')
            logger.info(f'数据已保存至: {file_path}')
            return True
        except Exception as e:
            logger.error(f'保存数据失败: {e}')
            return False
    
    def load_processed_data(self, filename, directory='processed'):
        """
        加载处理后的数据
        :param filename: 文件名
        :param directory: 目录类型 ('processed' 或 'portfolio')
        :return: 数据 DataFrame
        """
        if directory == 'processed':
            load_dir = self.processed_data_dir
        elif directory == 'portfolio':
            load_dir = self.portfolio_data_dir
        else:
            logger.error(f'无效的目录类型: {directory}')
            return None
        
        file_path = os.path.join(load_dir, filename)
        if not os.path.exists(file_path):
            logger.error(f'文件不存在: {file_path}')
            return None

        try:
            df = pd.read_csv(file_path, encoding='utf-8-sig')
            return df
        except Exception as e:
            logger.error(f'加载数据失败: {e}')
            return None
    
    def batch_process_all_stocks(self, period_days=90, save_results=True):
        """
        批量处理所有股票数据, 计算筛选所需的指标
        :param period_days: 统计周期（天)
        :param save_results: 是否保存结果
        :return: 处理后的汇总数据 DataFrame
        """
        stock_codes = self.get_all_available_stocks()
        results = []
        
        for i, code in enumerate(stock_codes):
            logger.info(f'处理第 {i+1}/{len(stock_codes)} 只股票: {code}')
            
            # 加载股票数据
            df = self.load_stock_data(code)
            
            if df is not None and not df.empty:
                try:
                    # 计算涨停天数
                    limit_up_days = self.calculate_limit_up_days(df, period_days)
                    
                    # 计算价格变化
                    price_change_pct = self.calculate_price_change(df, period_days)
                    
                    # 获取最新价格和日期
                    latest_data = df.sort_values('日期', ascending=False).iloc[0]
                    latest_price = latest_data['收盘价'] if '收盘价' in latest_data else None
                    latest_date = latest_data['日期']
                    
                    # 构建结果字典
                    result = {
                        '股票代码': code,
                        '最近日期': latest_date,
                        '最新价格': latest_price,
                        f'{period_days}天涨停次数': limit_up_days,
                        f'{period_days}天价格变化(%)': price_change_pct
                    }
                    
                    results.append(result)
                except Exception as e:
                    logger.error(f'处理 {code} 时出错: {e}')
            
            # 每处理50只股票输出一次进度
            if (i + 1) % 50 == 0:
                logger.info(f'已处理 {i+1} 只股票')
        
        # 转换为DataFrame
        results_df = pd.DataFrame(results)
        
        # 保存结果
        if save_results and not results_df.empty:
            timestamp = datetime.now().strftime('%Y%m%d')
            self.save_processed_data(results_df, f'stock_metrics_summary_{timestamp}.csv')
        
        logger.info(f'批量处理完成, 共处理 {len(results)} 只股票')
        return results_df
    
    def filter_stocks_by_strategy(self, stock_metrics_df, 
                                 limit_up_nums=2,   # 至少涨停次数
                                 max_price=20,           # 最高价格
                                 max_market_cap=None,    # 最高市值（单位：亿元)
                                 min_price_change=None,  # 最小价格变化百分比
                                 max_price_change=30):   # 最大价格变化百分比
        """
        根据策略筛选股票
        :param stock_metrics_df: 股票指标数据
        :param limit_up_nums: 涨停次数阈值
        :param max_price: 最高价格阈值
        :param max_market_cap: 最高市值阈值
        :param min_price_change: 最小价格变化阈值
        :param max_price_change: 最大价格变化阈值
        :return: 筛选后的股票 DataFrame
        """
        if stock_metrics_df is None or stock_metrics_df.empty:
            logger.warning('输入数据为空, 无法筛选')
            return pd.DataFrame()
        
        # 创建筛选条件
        mask = (stock_metrics_df[f'{90}天涨停次数'] >= limit_up_nums) & \
               (stock_metrics_df['最新价格'] <= max_price)
        
        # 添加价格变化条件
        if min_price_change is not None:
            mask &= (stock_metrics_df[f'{90}天价格变化(%)'] >= min_price_change)
        
        if max_price_change is not None:
            mask &= (stock_metrics_df[f'{90}天价格变化(%)'] <= max_price_change)
        
        # 应用筛选
        filtered_df = stock_metrics_df[mask].copy()
        
        # 如果有市值数据, 进一步筛选
        if max_market_cap is not None and '总市值' in filtered_df.columns:
            filtered_df = filtered_df[filtered_df['总市值'] <= max_market_cap]
        
        # 按涨停次数和价格变化排序
        if not filtered_df.empty:
            filtered_df.sort_values([f'{90}天涨停次数', f'{90}天价格变化(%)'], 
                                   ascending=[False, True], inplace=True)
        
        logger.info(f'筛选完成, 符合条件的股票有 {len(filtered_df)} 只')
        return filtered_df
    
    def update_processed_data_daily(self):
        """
        每日更新处理后的数据
        :return: 更新是否成功
        """
        try:
            # 批量处理所有股票
            period_days = self.config.get('price_change_period', 90)
            results_df = self.batch_process_all_stocks(save_results=True, period_days=period_days)
            
            # 如果处理结果不为空, 进行策略筛选
            if not results_df.empty:
                if self.config is not None:
                    logger.info('开始根据配置筛选股票...')
                    filtered_df = self.filter_stocks_by_strategy(results_df,
                                                                limit_up_nums=self.config.get('limit_up_nums', 2),
                                                                max_price=self.config.get('max_price', 20),
                                                                max_market_cap=self.config.get('max_market_cap', 500.0),
                                                                min_price_change=self.config.get('min_price_change', None),
                                                                max_price_change=self.config.get('max_price_change', None))
                else:
                    filtered_df = self.filter_stocks_by_strategy(results_df)

                # 保存筛选结果
                timestamp = datetime.now().strftime('%Y%m%d')
                self.save_processed_data(filtered_df, f'daily_filtered_stocks_{timestamp}.csv')
                
                logger.info('每日数据处理完成')
                return True
            else:
                logger.warning('处理结果为空, 无法进行筛选')
                return False
        except Exception as e:
            logger.error(f'每日数据处理失败: {e}')
            return False

    # 在update_processed_data_daily()方法之后添加
    def process_daily_data(self):
        """
        处理每日数据, 为选股策略准备数据
        该方法是update_processed_data_daily()的别名, 保持API兼容性
        
        Returns:
            bool: 处理是否成功
        """
        logger.info("开始处理每日数据...")
        return self.update_processed_data_daily()
    
    def get_latest_price(self, stock_code, use_real_time=True):
        """
        获取指定股票的最新收盘价
        :param stock_code: 股票代码
        :param use_real_time: 是否使用实时数据获取（默认为True）
        :return: 最新收盘价(float)，如果获取失败则返回None
        """
        if use_real_time:
            try:
                # 使用实时数据获取
                # 获取最近3天的数据，确保能拿到最新的收盘价
                end_date = datetime.now().strftime('%Y-%m-%d')
                start_date = (datetime.now() - timedelta(days=3)).strftime('%Y-%m-%d')
                
                # 使用DataFetcher获取实时数据
                df = self.data_fetcher.get_stock_history_data(stock_code, start_date, end_date)
                
                if df is not None and not df.empty:
                    # 根据akshare返回的列名获取最新收盘价
                    if '收盘价' in df.columns:
                        # 按日期降序排序，获取最新一条记录
                        latest_data = df.sort_values('日期', ascending=False).iloc[0]
                        return float(latest_data['收盘'])
                    elif 'close' in df.columns:
                        # 按日期降序排序，获取最新一条记录
                        latest_data = df.sort_values('日期', ascending=False).iloc[0]
                        return float(latest_data['close'])
                    else:
                        logger.error(f'{stock_code} 实时数据中缺少收盘价列')
            except Exception as e:
                logger.error(f'使用实时数据获取 {stock_code} 最新价格失败: {e}')
                # 如果实时获取失败，尝试使用本地数据
                
        # 如果不使用实时数据或实时获取失败，使用本地数据
        df = self.load_stock_data(stock_code)
        
        if df is None or df.empty:
            logger.error(f'无法获取 {stock_code} 的数据')
            return None
        
        try:
            # 确保日期列存在并按日期降序排序
            if '日期' not in df.columns:
                logger.error(f'{stock_code} 数据中缺少日期列')
                return None
            
            # 按日期降序排序，获取最新一条记录
            latest_data = df.sort_values('日期', ascending=False).iloc[0]
            
            # 获取收盘价
            if '收盘价' not in latest_data:
                logger.error(f'{stock_code} 数据中缺少收盘价列')
                return None
            
            return float(latest_data['收盘价'])
        except Exception as e:
            logger.error(f'获取 {stock_code} 最新价格时出错: {e}')
            return None


# 测试代码
if __name__ == "__main__":
    # 创建数据处理器实例
    processor = DataProcessor()
    
    # 获取所有可用的股票
    available_stocks = processor.get_all_available_stocks()
    print(f"可用股票数量: {len(available_stocks)}")
    
    # 如果有可用股票, 测试单个股票处理
    if available_stocks:
        sample_code = available_stocks[0]
        print(f"\n测试股票: {sample_code}")
        
        # 加载股票数据
        df = processor.load_stock_data(sample_code)
        if df is not None:
            print(f"数据形状: {df.shape}")
            print(f"数据样例:")
            print(df.tail())
            
            # 计算涨停天数
            limit_up_days = processor.calculate_limit_up_days(df)
            print(f"\n近90天涨停次数: {limit_up_days}")
            
            # 计算价格变化
            price_change = processor.calculate_price_change(df)
            print(f"近90天价格变化(%): {price_change:.2f}")
            
            # 测试获取最新价格
            latest_price = processor.get_latest_price(sample_code)
            print(f"最新价格: {latest_price}")
    
    # 测试批量处理（可选)
    # results = processor.batch_process_all_stocks(save_results=False)
    # if results is not None and not results.empty:
    #     print(f"\n批量处理结果示例:")
    #     print(results.head())