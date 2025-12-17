#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
@Author:            hudoudou-dev
@Email:             humengnju@qq.com
@Create Time:       2025-11-20
@Last Modified:     2025-12-17
@Modified By:       hudoudou-dev
@Version:           1.0
@Description:       manage equity investment portfolios, including position management, trade logging, performance calculation, and report generation.
@Notes:             none.
@History:
                    v1.0, create.
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
                    handlers=[logging.FileHandler("logs/portfolio.log"),
                              logging.StreamHandler()])
logger = logging.getLogger('portfolio')


class PortfolioManager:
    """
    投资组合管理器类，用于管理股票持仓和交易记录
    """
    
    def __init__(self, initial_capital=1000000, data_processor=None):
        """
        初始化投资组合管理器
        
        参数:
            initial_capital (float): 初始资金
            data_processor: 数据处理器对象，用于获取股票数据
        """
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.data_processor = data_processor
        
        # 持仓字典，格式: {code: {'shares': 数量, 'avg_price': 平均买入价格, 'buy_date': 买入日期}}
        self.positions = {}
        
        # 交易记录列表
        self.transactions = []
        
        # 投资组合历史记录
        self.portfolio_history = pd.DataFrame()
        
        # 确保数据目录存在
        os.makedirs('data/portfolio_data', exist_ok=True)
        
        logger.info(f"Portfolio initialized with initial capital: ¥{initial_capital:,.2f}")
    
    def buy_stock(self, code, date, price, shares, stock_name=None):
        """
        买入股票
        
        参数:
            code (str): 股票代码
            date (str): 交易日期
            price (float): 买入价格
            shares (int): 买入数量
            stock_name (str, optional): 股票名称
            
        返回:
            dict: 交易信息
        """
        try:
            # 计算买入成本
            cost = shares * price
            
            # 检查资金是否足够
            if cost > self.current_capital:
                logger.warning(f"Insufficient capital to buy {shares} shares of {code} at {price:.2f}")
                return None
            
            # 更新资金
            self.current_capital -= cost
            
            # 更新持仓
            if code in self.positions:
                # 已有持仓，计算新的平均价格
                current_position = self.positions[code]
                total_shares = current_position['shares'] + shares
                total_cost = (current_position['shares'] * current_position['avg_price']) + cost
                new_avg_price = total_cost / total_shares
                
                self.positions[code] = {
                    'shares': total_shares,
                    'avg_price': new_avg_price,
                    'buy_date': min(current_position['buy_date'], date),  # 保留最早买入日期
                    'stock_name': stock_name or current_position.get('stock_name', code)
                }
            else:
                # 新持仓
                self.positions[code] = {
                    'shares': shares,
                    'avg_price': price,
                    'buy_date': date,
                    'stock_name': stock_name or code
                }
            
            # 记录交易
            transaction = {
                'date': date,
                'code': code,
                'stock_name': stock_name or code,
                'action': 'BUY',
                'price': price,
                'shares': shares,
                'amount': cost,
                'remaining_capital': self.current_capital
            }
            
            self.transactions.append(transaction)
            
            logger.info(f"BOUGHT {shares} shares of {code} at {price:.2f} on {date}, "
                      f"cost: ¥{cost:,.2f}, remaining capital: ¥{self.current_capital:,.2f}")
            
            return transaction
            
        except Exception as e:
            logger.error(f"Error buying {code}: {str(e)}")
            return None
    
    def sell_stock(self, code, date, price, shares=None, stock_name=None):
        """
        卖出股票
        
        参数:
            code (str): 股票代码
            date (str): 交易日期
            price (float): 卖出价格
            shares (int, optional): 卖出数量，None表示卖出全部
            stock_name (str, optional): 股票名称
            
        返回:
            dict: 交易信息
        """
        try:
            # 检查是否持有该股票
            if code not in self.positions:
                logger.warning(f"Cannot sell {code}: not in portfolio")
                return None
            
            position = self.positions[code]
            
            # 确定卖出数量
            if shares is None or shares > position['shares']:
                shares = position['shares']
            
            # 计算卖出金额
            proceeds = shares * price
            
            # 计算盈亏
            cost = shares * position['avg_price']
            profit = proceeds - cost
            profit_percent = (profit / cost) * 100
            
            # 更新资金
            self.current_capital += proceeds
            
            # 更新持仓
            new_shares = position['shares'] - shares
            
            if new_shares == 0:
                # 全部卖出，移除持仓
                del self.positions[code]
            else:
                # 部分卖出，保持平均价格不变
                self.positions[code] = {
                    'shares': new_shares,
                    'avg_price': position['avg_price'],
                    'buy_date': position['buy_date'],
                    'stock_name': stock_name or position.get('stock_name', code)
                }
            
            # 记录交易
            transaction = {
                'date': date,
                'code': code,
                'stock_name': stock_name or position.get('stock_name', code),
                'action': 'SELL',
                'price': price,
                'shares': shares,
                'amount': proceeds,
                'cost': cost,
                'profit': profit,
                'profit_percent': profit_percent,
                'remaining_capital': self.current_capital
            }
            
            self.transactions.append(transaction)
            
            logger.info(f"SOLD {shares} shares of {code} at {price:.2f} on {date}, "
                      f"proceeds: ¥{proceeds:,.2f}, profit: ¥{profit:,.2f} ({profit_percent:.2f}%)")
            
            return transaction
            
        except Exception as e:
            logger.error(f"Error selling {code}: {str(e)}")
            return None
    
    def get_current_positions(self):
        """
        获取当前持仓信息
        
        返回:
            dict: 当前持仓字典
        """
        return self.positions
    
    def get_positions_value(self, prices=None):
        """
        计算当前持仓市值
        
        参数:
            prices (dict, optional): 股票价格字典 {code: price}
            
        返回:
            float: 持仓总市值
        """
        total_value = 0.0
        
        for code, position in self.positions.items():
            if prices and code in prices:
                current_price = prices[code]
            else:
                # 如果没有提供价格，尝试从数据处理器获取最新价格
                if self.data_processor:
                    try:
                        latest_price = self.data_processor.get_latest_price(code)
                        # latest_price = None
                        if latest_price:
                            current_price = latest_price
                        else:
                            current_price = position['avg_price']  # 使用平均买入价作为备选
                    except:
                        current_price = position['avg_price']
                else:
                    current_price = position['avg_price']
            
            position_value = position['shares'] * current_price
            total_value += position_value
        
        return total_value
    
    def get_total_portfolio_value(self, prices=None):
        """
        计算投资组合总价值（现金 + 持仓市值）
        
        参数:
            prices (dict, optional): 股票价格字典 {code: price}
            
        返回:
            float: 投资组合总价值
        """
        return self.current_capital + self.get_positions_value(prices)
    
    def calculate_total_return(self, prices=None):
        """
        计算总收益率
        
        参数:
            prices (dict, optional): 股票价格字典 {code: price}
            
        返回:
            float: 总收益率
        """
        total_value = self.get_total_portfolio_value(prices)
        return (total_value / self.initial_capital) - 1
    
    def record_portfolio_state(self, date, prices=None):
        """
        记录投资组合状态
        
        参数:
            date (str): 日期
            prices (dict, optional): 股票价格字典 {code: price}
        """
        positions_value = self.get_positions_value(prices)
        total_value = self.current_capital + positions_value
        daily_return = (total_value / self.initial_capital) - 1
        
        # 记录状态
        state = {
            'date': date,
            'capital': self.current_capital,
            'positions_value': positions_value,
            'total_value': total_value,
            'daily_return': daily_return,
            'num_positions': len(self.positions),
            'positions': self.positions.copy()  # 保存当前持仓快照
        }
        
        # 添加到历史记录
        self.portfolio_history = pd.concat([self.portfolio_history, pd.DataFrame([state])], ignore_index=True)
        
        logger.debug(f"Portfolio state recorded for {date}: total value ¥{total_value:,.2f}, "
                   f"return {daily_return*100:.2f}%")
    
    def get_transaction_history(self):
        """
        获取交易历史记录
        
        返回:
            pd.DataFrame: 交易历史记录
        """
        return pd.DataFrame(self.transactions)
    
    def get_performance_summary(self):
        """
        获取投资组合绩效摘要
        
        返回:
            dict: 绩效摘要字典
        """
        transactions_df = self.get_transaction_history()
        
        # 计算基本指标
        total_value = self.get_total_portfolio_value()
        total_return = (total_value / self.initial_capital) - 1
        
        # 交易统计
        num_trades = len(transactions_df)
        num_buys = len(transactions_df[transactions_df['action'] == 'BUY']) if not transactions_df.empty else 0
        num_sells = len(transactions_df[transactions_df['action'] == 'SELL']) if not transactions_df.empty else 0
        
        # 盈利统计
        sell_transactions = transactions_df[transactions_df['action'] == 'SELL'] if not transactions_df.empty else pd.DataFrame()
        winning_trades = sell_transactions[sell_transactions['profit'] > 0] if not sell_transactions.empty else pd.DataFrame()
        losing_trades = sell_transactions[sell_transactions['profit'] <= 0] if not sell_transactions.empty else pd.DataFrame()
        
        win_rate = len(winning_trades) / num_sells if num_sells > 0 else 0
        total_profit = sell_transactions['profit'].sum() if 'profit' in sell_transactions.columns else 0
        avg_profit_per_trade = total_profit / num_sells if num_sells > 0 else 0
        avg_profit_win = winning_trades['profit'].mean() if not winning_trades.empty else 0
        avg_loss = losing_trades['profit'].mean() if not losing_trades.empty else 0
        
        # 持仓统计
        current_value_by_stock = {}
        current_return_by_stock = {}
        
        for code, position in self.positions.items():
            if self.data_processor:
                try:
                    latest_price = self.data_processor.get_latest_price(code)
                    if latest_price:
                        current_price = latest_price
                    else:
                        current_price = position['avg_price']
                except:
                    current_price = position['avg_price']
            else:
                current_price = position['avg_price']
            
            position_value = position['shares'] * current_price
            position_return = (current_price / position['avg_price']) - 1
            
            current_value_by_stock[code] = position_value
            current_return_by_stock[code] = position_return
        
        summary = {
            'initial_capital': self.initial_capital,
            'current_capital': self.current_capital,
            'positions_value': self.get_positions_value(),
            'total_value': total_value,
            'total_return': total_return,
            'num_trades': num_trades,
            'num_buys': num_buys,
            'num_sells': num_sells,
            'win_rate': win_rate,
            'total_profit': total_profit,
            'avg_profit_per_trade': avg_profit_per_trade,
            'avg_profit_win': avg_profit_win,
            'avg_loss': avg_loss,
            'num_current_positions': len(self.positions),
            'current_value_by_stock': current_value_by_stock,
            'current_return_by_stock': current_return_by_stock
        }
        
        return summary
    
    def generate_portfolio_report(self, output_file=None):
        """
        生成投资组合报告
        
        参数:
            output_file (str, optional): 输出文件路径
            
        返回:
            str: 报告内容
        """
        summary = self.get_performance_summary()
        
        # 构建报告
        report = []
        report.append("=" * 60)
        report.append("        投资组合绩效报告")
        report.append("=" * 60)
        report.append(f"报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        # 基本信息
        report.append("1. 基本信息")
        report.append("-" * 30)
        report.append(f"初始资金: ¥{summary['initial_capital']:,.2f}")
        report.append(f"当前现金: ¥{summary['current_capital']:,.2f}")
        report.append(f"持仓市值: ¥{summary['positions_value']:,.2f}")
        report.append(f"总市值: ¥{summary['total_value']:,.2f}")
        report.append(f"总收益率: {summary['total_return']*100:.2f}%")
        report.append("")
        
        # 交易统计
        report.append("2. 交易统计")
        report.append("-" * 30)
        report.append(f"总交易次数: {summary['num_trades']}")
        report.append(f"买入次数: {summary['num_buys']}")
        report.append(f"卖出次数: {summary['num_sells']}")
        report.append(f"胜率: {summary['win_rate']*100:.2f}%")
        report.append(f"总盈利: ¥{summary['total_profit']:,.2f}")
        report.append(f"平均每笔交易盈利: ¥{summary['avg_profit_per_trade']:,.2f}")
        report.append(f"平均盈利: ¥{summary['avg_profit_win']:,.2f}")
        report.append(f"平均亏损: ¥{summary['avg_loss']:,.2f}")
        report.append("")
        
        # 当前持仓
        report.append("3. 当前持仓")
        report.append("-" * 30)
        report.append(f"持仓数量: {summary['num_current_positions']}")
        report.append("")
        report.append(f"{'股票代码':<10}{'股票名称':<20}{'持仓数量':<10}{'平均成本':<10}{'当前价值':<12}{'收益率':<10}")
        report.append("-" * 72)
        
        for code, position in self.positions.items():
            stock_name = position.get('stock_name', code)
            shares = position['shares']
            avg_price = position['avg_price']
            
            # 获取当前价格
            if code in summary['current_value_by_stock']:
                current_value = summary['current_value_by_stock'][code]
                current_return = summary['current_return_by_stock'][code]
                current_price = current_value / shares if shares > 0 else 0
            else:
                current_price = avg_price
                current_value = shares * current_price
                current_return = 0
            
            report.append(f"{code:<10}{stock_name:<20}{shares:<10}{avg_price:<10.2f}{current_value:<12.2f}{current_return*100:<10.2f}%")
        
        report.append("=" * 60)
        
        # 生成报告文本
        report_text = "\n".join(report)
        
        # 输出到文件
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(report_text)
            logger.info(f"Portfolio report saved to {output_file}")
        
        return report_text
    
    def save_portfolio(self, file_path=None):
        """
        保存投资组合状态
        
        参数:
            file_path (str, optional): 保存路径，默认为 'data/portfolio_data/current_portfolio.json'
        """
        if file_path is None:
            file_path = 'data/portfolio_data/current_portfolio.json'
        
        portfolio_data = {
            'timestamp': datetime.now().isoformat(),
            'initial_capital': self.initial_capital,
            'current_capital': self.current_capital,
            'positions': self.positions,
            'transactions': self.transactions
        }
        
        try:
            import json
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(portfolio_data, f, ensure_ascii=False, indent=2, default=str)
            logger.info(f"Portfolio saved to {file_path}")
            return True
        except Exception as e:
            logger.error(f"Error saving portfolio: {str(e)}")
            return False
    
    def load_portfolio(self, file_path=None):
        """
        加载投资组合状态
        
        参数:
            file_path (str, optional): 加载路径，默认为 'data/portfolio_data/current_portfolio.json'
            
        返回:
            bool: 是否加载成功
        """
        if file_path is None:
            file_path = 'data/portfolio_data/current_portfolio.json'
        
        try:
            import json
            
            if not os.path.exists(file_path):
                logger.warning(f"Portfolio file not found: {file_path}")
                return False
            
            with open(file_path, 'r', encoding='utf-8') as f:
                portfolio_data = json.load(f)
            
            # 恢复投资组合状态
            self.initial_capital = portfolio_data['initial_capital']
            self.current_capital = portfolio_data['current_capital']
            self.positions = portfolio_data['positions']
            self.transactions = portfolio_data['transactions']
            
            logger.info(f"Portfolio loaded from {file_path}")
            logger.info(f"Restored capital: ¥{self.current_capital:,.2f}, positions: {len(self.positions)}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error loading portfolio: {str(e)}")
            return False
    
    def clear_portfolio(self):
        """
        清空投资组合（重置为初始状态）
        """
        self.current_capital = self.initial_capital
        self.positions = {}
        self.transactions = []
        self.portfolio_history = pd.DataFrame()
        
        logger.info("Portfolio cleared, reset to initial state")
    
    def export_portfolio_history(self, file_path=None):
        """
        导出投资组合历史到CSV文件
        
        参数:
            file_path (str, optional): 导出路径，默认为 'data/portfolio_data/portfolio_history.csv'
            
        返回:
            bool: 是否导出成功
        """
        if file_path is None:
            file_path = 'data/portfolio_data/portfolio_history.csv'
        
        try:
            # 复制历史数据以避免修改原始数据
            export_df = self.portfolio_history.copy()
            
            # 移除positions列，因为它包含复杂对象
            if 'positions' in export_df.columns:
                export_df = export_df.drop('positions', axis=1)
            
            export_df.to_csv(file_path, index=False, encoding='utf-8')
            logger.info(f"Portfolio history exported to {file_path}")
            return True
        except Exception as e:
            logger.error(f"Error exporting portfolio history: {str(e)}")
            return False

    def export_transactions(self, file_path=None):
        """
        导出交易记录到CSV文件
        
        参数:
            file_path (str, optional): 导出路径，默认为 'data/portfolio_data/transactions.csv'
            
        返回:
            bool: 是否导出成功
        """
        if file_path is None:
            file_path = 'data/portfolio_data/transactions.csv'
        
        try:
            transactions_df = self.get_transaction_history()
            transactions_df.to_csv(file_path, index=False, encoding='utf-8')
            logger.info(f"Transactions exported to {file_path}")
            return True
        except Exception as e:
            logger.error(f"Error exporting transactions: {str(e)}")
            return False


def run_portfolio_example():
    """
    投资组合示例函数，演示如何使用投资组合管理器
    """
    # 这里需要导入实际的数据处理器类
    # from src.data_processor import DataProcessor
    
    print("Portfolio Manager example configuration:")
    print("1. Portfolio management functions:")
    print("   - Buy and sell stocks")
    print("   - Track positions and transactions")
    print("   - Calculate performance metrics")
    print("   - Generate reports")
    print("   - Save and load portfolio state")
    
    print("\nNote: To run a real portfolio manager, you need to:")
    print("1. Import your data processor")
    print("2. Initialize it with proper parameters")
    print("3. Create a PortfolioManager instance")
    print("4. Use the portfolio methods as needed")
    
    # 示例代码（未运行）:
    """
    # 初始化数据处理器
    data_processor = DataProcessor()
    
    # 创建投资组合管理器
    portfolio = PortfolioManager(initial_capital=1000000, data_processor=data_processor)
    
    # 买入股票
    portfolio.buy_stock('000001', '2024-01-01', 10.5, 1000, '平安银行')
    portfolio.buy_stock('600000', '2024-01-02', 9.8, 2000, '浦发银行')
    
    # 记录投资组合状态
    portfolio.record_portfolio_state('2024-01-02')
    
    # 卖出股票
    portfolio.sell_stock('000001', '2024-01-15', 11.2, 500)
    
    # 生成报告
    report = portfolio.generate_portfolio_report('data/portfolio_data/portfolio_report.txt')
    print(report)
    
    # 保存投资组合
    portfolio.save_portfolio()
    """


if __name__ == "__main__":
    # 运行示例
    run_portfolio_example()
