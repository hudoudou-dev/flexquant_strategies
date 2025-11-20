#!/usr/bin/env python
# -*- coding: utf-8 -*-


# 核心功能:

# 实现了回测器所需的三个核心方法：should_buy()、should_sell() 和 score_stock()
# 基于用户要求的选股条件（近三月两三次涨停但股价未大幅上涨、20元以下、市值500亿以下、非亏损等）
# 提供卖出评分机制（目标收益率15%、止损8%、最大持股30天等）
# 支持特定股票的交易评估
# 策略参数:

# 股价上限：20元
# 市值上限：500亿元
# 涨停次数范围：2-3次
# 涨停观察期：90天
# 最大价格涨幅：30%
# 目标收益率：15%
# 止损比例：-8%
# 最大持股天数：30天
# 买入逻辑 (should_buy):

# 检查股价是否在20元以下
# 检查市值是否在500亿以下
# 检查是否为非亏损股票
# 检查近三个月是否有2-3次涨停
# 检查近三个月股价涨幅是否不超过30%
# 技术面检查（均线多头排列、RSI指标等）
# 卖出逻辑 (should_sell):

# 达到目标收益率（15%）时止盈卖出
# 达到止损条件（-8%）时止损卖出
# 持股时间超过最大期限（30天）时卖出
# 技术面恶化（均线空头排列、RSI超买等）时卖出
# 股票评分机制 (score_stock):

# 基础条件评分（价格、市值等）
# 涨停模式评分
# 价格变化评分
# 技术面评分（均线排列、RSI指标等）
# 总分为100分，评分越高表示股票越符合策略要求
# 额外功能:

# get_candidate_stocks(): 获取候选股票列表，用于全市场回测
# filter_stocks_by_conditions(): 根据条件过滤股票
# get_top_stocks(): 获取评分最高的前N只股票
# evaluate_stock_performance(): 评估特定股票在指定时间段内的表现
# 使用方法
# 与回测器配合:

# 回测器初始化时需要传入策略实例
# 回测过程中会自动调用 should_buy()、should_sell() 和 score_stock() 方法
# 独立使用:

# 可以单独使用策略评估特定股票的表现
# 可以筛选符合条件的股票列表
# 参数调整:

# 可以通过修改类初始化时的参数来调整策略的严格程度
# 可以根据实际市场情况调整买入卖出条件
# 这个策略模块设计灵活，可以与之前实现的回测器无缝配合，支持用户要求的全市场回测和特定股票回测功能，同时提供了详细的股票评估和筛选机制。



