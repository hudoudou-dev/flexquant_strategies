#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
@Author:            hudoudou-dev
@Email:             humengnju@qq.com
@Create Time:       2025-11-20
@Last Modified:     2025-12-17
@Modified By:       hudoudou-dev
@Version:           1.0
@Description:       provide stock strategy backtesting functionality, supporting full-market backtesting and specific stock backtesting, 
                    with calculations of return rates and trading performance metrics.
@Notes:             none.
@History:
                    v1.0, create.
"""


import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import logging
import sys

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 设置日志
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    handlers=[logging.FileHandler("logs/backtest.log"),
                              logging.StreamHandler()])
logger = logging.getLogger('backtester')


class Backtester:
    """
    回测器类，用于执行股票交易策略的回测
    """
    
    def __init__(self, 
                 start_date, 
                 end_date, 
                 initial_capital=1000000, 
                 max_stocks=5,
                 strategy=None, 
                 data_processor=None,
                 warm_up_period=0,
                 cold_start_strategy='empty',
                 min_buy_score=0,
                 score_thresholds=None,
                 position_management=None):
        """
        初始化回测器
        
        参数:
            start_date (str): 回测开始日期，格式 'YYYY-MM-DD'
            end_date (str): 回测结束日期，格式 'YYYY-MM-DD'
            initial_capital (float): 初始资金，默认100万
            max_stocks (int): 最大持仓股票数量
            strategy: 策略对象，包含生成买卖信号的方法
            data_processor: 数据处理器对象，用于获取数据
            warm_up_period (int): 预热期天数，预热期内不进行交易
            cold_start_strategy (str): 冷启动策略，'empty'或'random'
            min_buy_score (float): 最低买入评分阈值
            score_thresholds (dict): 评分阈值与仓位比例映射
            position_management (dict): 仓位管理配置
        """
        self.start_date = start_date
        self.end_date = end_date
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.max_stocks = max_stocks
        self.strategy = strategy
        self.data_processor = data_processor
        self.warm_up_period = warm_up_period
        self.cold_start_strategy = cold_start_strategy
        
        # 仓位管理参数
        self.min_buy_score = min_buy_score
        self.score_thresholds = score_thresholds or {'excellent': 80, 'good': 70, 'fair': 60}
        self.position_management = position_management or {
            'enable_dynamic_position': False,
            'max_position_ratio': 0.95,
            'min_cash_ratio': 0.05
        }
        
        # 回测结果存储
        self.portfolio_history = pd.DataFrame()
        self.transactions = []
        self.positions = {}
        self.trade_dates = []
        self.warm_up_end_date = None  # 预热期结束日期
        
        # 确保结果目录存在
        os.makedirs('data/portfolio_data', exist_ok=True)
    
    def _get_position_ratio_by_score(self, score):
        """
        根据股票评分计算建议的仓位比例
        
        参数:
            score (float): 股票评分
            
        返回:
            float: 建议的仓位比例（0-1之间）
        """
        if score >= self.score_thresholds.get('excellent', 80):
            return 1.0  # 全仓
        elif score >= self.score_thresholds.get('good', 70):
            return 0.5  # 半仓
        elif score >= self.score_thresholds.get('fair', 60):
            return 0.3  # 轻仓
        else:
            return 0.0  # 不买入
    
    def _calculate_max_available_capital(self):
        """
        计算当前可用于买入的最大资金
        
        返回:
            float: 可用资金上限
        """
        if not self.position_management.get('enable_dynamic_position', False):
            return self.current_capital
        
        # 计算当前持仓价值
        positions_value = sum(
            pos['shares'] * pos['avg_price'] 
            for pos in self.positions.values()
        )
        
        total_value = self.current_capital + positions_value
        max_position_value = total_value * self.position_management.get('max_position_ratio', 0.95)
        min_cash = total_value * self.position_management.get('min_cash_ratio', 0.05)
        
        # 可用资金 = 最大持仓价值 - 当前持仓价值，但不能超过当前现金 - 最小现金
        available = min(
            max_position_value - positions_value,
            self.current_capital - min_cash
        )
        
        return max(0, available)
    
    def load_data(self, stock_codes=None):
        """
        加载回测所需的数据
        
        参数:
            stock_codes (list): 股票代码列表，None表示全市场回测
            
        返回:
            dict: 股票数据字典
        """
        logger.info(f"Loading data from {self.start_date} to {self.end_date}")
        
        if stock_codes:
            # 特定股票回测
            stock_data = {}
            for code in stock_codes:
                try:
                    df = self.data_processor.load_stock_data(stock_code=code, start_date=self.start_date, end_date=self.end_date)
                    # 确保日期列统一
                    if '日期' in df.columns and 'date' not in df.columns:
                        df['date'] = df['日期']
                    
                    # 过滤日期范围
                    df = df[(df['date'] >= self.start_date) & (df['date'] <= self.end_date)]
                    if not df.empty:
                        # 核心修复：加载数据后必须计算策略所需的特征指标
                        if self.strategy:
                            df = self.strategy._calculate_features(df)
                        stock_data[code] = df
                        logger.info(f"Loaded and pre-calculated features for {code}, shape: {df.shape}")
                except Exception as e:
                    logger.error(f"Error loading data for {code}: {str(e)}")
            return stock_data
        else:
            # 全市场回测，由策略提供候选股票
            if self.strategy:
                return self.strategy.get_candidate_stocks(self.start_date, self.end_date)
            else:
                logger.error("No strategy provided for market-wide backtest")
                return {}
    
    def run_backtest(self, stock_codes=None):
        """
        运行回测
        
        参数:
            stock_codes (list): 股票代码列表，None表示全市场回测
            
        返回:
            dict: 回测结果统计
        """
        logger.info(f"Starting backtest from {self.start_date} to {self.end_date}")
        logger.info(f"Initial capital: {self.initial_capital}, Max stocks: {self.max_stocks}")
        if self.warm_up_period > 0:
            logger.info(f"Warm-up period: {self.warm_up_period} trading days")
            logger.info(f"Cold start strategy: {self.cold_start_strategy}")
        
        # 重置回测状态
        self.current_capital = self.initial_capital
        self.positions = {}
        self.transactions = []
        
        # 加载数据
        stock_data = self.load_data(stock_codes)
        if not stock_data:
            logger.error("No data available for backtest")
            return None
        
        # 获取所有唯一日期并排序
        all_dates = set()
        for code, data in stock_data.items():
            all_dates.update(data['date'].tolist())
        
        # 统一转换为 Timestamp 进行比较，确保与 self.start_date/end_date (str) 兼容
        start_ts = pd.to_datetime(self.start_date)
        end_ts = pd.to_datetime(self.end_date)
        sorted_dates = sorted([pd.to_datetime(d) for d in all_dates])
        sorted_dates = [d for d in sorted_dates if d >= start_ts and d <= end_ts]
        
        self.trade_dates = sorted_dates
        
        # 计算预热期结束日期
        if self.warm_up_period > 0 and len(sorted_dates) > self.warm_up_period:
            self.warm_up_end_date = sorted_dates[self.warm_up_period - 1]
            logger.info(f"Warm-up period ends on: {self.warm_up_end_date}")
            logger.info(f"Actual trading starts from: {sorted_dates[self.warm_up_period]}")
        else:
            self.warm_up_end_date = None
            if self.warm_up_period > 0:
                logger.warning(f"Warm-up period ({self.warm_up_period}) exceeds available trading days ({len(sorted_dates)}), no warm-up applied")
        
        # 逐天执行回测
        for idx, date in enumerate(sorted_dates):
            # 检查是否在预热期内
            is_warm_up = self.warm_up_period > 0 and idx < self.warm_up_period
            
            if is_warm_up:
                # 预热期内只记录状态，不进行交易
                logger.debug(f"Warm-up day {idx + 1}/{self.warm_up_period}: {date}, no trading")
                self._record_portfolio_state(date)
            else:
                # 正式交易期
                self._execute_daily_trading(date, stock_data)
                self._record_portfolio_state(date)
        
        # 生成回测报告
        results = self._calculate_performance_metrics()
        self._save_results()
        
        logger.info(f"Backtest completed. Final capital: {self.current_capital:.2f}")
        return results
    
    def _execute_daily_trading(self, date, stock_data):
        """
        执行单日交易
        
        参数:
            date (str): 交易日期
            stock_data (dict): 股票数据字典
        """
        # 获取当日有数据的股票
        daily_stocks = {code: data for code, data in stock_data.items() 
                       if date in data['date'].values}
        
        # 先处理卖出信号
        self._process_sell_signals(date, daily_stocks)
        
        # 再处理买入信号
        self._process_buy_signals(date, daily_stocks)
    
    def _process_sell_signals(self, date, daily_stocks):
        """
        处理卖出信号
        
        参数:
            date (str): 交易日期
            daily_stocks (dict): 当日有数据的股票字典
        """
        stocks_to_sell = []
        
        # 检查当前持仓股票是否需要卖出
        for code, position in self.positions.items():
            if code in daily_stocks:
                # 获取该股票当日数据
                stock_data = daily_stocks[code]
                daily_data = stock_data[stock_data['date'] == date].iloc[0]
                
                # 使用策略生成卖出信号
                if self.strategy and self.strategy.should_sell(code, daily_data, position):
                    stocks_to_sell.append(code)
        
        # 执行卖出操作
        for code in stocks_to_sell:
            self._sell_stock(code, date, daily_stocks[code])
    
    def _process_buy_signals(self, date, daily_stocks):
        """
        处理买入信号
        
        参数:
            date (str): 交易日期
            daily_stocks (dict): 当日有数据的股票字典
        """
        # 如果已达到最大持仓数量，不进行买入
        if len(self.positions) >= self.max_stocks:
            logger.debug(f"On {date}: Max stocks ({self.max_stocks}) reached, skipping buy signals.")
            return
        
        # 获取候选买入股票
        potential_buys = []
        for code, stock_data in daily_stocks.items():
            # 跳过已持仓的股票
            if code in self.positions:
                logger.debug(f"On {date}: Stock {code} already in position, skipping buy signal check.")
                continue
                
            daily_data = stock_data[stock_data['date'] == date].iloc[0]
            
            # 使用策略生成买入信号
            if self.strategy and self.strategy.should_buy(code, daily_data):
                # 计算股票评分
                score = self.strategy.score_stock(code, daily_data)
                
                # 评分阈值过滤
                if score < self.min_buy_score:
                    logger.debug(f"On {date}: Stock {code} score {score:.2f} < min_buy_score {self.min_buy_score}, skipping.")
                    continue
                
                # 计算建议仓位比例
                position_ratio = self._get_position_ratio_by_score(score)
                if position_ratio <= 0:
                    logger.debug(f"On {date}: Stock {code} score {score:.2f} too low for any position, skipping.")
                    continue
                
                potential_buys.append((code, daily_data, score, position_ratio))
            else:
                logger.debug(f"On {date}: Strategy did not generate buy signal for {code}.")
        
        if not potential_buys:
            logger.debug(f"On {date}: No potential buys after strategy check.")
            return

        # 根据评分排序（评分高的优先）
        potential_buys.sort(key=lambda x: x[2], reverse=True)
        logger.debug(f"On {date}: Potential buys after scoring: {[(pb[0], pb[2]) for pb in potential_buys]}")
        
        # 计算可用于购买的最大资金
        max_available_capital = self._calculate_max_available_capital()
        logger.debug(f"On {date}: Max available capital: {max_available_capital:.2f}")
        
        # 执行买入操作
        for code, daily_data, score, position_ratio in potential_buys:
            # 检查是否还有持仓空位
            if len(self.positions) >= self.max_stocks:
                logger.debug(f"On {date}: Max stocks ({self.max_stocks}) reached during buy loop, breaking.")
                break
            
            # 计算该股票的可用资金（考虑仓位比例）
            remaining_slots = self.max_stocks - len(self.positions)
            base_capital_per_stock = max_available_capital / remaining_slots
            adjusted_capital = base_capital_per_stock * position_ratio
            
            # 检查是否有足够资金
            if self.current_capital < adjusted_capital:
                logger.debug(f"On {date}: Insufficient capital ({self.current_capital:.2f}) for {code} (need {adjusted_capital:.2f}), skipping.")
                continue
            
            self._buy_stock(code, date, daily_data, adjusted_capital, score, position_ratio)
    
    def _buy_stock(self, code, date, daily_data, available_capital, score=0, position_ratio=1.0):
        """
        买入股票
        
        参数:
            code (str): 股票代码
            date (str): 交易日期
            daily_data (pd.Series): 当日股票数据
            available_capital (float): 可用于购买的资金
            score (float): 股票评分
            position_ratio (float): 仓位比例
        """
        try:
            # 使用当日收盘价买入
            price = daily_data['收盘价']
            # 计算可以买入的股数（向下取整，不考虑交易费用）
            shares = int(available_capital / price)
            
            if shares > 0:
                cost = shares * price
                
                # 更新持仓
                self.positions[code] = {
                    'shares': shares,
                    'avg_price': price,
                    'buy_date': date,
                    'score': score,
                    'position_ratio': position_ratio
                }
                
                # 更新资金
                self.current_capital -= cost
                
                # 记录交易
                self.transactions.append({
                    'date': date,
                    'code': code,
                    'action': 'BUY',
                    'price': price,
                    'shares': shares,
                    'amount': cost,
                    'score': score,
                    'position_ratio': position_ratio,
                    'remaining_capital': self.current_capital
                })
                
                logger.info(f"BUY {code} on {date}: {shares} shares at {price:.2f}, cost: {cost:.2f}, score: {score:.2f}, position_ratio: {position_ratio:.0%}")
        except Exception as e:
            logger.error(f"Error buying {code} on {date}: {str(e)}")
    
    def _sell_stock(self, code, date, stock_data):
        """
        卖出股票
        
        参数:
            code (str): 股票代码
            date (str): 交易日期
            stock_data (pd.DataFrame): 股票数据
        """
        try:
            # 获取持仓信息
            position = self.positions[code]
            shares = position['shares']    # 持仓股票数量
            
            # 获取当日收盘价
            daily_data = stock_data[stock_data['date'] == date].iloc[0]
            price = daily_data['收盘价']
            
            # 计算卖出金额
            proceeds = shares * price
            
            # 更新资金
            self.current_capital += proceeds
            
            # 计算盈亏
            buy_cost = shares * position['avg_price']
            profit = proceeds - buy_cost
            profit_percent = (profit / buy_cost) * 100
            
            # 记录交易
            self.transactions.append({
                'date': date,
                'code': code,
                'action': 'SELL',
                'price': price,
                'shares': shares,
                'amount': proceeds,
                'profit': profit,
                'profit_percent': profit_percent,
                'remaining_capital': self.current_capital
            })
            
            # 删除持仓
            del self.positions[code]
            
            logger.info(f"SELL {code} on {date}: {shares} shares at {price:.2f}, proceeds: {proceeds:.2f}, "
                      f"profit: {profit:.2f} ({profit_percent:.2f}%)")
        except Exception as e:
            logger.error(f"Error selling {code} on {date}: {str(e)}")
    
    def _record_portfolio_state(self, date):
        """
        记录每日投资组合状态
        
        参数:
            date (str): 日期
        """
        # 计算当前持仓价值
        positions_value = 0
        for code, position in self.positions.items():
            # 尝试获取当日收盘价
            try:
                positions_value += position['shares'] * position['avg_price']  # 简化处理
            except:
                positions_value += position['shares'] * position['avg_price']
        
        total_value = self.current_capital + positions_value
        daily_return = (total_value / self.initial_capital) - 1
        
        # 记录状态
        state = {
            'date': date,
            'capital': self.current_capital,
            'positions_value': positions_value,
            'total_value': total_value,
            'daily_return': daily_return,
            'num_positions': len(self.positions)
        }
        
        # 添加到历史记录
        self.portfolio_history = pd.concat([self.portfolio_history, pd.DataFrame([state])], ignore_index=True)
    
    def _calculate_performance_metrics(self):
        """
        计算回测指标
        
        返回:
            dict: 指标字典
        """
        exchange_days_annual = 252
        if self.portfolio_history.empty:
            return {}
        
        # 基本收益指标
        final_value = self.portfolio_history['total_value'].iloc[-1]
        total_return = (final_value / self.initial_capital) - 1
        annual_return = ((1 + total_return) ** (exchange_days_annual / len(self.trade_dates))) - 1
        
        # 风险指标
        daily_returns = self.portfolio_history['total_value'].pct_change().dropna()
        sharpe_ratio = np.sqrt(exchange_days_annual) * daily_returns.mean() / daily_returns.std() if daily_returns.std() > 0 else 0
        max_drawdown = (self.portfolio_history['total_value'] / self.portfolio_history['total_value'].cummax() - 1).min()
        
        # 交易统计
        if not self.transactions:
            num_trades = 0
            num_buys = 0
            num_sells = 0
            win_rate = 0
            avg_profit = 0
            avg_loss = 0
        else:
            transactions_df = pd.DataFrame(self.transactions)
            num_trades = len(transactions_df)
            num_buys = len(transactions_df[transactions_df['action'] == 'BUY'])
            num_sells = len(transactions_df[transactions_df['action'] == 'SELL'])
            
            # 计算胜率
            winning_trades = transactions_df[(transactions_df['action'] == 'SELL') & (transactions_df.get('profit', 0) > 0)]
            win_rate = len(winning_trades) / num_sells if num_sells > 0 else 0
            
            # 平均收益/亏损
            avg_profit = winning_trades['profit'].mean() if not winning_trades.empty else 0
            losing_trades = transactions_df[(transactions_df['action'] == 'SELL') & (transactions_df.get('profit', 0) <= 0)]
            avg_loss = losing_trades['profit'].mean() if not losing_trades.empty else 0
        
        metrics = {
            'initial_capital': self.initial_capital,
            'final_capital': final_value,
            'total_return': total_return,
            'annual_return': annual_return,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'num_trades': num_trades,
            'num_buys': num_buys,
            'num_sells': num_sells,
            'win_rate': win_rate,
            'avg_profit': avg_profit,
            'avg_loss': avg_loss,
            'backtest_period': f"{self.start_date} to {self.end_date}",
            'warm_up_period': self.warm_up_period,
            'warm_up_end_date': str(self.warm_up_end_date) if self.warm_up_end_date else None,
            'actual_trading_days': len(self.trade_dates) - self.warm_up_period if self.warm_up_period > 0 else len(self.trade_dates)
        }
        
        # 打印关键指标
        self._print_performance_summary(metrics)
        
        return metrics
    
    def _print_performance_summary(self, metrics):
        """
        打印回测结果摘要
        
        参数:
            metrics (dict): 回测指标字典
        """
        logger.info("\n" + "="*50)
        logger.info("Backtest Performance Summary")
        logger.info("="*50)
        logger.info(f"Period: {metrics['backtest_period']}")
        
        # 显示预热期信息
        if metrics['warm_up_period'] > 0:
            logger.info(f"Warm-up Period: {metrics['warm_up_period']} trading days")
            logger.info(f"Warm-up Ends: {metrics['warm_up_end_date']}")
            logger.info(f"Actual Trading Days: {metrics['actual_trading_days']}")
        
        logger.info("-"*50)
        logger.info(f"Initial Capital: ¥{metrics['initial_capital']:,.2f}")
        logger.info(f"Final Capital: ¥{metrics['final_capital']:,.2f}")
        logger.info(f"Total Return: {metrics['total_return']*100:.2f}%")
        logger.info(f"Annual Return: {metrics['annual_return']*100:.2f}%")
        logger.info(f"Sharpe Ratio: {metrics['sharpe_ratio']:.2f}")
        logger.info(f"Maximum Drawdown: {metrics['max_drawdown']*100:.2f}%")
        logger.info("-"*50)
        logger.info(f"Number of Trades: {metrics['num_trades']}")
        logger.info(f"Win Rate: {metrics['win_rate']*100:.2f}%")
        logger.info(f"Average Profit per Winning Trade: ¥{metrics['avg_profit']:.2f}")
        logger.info(f"Average Loss per Losing Trade: ¥{metrics['avg_loss']:.2f}")
        logger.info("="*50 + "\n")
    
    def _save_results(self):
        """
        保存回测结果到文件
        """
        # 保存交易记录
        if self.transactions:
            transactions_df = pd.DataFrame(self.transactions)
            transactions_df.to_csv('data/portfolio_data/transactions.csv', index=False)
            logger.info(f"Saved transactions to data/portfolio_data/transactions.csv")
        
        # 保存投资组合历史
        if not self.portfolio_history.empty:
            self.portfolio_history.to_csv('data/portfolio_data/portfolio_history.csv', index=False)
            logger.info(f"Saved portfolio history to data/portfolio_data/portfolio_history.csv")
    
    def plot_results(self):
        """
        绘制回测结果图表
        """
        if self.portfolio_history.empty:
            logger.warning("No portfolio history to plot")
            return
        
        plt.figure(figsize=(14, 10))
        
        # 绘制累计收益率
        plt.subplot(2, 1, 1)
        plt.plot(self.portfolio_history['date'], self.portfolio_history['total_value'] / self.initial_capital - 1)
        plt.title('Cumulative Return')
        plt.ylabel('Return')
        plt.grid(True)
        
        # 绘制最大回撤
        plt.subplot(2, 1, 2)
        cumulative_max = self.portfolio_history['total_value'].cummax()
        drawdown = (self.portfolio_history['total_value'] - cumulative_max) / cumulative_max
        plt.plot(self.portfolio_history['date'], drawdown)
        plt.title('Maximum Drawdown')
        plt.ylabel('Drawdown')
        plt.grid(True)
        
        plt.tight_layout()
        plt.savefig('data/portfolio_data/backtest_results.png')
        logger.info("Saved backtest plot to data/portfolio_data/backtest_results.png")
        
        # 尝试显示图表
        try:
            plt.show()
        except:
            logger.warning("Could not display plot, saved to file instead")


def run_backtest_example():
    """
    回测示例函数，演示如何使用回测器
    """
    # from src.strategy import FlexStrategy
    # from src.data_processor import DataProcessor
    
    # 示例回测配置
    backtest_config = {
        'start_date': '2024-10-31',
        'end_date': '2025-10-31',
        'initial_capital': 1000000,
        'max_stocks': 5
    }
    
    print("Backtester example configuration:")
    for key, value in backtest_config.items():
        print(f"  {key}: {value}")
    
    print("\nNote: To run a real backtest, you need to:")
    print("1. Import your strategy and data processor")
    print("2. Initialize them with proper parameters")
    print("3. Create a Backtester instance with these components")
    print("4. Call run_backtest() with or without specific stock codes")
    
    # 示例代码（未运行）:
    """
    # 初始化策略和数据处理器
    data_processor = DataProcessor()
    strategy = FlexStrategy(data_processor)
    
    # 创建回测器
    backtester = Backtester(
        start_date='2024-10-31',
        end_date='2025-10-31',
        initial_capital=1000000,
        max_stocks=5,
        strategy=strategy,
        data_processor=data_processor
    )
    
    # 全市场回测
    results = backtester.run_backtest()
    
    # 或者特定股票回测
    # results = backtester.run_backtest(stock_codes=['000001', '002415'])
    
    # 绘制结果
    backtester.plot_results()
    """


if __name__ == "__main__":
    # 运行示例
    run_backtest_example()
