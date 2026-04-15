#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
@Author:            hudoudou-dev
@Email:             humengnju@qq.com
@Create Time:       2025-11-20
@Last Modified:     2025-11-20
@Modified By:       hudoudou-dev
@Version:           1.0
@Description:       stock trading strategy, including buy signals, sell signals, and a stock scoring mechanism
@Notes:             none.
@History:
                    v1.0, create. implemented multi-source stock data fetching functionality.
"""


import os
import pandas as pd
import numpy as np
import logging
import sys
from datetime import datetime, timedelta

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 设置日志
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    handlers=[logging.FileHandler("logs/strategy.log"),
                              logging.StreamHandler()])
logger = logging.getLogger('strategy')


class FlexStrategy:
    """
    股票交易策略类，实现基于涨停模式的选股和交易策略
    """
    
    def __init__(self, data_processor=None, config={}):
        """
        初始化策略对象
        
        参数:
            data_processor: 数据处理器对象，用于获取数据
        """
        self.data_processor = data_processor

        # 策略参数
        self.max_price = config.get('stock_selection', {}).get('max_price', 20.0)  # 股价上限
        self.min_price = config.get('stock_selection', {}).get('min_price', 10.0)  # 股价下限
        self.max_market_cap = config.get('stock_selection', {}).get('max_market_cap', 10.0)  # 市值上限（单位：亿元）
        self.min_limit_up_count = config.get('stock_selection', {}).get('min_limit_up_count', 2)  # 最低涨停次数
        self.max_limit_up_count = config.get('stock_selection', {}).get('max_limit_up_count', 5)  # 最高涨停次数
        self.limit_up_period = config.get('stock_selection', {}).get('limit_up_period', 90)  # 涨停时间范围（天）
        self.max_price_increase = config.get('stock_selection', {}).get('max_price_increase', 30.0)  # 最大价格涨幅（30%）
        self.profit_target = config.get('stock_selection', {}).get('profit_target', 20.0)  # 目标收益率（20%）
        self.stop_loss_ratio = config.get('stock_selection', {}).get('stop_loss_ratio', 10.0)  # 止损比例（10%）
        self.holding_period_limit = config.get('stock_selection', {}).get('holding_period_limit', 30)  # 最大持股天数
        self.min_volume = config.get('stock_selection', {}).get('min_volume', 100.0)  # 最低成交量（万股）
        self.require_profit = config.get('stock_selection', {}).get('require_profit', True)  # 是否要求正盈利
        self.concept_weight = config.get('stock_selection', {}).get('concept_weight', 0.3)   # 概念叠加权重（0-1之间）
        self.limit_up_threshold = config.get('stock_selection', {}).get('limit_up_threshold', 9.8)   # 涨停阈值（百分比）
        
        # 技术指标参数
        tech_config = config.get('technical_indicators', {})
        self.ma_short_window = tech_config.get('ma_short_window', 5)
        self.ma_medium_window = tech_config.get('ma_medium_window', 20)
        self.ma_long_window = tech_config.get('ma_long_window', 60)
        self.rsi_window = tech_config.get('rsi_window', 14)
        self.rsi_overbought_threshold = tech_config.get('rsi_overbought_threshold', 75)
        self.rsi_severe_overbought_threshold = tech_config.get('rsi_severe_overbought_threshold', 80)
        self.rsi_ideal_range_min = tech_config.get('rsi_ideal_range_min', 40)
        self.rsi_ideal_range_max = tech_config.get('rsi_ideal_range_max', 60)
        self.rsi_normal_range_min = tech_config.get('rsi_normal_range_min', 30)
        self.rsi_normal_range_max = tech_config.get('rsi_normal_range_max', 70)
        
        # 评分权重参数
        scoring_config = config.get('scoring_weights', {})
        self.price_factor_weight = scoring_config.get('price_factor_weight', 20)
        self.market_cap_factor_weight = scoring_config.get('market_cap_factor_weight', 15)
        self.limit_up_factor_weight = scoring_config.get('limit_up_factor_weight', 30)
        self.price_change_factor_weight = scoring_config.get('price_change_factor_weight', 20)
        self.ma_bullish_weight = scoring_config.get('ma_bullish_weight', 15)
        self.ma_partial_bullish_weight = scoring_config.get('ma_partial_bullish_weight', 10)
        self.rsi_ideal_weight = scoring_config.get('rsi_ideal_weight', 10)
        self.rsi_normal_weight = scoring_config.get('rsi_normal_weight', 5)

        logger.info(f"Strategy initialized with parameters:")
        logger.info(f"  max_price: {self.max_price}, max_market_cap: {self.max_market_cap}")
        logger.info(f"  max_price_increase: {self.max_price_increase}, profit_target: {self.profit_target}")
        logger.info(f"  stop_loss_ratio: {self.stop_loss_ratio}, holding_period_limit: {self.holding_period_limit} days")
        logger.info(f"  technical_indicators: MA({self.ma_short_window},{self.ma_medium_window},{self.ma_long_window}), RSI({self.rsi_window})")
    
    def get_candidate_stocks(self, start_date, end_date):
        """
        获取候选股票列表，用于全市场回测
        
        参数:
            start_date (str): 开始日期
            end_date (str): 结束日期
            
        返回:
            dict: 候选股票数据字典
        """
        if not self.data_processor:
            logger.error("No data processor provided")
            return {}
        
        try:
            # 获取所有A股代码列表
            stock_list = self.data_processor.get_all_available_stocks()
            logger.info(f"Processing {len(stock_list)} stocks for candidate selection")
            
            candidate_data = {}
            # 为每个股票获取数据
            for code in stock_list:
                try:
                    # 加载处理后的数据
                    # df = self.data_processor.load_processed_data(code)
                    df = self.data_processor.load_stock_data(code)
                    if df is not None and not df.empty:
                        # 过滤日期范围
                        df = df[(df['日期'] >= pd.to_datetime(start_date)) & (df['日期'] <= pd.to_datetime(end_date))]
                        if not df.empty:
                            try:
                                df = self._calculate_features(df)   # 计算额外的特征
                                candidate_data[code] = df
                            except Exception as e:
                                logger.warning(f"Failed to calculate features for {code}: {e}")
                                continue
                except Exception as e:
                    logger.error(f"Error processing stock {code}: {str(e)}")
                    continue
            logger.info(f"Selected {len(candidate_data)} candidate stocks")
            return candidate_data   
        except Exception as outer_e: # 修正 NameError
            logger.error(f"Error in get_candidate_stocks: {str(outer_e)}")
            return {}
    
    def _calculate_features(self, df):
        """
        计算股票的技术特征
        
        参数:
            df (pd.DataFrame): 股票数据
            
        返回:
            pd.DataFrame: 添加了特征的股票数据
        """
        df_new = df.copy()

        # 确保有date列（兼容中文列名）
        if '日期' in df_new.columns and 'date' not in df_new.columns:
            df_new['date'] = df_new['日期']

        # 计算涨停标记（涨幅>=涨停阈值认为是涨停）
        df_new.loc[:, 'is_limit_up'] = (df_new['收盘价'].pct_change() * 100.0) >= self.limit_up_threshold
        
        # 计算N日内涨停次数
        df_new.loc[:, 'limit_up_count'] = df_new['is_limit_up'].rolling(window=self.limit_up_period).sum()
        
        # 计算N日内最大价格变化
        df_new.loc[:, 'price_change_n_days'] = df_new['收盘价'] / df_new['收盘价'].shift(self.limit_up_period) - 1

        # 计算移动平均线
        df_new.loc[:, 'ma5'] = df_new['收盘价'].rolling(window=self.ma_short_window).mean()
        df_new.loc[:, 'ma20'] = df_new['收盘价'].rolling(window=self.ma_medium_window).mean()
        df_new.loc[:, 'ma60'] = df_new['收盘价'].rolling(window=self.ma_long_window).mean()
        
        # 计算相对强弱指标（简化版）
        delta = df_new['收盘价'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=self.rsi_window).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=self.rsi_window).mean()
        rs = gain / loss
        df_new.loc[:, 'rsi'] = 100 - (100 / (1 + rs))
        
        return df_new
    
    def should_buy(self, code, daily_data):
        """
        判断是否应该买入股票
        
        参数:
            code (str): 股票代码
            daily_data (pd.Series): 当日股票数据
            
        返回:
            bool: 是否应该买入
        """
        try:
            # 基础条件检查
            # 1. 股价区间检查
            if not (self.min_price <= daily_data['收盘价'] <= self.max_price):
                logger.debug(f"Buy condition failed for {code} on {daily_data['日期']}: Price {daily_data['收盘价']:.2f} not in [{self.min_price}, {self.max_price}]")
                return False
            
            # 2. 市值上限检查（如果有市值数据）
            if '总市值' in daily_data and not pd.isna(daily_data['总市值']):
                mkt_cap_billion = daily_data['总市值'] / 1e8 if daily_data['总市值'] > 1e6 else daily_data['总市值']
                if mkt_cap_billion > self.max_market_cap:
                    logger.debug(f"Buy condition failed for {code} on {daily_data['日期']}: Market Cap {mkt_cap_billion:.2f}B > {self.max_market_cap:.2f}B")
                    return False
            
            # 3. 盈利检查（如果有净利润数据）
            if self.require_profit and 'net_profit' in daily_data and not pd.isna(daily_data['net_profit']):
                if daily_data['net_profit'] < 0:
                    logger.debug(f"Buy condition failed for {code} on {daily_data['日期']}: Net Profit < 0")
                    return False
            
            # 4. 涨停次数检查
            if 'limit_up_count' in daily_data and not pd.isna(daily_data['limit_up_count']):
                if not (self.min_limit_up_count <= daily_data['limit_up_count'] <= self.max_limit_up_count):
                    logger.debug(f"Buy condition failed for {code} on {daily_data['日期']}: Limit Up Count {daily_data['limit_up_count']} not in [{self.min_limit_up_count}, {self.max_limit_up_count}]")
                    return False
            
            # 5. 阶段涨幅检查
            if 'price_change_n_days' in daily_data and not pd.isna(daily_data['price_change_n_days']):
                if daily_data['price_change_n_days'] > (self.max_price_increase / 100.0):
                    logger.debug(f"Buy condition failed for {code} on {daily_data['日期']}: Price Change {daily_data['price_change_n_days']:.2%} > {self.max_price_increase/100.0:.2%}")
                    return False
            
            # 技术面条件
            # 6. 均线趋势（放宽条件：MA5接近MA20或刚刚金叉）
            if 'ma5' in daily_data and 'ma20' in daily_data and not pd.isna(daily_data['ma5']) and not pd.isna(daily_data['ma20']):
                # 放宽条件：MA5 >= MA20 * 0.95（允许5%的误差）
                if daily_data['ma5'] < daily_data['ma20'] * 0.95:
                    logger.debug(f"Buy condition failed for {code} on {daily_data['日期']}: MA5 ({daily_data['ma5']:.2f}) < MA20 * 0.95 ({daily_data['ma20'] * 0.95:.2f})")
                    return False
            
            # 7. RSI指标（避免过热，RSI < 超买阈值）
            if 'rsi' in daily_data and not pd.isna(daily_data['rsi']):
                if daily_data['rsi'] > self.rsi_overbought_threshold:
                    logger.debug(f"Buy condition failed for {code} on {daily_data['日期']}: RSI ({daily_data['rsi']:.2f}) > {self.rsi_overbought_threshold}")
                    return False
            
            # 8. 成交量检查（如果设置了最低成交量）
            if '成交量' in daily_data and not pd.isna(daily_data['成交量']):
                if daily_data['成交量'] < self.min_volume:
                    logger.debug(f"Buy condition failed for {code} on {daily_data['日期']}: Volume {daily_data['成交量']:.2f} < {self.min_volume:.2f}")
                    return False
            
            # 满足所有条件，可以买入
            logger.debug(f"Buy signal generated for {code} on {daily_data['日期']}")
            return True
            
        except Exception as e:
            logger.error(f"Error in should_buy for {code} on {daily_data['日期']}: {str(e)}")
            return False
    
    def should_sell(self, code, daily_data, position):
        """
        判断是否应该卖出股票
        
        参数:
            code (str): 股票代码
            daily_data (pd.Series): 当日股票数据
            position (dict): 持仓信息
            
        返回:
            bool: 是否应该卖出
        """
        try:
            # 1. 达到目标收益率（止盈）
            buy_price = position['avg_price']
            current_price = daily_data['收盘价']
            profit_ratio = (current_price / buy_price) - 1
            
            if profit_ratio >= self.profit_target:
                logger.debug(f"Sell signal (profit target) for {code} on {daily_data['日期']}: {profit_ratio:.2%} >= {self.profit_target:.2%}")
                return True
            
            # 2. 达到止损条件
            # 注意：止损比例通常是负值，例如 -0.10 表示亏损10%
            if profit_ratio <= -abs(self.stop_loss_ratio / 100.0): # 确保止损比例为负
                logger.debug(f"Sell signal (stop loss) for {code} on {daily_data['日期']}: {profit_ratio:.2%} <= {-abs(self.stop_loss_ratio / 100.0):.2%}")
                return True
            
            # 3. 持股时间过长
            buy_date = position['buy_date']
            current_date = daily_data['日期']
            
            # 计算持股天数
            days_held = (pd.to_datetime(current_date) - pd.to_datetime(buy_date)).days
            
            if days_held >= self.holding_period_limit:
                logger.debug(f"Sell signal (holding period) for {code} on {daily_data['日期']}: {days_held} days >= {self.holding_period_limit} days")
                return True
            
            # 4. 技术面恶化（放宽条件：MA5明显低于MA20才卖出）
            if 'ma5' in daily_data and 'ma20' in daily_data and not pd.isna(daily_data['ma5']) and not pd.isna(daily_data['ma20']):
                # 放宽条件：MA5 < MA20 * 0.90（下跌10%才卖出）
                if daily_data['ma5'] < daily_data['ma20'] * 0.90:
                    logger.debug(f"Sell signal (technical) for {code} on {daily_data['日期']}: MA5 ({daily_data['ma5']:.2f}) < MA20 * 0.90 ({daily_data['ma20'] * 0.90:.2f})")
                    return True
            
            # 5. RSI超买
            if 'rsi' in daily_data and not pd.isna(daily_data['rsi']):
                if daily_data['rsi'] > self.rsi_severe_overbought_threshold:  # 强烈超买
                    logger.debug(f"Sell signal (RSI) for {code} on {daily_data['日期']}: RSI={daily_data['rsi']:.2f} > {self.rsi_severe_overbought_threshold}")
                    return True
            
            # 不满足卖出条件
            logger.debug(f"No sell signal for {code} on {daily_data['日期']}")
            return False
            
        except Exception as e:
            logger.error(f"Error in should_sell for {code} on {daily_data['日期']}: {str(e)}")
            return False  # 出错时保守处理，不卖出
    
    def score_stock(self, code, daily_data):
        """
        对股票进行评分，用于排序选股
        
        参数:
            code (str): 股票代码
            daily_data (pd.Series): 当日股票数据
            
        返回:
            float: 股票评分，越高越好
        """
        try:
            score = 0.0
            
            # 1. 基础条件评分
            # 价格因素（价格越低，评分越高）
            if daily_data['收盘价'] <= self.max_price:
                score += (1 - daily_data['收盘价'] / self.max_price) * self.price_factor_weight
            
            # 市值因素（如果有数据）
            if '总市值' in daily_data and not pd.isna(daily_data['总市值']):
                market_cap_score = max(0, 1 - daily_data['总市值'] / 1e8 / self.max_market_cap) * self.market_cap_factor_weight
                score += market_cap_score
            
            # 2. 涨停模式评分
            if 'limit_up_count' in daily_data and not pd.isna(daily_data['limit_up_count']):
                # 涨停次数在理想范围内给予高分
                if self.min_limit_up_count <= daily_data['limit_up_count'] <= self.max_limit_up_count:
                    score += self.limit_up_factor_weight
                elif daily_data['limit_up_count'] > self.max_limit_up_count:
                    # 涨停次数过多，可能已经过热
                    score += max(0, self.limit_up_factor_weight - (daily_data['limit_up_count'] - self.max_limit_up_count) * 10)
            
            # 3. 价格变化评分
            if 'price_change_n_days' in daily_data and not pd.isna(daily_data['price_change_n_days']):
                # 涨幅适中给予高分，涨幅过大可能过热
                if daily_data['price_change_n_days'] <= self.max_price_increase:
                    score += (1 - daily_data['price_change_n_days'] / self.max_price_increase) * self.price_change_factor_weight
            
            # 4. 技术面评分
            # 均线排列
            if 'ma5' in daily_data and 'ma20' in daily_data and 'ma60' in daily_data and \
               not pd.isna(daily_data['ma5']) and not pd.isna(daily_data['ma20']) and not pd.isna(daily_data['ma60']):
                if daily_data['ma5'] > daily_data['ma20'] > daily_data['ma60']:
                    score += self.ma_bullish_weight
                elif daily_data['ma5'] > daily_data['ma20']:
                    score += self.ma_partial_bullish_weight
            
            # RSI指标
            if 'rsi' in daily_data and not pd.isna(daily_data['rsi']):
                # RSI在理想范围内是较为理想的状态
                if self.rsi_ideal_range_min <= daily_data['rsi'] <= self.rsi_ideal_range_max:
                    score += self.rsi_ideal_weight
                elif self.rsi_normal_range_min <= daily_data['rsi'] < self.rsi_ideal_range_min or self.rsi_ideal_range_max < daily_data['rsi'] <= self.rsi_normal_range_max:
                    score += self.rsi_normal_weight
            
            # 5. 成交量评分（如果有数据）
            if '成交量' in daily_data and '成交量' in daily_data.index:
                # 简化处理，假设成交量较前一交易日有所增加
                pass
            
            logger.debug(f"Stock {code} scored: {score:.2f}")
            return score
            
        except Exception as e:
            logger.error(f"Error in score_stock for {code}: {str(e)}")
            return 0.0  # 出错时返回最低分
    
    def filter_stocks_by_conditions(self, stocks_data, date):
        """
        根据策略条件过滤股票
        
        参数:
            stocks_data (dict): 股票数据字典
            date (str): 过滤日期
            
        返回:
            list: 符合条件的股票列表 [(code, score, data), ...]
        """
        filtered_stocks = []
        
        for code, df in stocks_data.items():
            try:
                # 获取指定日期的数据
                daily_data = df[df['日期'] == date]
                
                if not daily_data.empty:
                    daily_data = daily_data.iloc[0]
                    
                    # 检查买入条件
                    if self.should_buy(code, daily_data):
                        # 计算评分
                        score = self.score_stock(code, daily_data)
                        filtered_stocks.append((code, score, daily_data))
            except Exception as e:
                logger.error(f"Error filtering stock {code}: {str(e)}")
                continue
        
        # 按评分排序
        filtered_stocks.sort(key=lambda x: x[1], reverse=True)
        
        logger.info(f"Filtered {len(filtered_stocks)} stocks for date {date}")
        return filtered_stocks
    
    def get_top_stocks(self, stocks_data, date, top_n=10):
        """
        获取评分最高的前N只股票
        
        参数:
            stocks_data (dict): 股票数据字典
            date (str): 筛选日期
            top_n (int): 返回数量
            
        返回:
            list: 评分最高的前N只股票 [(code, score, data), ...]
        """
        filtered_stocks = self.filter_stocks_by_conditions(stocks_data, date)
        return filtered_stocks[:top_n]
    
    def score_and_rank_stocks(self, candidates):
        """
        对候选股票进行评分和排序
        
        Args:
            candidates (dict or list): 候选股票数据字典或列表
                如果是字典，格式为 {code: df}，df为股票数据DataFrame
                如果是列表，格式为 [(code, df), ...]
                
        Returns:
            list: 排序后的股票列表，每个元素为字典 {'code': str, 'name': str, 'score': float, ...}
        """
        scored_stocks = []
        current_date = datetime.now().strftime('%Y-%m-%d')
        
        try:
            # 处理不同类型的输入
            if isinstance(candidates, dict):
                stocks_to_process = [(code, df) for code, df in candidates.items()]
            elif isinstance(candidates, list):
                stocks_to_process = candidates
            else:
                logger.error(f"候选股票数据格式错误: {type(candidates)}")
                return []
            
            # 为每只股票评分
            for code, df in stocks_to_process:
                try:
                    # 获取最新的可用数据
                    if isinstance(df, pd.DataFrame) and not df.empty:
                        # 尝试获取当前日期或最新日期的数据
                        if 'date' in df.columns:
                            daily_data = df[df['date'] <= current_date].sort_values('date', ascending=False).iloc[0]
                        elif '日期' in df.columns:
                            daily_data = df.sort_values('日期', ascending=False).iloc[0]
                        else:
                            daily_data = df.iloc[0]
                        
                        # 计算评分
                        score = self.score_stock(code, daily_data)
                        
                        # 获取股票名称（如果有）
                        name = daily_data.get('name', daily_data.get('股票名称', code))
                        
                        # 构建结果字典
                        stock_info = {
                            'code': code,
                            'name': name,
                            'score': score,
                            'price': daily_data.get('close', daily_data.get('收盘价', 0)),
                            'date': daily_data.get('date', daily_data.get('日期', current_date))
                        }
                        
                        # 添加涨停次数信息（如果有）
                        if hasattr(daily_data, 'limit_up_count'):
                            stock_info['limit_up_count'] = daily_data['limit_up_count']
                        
                        scored_stocks.append(stock_info)
                except Exception as e:
                    logger.error(f"评分股票 {code} 时出错: {str(e)}")
                    continue
            
            # 按评分降序排序
            scored_stocks.sort(key=lambda x: x['score'], reverse=True)
            
            logger.info(f"完成股票评分和排序，处理了 {len(scored_stocks)} 只股票")
            return scored_stocks
            
        except Exception as e:
            logger.error(f"评分和排序股票时发生错误: {str(e)}")
            return []

    def evaluate_stock_performance(self, code, start_date, end_date):
        """
        评估特定股票在指定时间段内的表现
        
        参数:
            code (str): 股票代码
            start_date (str): 开始日期
            end_date (str): 结束日期
            
        返回:
            dict: 评估结果
        """
        try:
            if not self.data_processor:
                logger.error("No data processor provided for evaluation")
                return None
            
            # 获取股票数据
            df = self.data_processor.load_processed_data(code)
            
            if df is None or df.empty:
                logger.error(f"No data available for stock {code}")
                return None
            
            # 过滤日期范围
            df = df[(df['日期'] >= start_date) & (df['日期'] <= end_date)]
            if df.empty:
                logger.error(f"No data available for stock {code} in date range")
                return None
            
            # 计算基础表现指标
            start_price = df['收盘价'].iloc[0]
            end_price = df['收盘价'].iloc[-1]
            total_return = (end_price / start_price) - 1
            
            # 计算最大回撤
            cumulative_max = df['收盘价'].cummax()
            drawdown = (df['收盘价'] - cumulative_max) / cumulative_max
            max_drawdown = drawdown.min()
            
            # 计算涨停次数
            df['is_limit_up'] = (df['收盘价'].pct_change() * 100 >= self.limit_up_threshold)
            limit_up_count = df['is_limit_up'].sum()
            
            # 计算日均成交量
            avg_volume = df['volume'].mean() if 'volume' in df.columns else 0
            
            # 模拟买卖信号
            buy_signals = []
            sell_signals = []
            position = None
            
            for _, row in df.iterrows():
                if position is None:
                    if self.should_buy(code, row):
                        buy_signals.append({
                            'date': row['日期'],
                            'price': row['收盘价']
                        })
                        position = {'avg_price': row['收盘价'], 'buy_date': row['日期']}
                else:
                    if self.should_sell(code, row, position):
                        sell_signals.append({
                            'date': row['日期'],
                            'price': row['收盘价'],
                            'profit_ratio': (row['收盘价'] / position['avg_price']) - 1
                        })
                        position = None
            
            # 计算策略收益
            strategy_returns = []
            if buy_signals and sell_signals:
                for i, sell in enumerate(sell_signals):
                    if i < len(buy_signals):
                        buy = buy_signals[i]
                        strategy_return = (sell['price'] / buy['price']) - 1
                        strategy_returns.append(strategy_return)
            
            avg_strategy_return = np.mean(strategy_returns) if strategy_returns else 0
            
            evaluation = {
                'code': code,
                'start_date': start_date,
                'end_date': end_date,
                'total_return': total_return,
                'max_drawdown': max_drawdown,
                'limit_up_count': limit_up_count,
                'avg_volume': avg_volume,
                'buy_signals_count': len(buy_signals),
                'sell_signals_count': len(sell_signals),
                'avg_strategy_return': avg_strategy_return,
                'buy_signals': buy_signals,
                'sell_signals': sell_signals
            }
            
            logger.info(f"Evaluation completed for {code}: total_return={total_return:.2%}, "
                      f"buy_signals={len(buy_signals)}, sell_signals={len(sell_signals)}")
            
            return evaluation
            
        except Exception as e:
            logger.error(f"Error evaluating stock {code}: {str(e)}")
            return None


def run_strategy_example():
    """
    策略示例函数，演示如何使用策略类
    """

    print("Strategy example configuration:")
    print("1. Stock selection based on limit up patterns")
    print("2. Buy conditions: ")
    print("   - Price under 20 yuan")
    print("   - Market cap under 50 billion")
    print("   - 2-3 limit ups in recent 3 months")
    print("   - Price increase not too large")
    print("   - Non-loss making")
    print("3. Sell conditions: ")
    print("   - Profit target reached (15%)")
    print("   - Stop loss triggered (-8%)")
    print("   - Holding period too long (30 days)")
    print("   - Technical deterioration")
    
    print("\nNote: To run a real strategy, you need to:")
    print("1. Import your data processor")
    print("2. Initialize it with proper parameters")
    print("3. Create a FlexStrategy instance with this component")
    print("4. Use the strategy methods as needed")
    
    # 示例代码（未运行）:
    """
    from src.data_processor import DataProcessor

    # 初始化数据处理器
    data_processor = DataProcessor()
    
    # 创建策略实例
    strategy = FlexStrategy(data_processor)
    
    # 评估特定股票
    evaluation = strategy.evaluate_stock_performance('000001', '2022-01-01', '2023-12-31')
    
    if evaluation:
        print(f"Stock: {evaluation['code']}")
        print(f"Total Return: {evaluation['total_return']*100:.2f}%")
        print(f"Max Drawdown: {evaluation['max_drawdown']*100:.2f}%")
        print(f"Limit Up Count: {evaluation['limit_up_count']}")
    
    # 获取候选股票（用于回测）
    # candidate_stocks = strategy.get_candidate_stocks('2022-01-01', '2023-12-31')
    """


if __name__ == "__main__":
    # 运行示例
    run_strategy_example()