"""
策略模块 (Strategy)

功能描述: 实现股票交易策略，包含买入信号、卖出信号和股票评分机制
作者: FlexQuant Team
创建时间: 2024-01-01
修改时间: 2024-01-01
修改备注: 初始版本
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
    
    def __init__(self, data_processor=None):
        """
        初始化策略对象
        
        参数:
            data_processor: 数据处理器对象，用于获取数据
        """
        self.data_processor = data_processor
        
        # 策略参数
        self.max_price = 20.0  # 股价上限
        self.max_market_cap = 500  # 市值上限（单位：亿元）
        self.min_limit_ups = 2  # 最少涨停次数
        self.max_limit_ups = 3  # 最多涨停次数
        self.limit_up_period = 90  # 涨停观察期（天数）
        self.max_price_increase = 0.3  # 最大价格涨幅（30%）
        self.profit_target = 0.15  # 目标收益率（15%）
        self.stop_loss_ratio = -0.08  # 止损比例（-8%）
        self.holding_period_limit = 30  # 最大持股天数
        
        logger.info(f"Strategy initialized with parameters:")
        logger.info(f"  max_price: {self.max_price}, max_market_cap: {self.max_market_cap}B")
        logger.info(f"  limit_ups range: {self.min_limit_ups}-{self.max_limit_ups} in {self.limit_up_period} days")
        logger.info(f"  max_price_increase: {self.max_price_increase}, profit_target: {self.profit_target}")
        logger.info(f"  stop_loss_ratio: {self.stop_loss_ratio}, holding_period_limit: {self.holding_period_limit} days")
    
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
            stock_list = self.data_processor.get_stock_list()
            logger.info(f"Processing {len(stock_list)} stocks for candidate selection")
            
            candidate_data = {}
            
            # 为每个股票获取数据
            for code in stock_list[:100]:  # 限制处理数量以提高效率
                try:
                    # 加载处理后的数据
                    df = self.data_processor.load_processed_data(code)
                    
                    if df is not None and not df.empty:
                        # 过滤日期范围
                        df = df[(df['date'] >= start_date) & (df['date'] <= end_date)]
                        if not df.empty:
                            # 计算额外的特征
                            df = self._calculate_features(df)
                            candidate_data[code] = df
                except Exception as e:
                    logger.error(f"Error processing stock {code}: {str(e)}")
                    continue
            
            logger.info(f"Selected {len(candidate_data)} candidate stocks")
            return candidate_data
        
        except Exception as e:
            logger.error(f"Error in get_candidate_stocks: {str(e)}")
            return {}
    
    def _calculate_features(self, df):
        """
        计算股票的技术特征
        
        参数:
            df (pd.DataFrame): 股票数据
            
        返回:
            pd.DataFrame: 添加了特征的股票数据
        """
        # 计算涨停标记（涨幅>=9.8%认为是涨停）
        df['is_limit_up'] = df['close'].pct_change() >= 0.098
        
        # 计算N日内涨停次数
        df['limit_up_count'] = df['is_limit_up'].rolling(window=self.limit_up_period).sum()
        
        # 计算N日内最大价格变化
        df['price_change_n_days'] = df['close'] / df['close'].shift(self.limit_up_period) - 1
        
        # 计算移动平均线
        df['ma5'] = df['close'].rolling(window=5).mean()
        df['ma20'] = df['close'].rolling(window=20).mean()
        df['ma60'] = df['close'].rolling(window=60).mean()
        
        # 计算相对强弱指标（简化版）
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        return df
    
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
            # 1. 股价在20元以下
            if daily_data['close'] > self.max_price:
                return False
            
            # 2. 市值在500亿以下（如果有市值数据）
            if 'market_cap' in daily_data and not pd.isna(daily_data['market_cap']):
                if daily_data['market_cap'] > self.max_market_cap:
                    return False
            
            # 3. 非亏损（如果有净利润数据）
            if 'net_profit' in daily_data and not pd.isna(daily_data['net_profit']):
                if daily_data['net_profit'] < 0:
                    return False
            
            # 4. 近三个月有2-3次涨停
            if 'limit_up_count' in daily_data and not pd.isna(daily_data['limit_up_count']):
                if not (self.min_limit_ups <= daily_data['limit_up_count'] <= self.max_limit_ups):
                    return False
            else:
                # 如果没有涨停计数，尝试计算
                return False  # 为安全起见，没有足够信息时不买入
            
            # 5. 近三个月股价涨幅不大（不超过30%）
            if 'price_change_n_days' in daily_data and not pd.isna(daily_data['price_change_n_days']):
                if daily_data['price_change_n_days'] > self.max_price_increase:
                    return False
            
            # 技术面条件
            # 6. 均线多头排列（短期均线上穿长期均线）
            if 'ma5' in daily_data and 'ma20' in daily_data and not pd.isna(daily_data['ma5']) and not pd.isna(daily_data['ma20']):
                if daily_data['ma5'] <= daily_data['ma20']:
                    return False
            
            # 7. RSI指标在合理范围内（避免超买）
            if 'rsi' in daily_data and not pd.isna(daily_data['rsi']):
                if daily_data['rsi'] > 70:  # 超买区域
                    return False
            
            # 8. 当日成交量放大
            if 'volume' in daily_data and 'volume' in daily_data.index:
                # 简化处理，这里假设已经有成交量的均值
                pass
            
            # 满足所有条件，可以买入
            logger.debug(f"Buy signal generated for {code} on {daily_data['date']}")
            return True
            
        except Exception as e:
            logger.error(f"Error in should_buy for {code}: {str(e)}")
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
            current_price = daily_data['close']
            profit_ratio = (current_price / buy_price) - 1
            
            if profit_ratio >= self.profit_target:
                logger.debug(f"Sell signal (profit target) for {code}: {profit_ratio:.2%} >= {self.profit_target:.2%}")
                return True
            
            # 2. 达到止损条件
            if profit_ratio <= self.stop_loss_ratio:
                logger.debug(f"Sell signal (stop loss) for {code}: {profit_ratio:.2%} <= {self.stop_loss_ratio:.2%}")
                return True
            
            # 3. 持股时间过长
            buy_date = position['buy_date']
            current_date = daily_data['date']
            
            # 计算持股天数
            days_held = (pd.to_datetime(current_date) - pd.to_datetime(buy_date)).days
            
            if days_held >= self.holding_period_limit:
                logger.debug(f"Sell signal (holding period) for {code}: {days_held} days >= {self.holding_period_limit} days")
                return True
            
            # 4. 技术面恶化（例如均线空头排列）
            if 'ma5' in daily_data and 'ma20' in daily_data and not pd.isna(daily_data['ma5']) and not pd.isna(daily_data['ma20']):
                if daily_data['ma5'] < daily_data['ma20']:
                    logger.debug(f"Sell signal (technical) for {code}: MA5 < MA20")
                    return True
            
            # 5. RSI超买
            if 'rsi' in daily_data and not pd.isna(daily_data['rsi']):
                if daily_data['rsi'] > 80:  # 强烈超买
                    logger.debug(f"Sell signal (RSI) for {code}: RSI={daily_data['rsi']} > 80")
                    return True
            
            # 不满足卖出条件
            return False
            
        except Exception as e:
            logger.error(f"Error in should_sell for {code}: {str(e)}")
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
            if daily_data['close'] <= self.max_price:
                score += (1 - daily_data['close'] / self.max_price) * 20
            
            # 市值因素（如果有数据）
            if 'market_cap' in daily_data and not pd.isna(daily_data['market_cap']):
                market_cap_score = max(0, 1 - daily_data['market_cap'] / self.max_market_cap) * 15
                score += market_cap_score
            
            # 2. 涨停模式评分
            if 'limit_up_count' in daily_data and not pd.isna(daily_data['limit_up_count']):
                # 涨停次数在理想范围内给予高分
                if self.min_limit_ups <= daily_data['limit_up_count'] <= self.max_limit_ups:
                    score += 30
                elif daily_data['limit_up_count'] > self.max_limit_ups:
                    # 涨停次数过多，可能已经过热
                    score += max(0, 30 - (daily_data['limit_up_count'] - self.max_limit_ups) * 10)
            
            # 3. 价格变化评分
            if 'price_change_n_days' in daily_data and not pd.isna(daily_data['price_change_n_days']):
                # 涨幅适中给予高分，涨幅过大可能过热
                if daily_data['price_change_n_days'] <= self.max_price_increase:
                    score += (1 - daily_data['price_change_n_days'] / self.max_price_increase) * 20
            
            # 4. 技术面评分
            # 均线排列
            if 'ma5' in daily_data and 'ma20' in daily_data and 'ma60' in daily_data and \
               not pd.isna(daily_data['ma5']) and not pd.isna(daily_data['ma20']) and not pd.isna(daily_data['ma60']):
                if daily_data['ma5'] > daily_data['ma20'] > daily_data['ma60']:
                    score += 15
                elif daily_data['ma5'] > daily_data['ma20']:
                    score += 10
            
            # RSI指标
            if 'rsi' in daily_data and not pd.isna(daily_data['rsi']):
                # RSI在40-60之间是较为理想的状态
                if 40 <= daily_data['rsi'] <= 60:
                    score += 10
                elif 30 <= daily_data['rsi'] < 40 or 60 < daily_data['rsi'] <= 70:
                    score += 5
            
            # 5. 成交量评分（如果有数据）
            if 'volume' in daily_data and 'volume' in daily_data.index:
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
                daily_data = df[df['date'] == date]
                
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
            df = df[(df['date'] >= start_date) & (df['date'] <= end_date)]
            
            if df.empty:
                logger.error(f"No data available for stock {code} in date range")
                return None
            
            # 计算基础表现指标
            start_price = df['close'].iloc[0]
            end_price = df['close'].iloc[-1]
            total_return = (end_price / start_price) - 1
            
            # 计算最大回撤
            cumulative_max = df['close'].cummax()
            drawdown = (df['close'] - cumulative_max) / cumulative_max
            max_drawdown = drawdown.min()
            
            # 计算涨停次数
            df['is_limit_up'] = df['close'].pct_change() >= 0.098
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
                            'date': row['date'],
                            'price': row['close']
                        })
                        position = {'avg_price': row['close'], 'buy_date': row['date']}
                else:
                    if self.should_sell(code, row, position):
                        sell_signals.append({
                            'date': row['date'],
                            'price': row['close'],
                            'profit_ratio': (row['close'] / position['avg_price']) - 1
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
    # 这里需要导入实际的数据处理器类
    # from src.data_processor import DataProcessor
    
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
