#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# 这个main.py文件具有以下特点：

# 简洁明了：避免了过于复杂的实现，专注于核心功能集成
# 模块化设计：清晰地调用我们之前实现的各个模块
# 命令行接口：使用子命令模式提供多种功能入口
# 完整功能覆盖：包含数据获取、策略选股、回测、投资组合管理和调度器启动
# 友好提示：提供详细的使用说明和示例命令
# 使用方法非常简单，您可以通过不同的子命令来执行不同的功能：

# 获取数据：python main.py fetch --daily 或 python main.py fetch --full
# 执行选股：python main.py select --top 10
# 运行回测：python main.py backtest
# 管理投资组合：python main.py portfolio --status
# 启动调度器：python main.py scheduler

# 现在您可以使用以下命令来测试新功能：

# 自动判断最近抓取日期并追加数据：


# bash
# python main.py fetch --incremental
# 这个命令会自动检查现有数据中最新的日期，然后只获取从该日期之后到今天的数据。

# 获取特定股票的数据：


# bash
# python main.py fetch --stocks 000001 000002 600000
# 这个命令会只获取指定的几只股票的数据。

# 从文件中读取股票代码并获取数据：


# bash
# python main.py fetch --stock-file stock_list.txt
# 您需要创建一个stock_list.txt文件，每行一个股票代码。

# 指定日期范围获取特定股票数据：


# bash
# python main.py fetch --stocks 000001 000002 --start-date 2023-01-01 --end-date 2023-12-31
# 这些新功能完全满足了您的需求：可以自动判断最近抓取日期进行追加更新，也可以方便地进行小规模测试，无论是直接指定股票代码还是从文件读取。同时，我保留了原有的完整数据获取和每日更新功能。

"""
FlexQuant Strategies - 主入口

功能描述: 系统主入口，提供命令行接口，集成数据获取、处理、策略、回测和调度功能
作者: FlexQuant Team
创建时间: 2024-01-15
修改时间: 2024-01-15
修改备注: 初始版本，实现基础功能集成
"""

import os
import sys
import argparse
import yaml
import logging

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 导入自定义模块
from src.data_fetch import DataFetcher
from src.data_processor import DataProcessor
from src.strategy import FlexStrategy
from src.backtester import Backtester
from src.portfolio import PortfolioManager
from src.scheduler import StrategyScheduler

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs', 'main.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('main')


def load_config(config_path=None):
    """
    加载配置文件
    
    Args:
        config_path: 配置文件路径
        
    Returns:
        dict: 配置字典
    """
    if config_path is None:
        config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config', 'config.yaml')
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        logger.info(f"成功加载配置文件: {config_path}")
        return config
    except Exception as e:
        logger.error(f"加载配置文件失败: {str(e)}")
        return {}


def parse_arguments():
    """
    解析命令行参数
    
    Returns:
        argparse.Namespace: 解析后的参数
    """
    parser = argparse.ArgumentParser(description='FlexQuant股票策略系统')
    
    # 子命令解析器
    subparsers = parser.add_subparsers(dest='mode', help='运行模式')
    
    # 数据获取模式
    fetch_parser = subparsers.add_parser('fetch', help='获取股票数据')
    fetch_parser.add_argument('--full', action='store_true', help='执行完整数据获取')
    fetch_parser.add_argument('--daily', action='store_true', help='执行每日数据更新')
    
    # 策略选股模式
    select_parser = subparsers.add_parser('select', help='执行策略选股')
    select_parser.add_argument('--top', type=int, default=10, help='返回前N只股票')
    select_parser.add_argument('--output', type=str, help='输出文件路径')
    
    # 回测模式
    backtest_parser = subparsers.add_parser('backtest', help='执行回测')
    backtest_parser.add_argument('--start-date', type=str, help='回测开始日期 (YYYY-MM-DD)')
    backtest_parser.add_argument('--end-date', type=str, help='回测结束日期 (YYYY-MM-DD)')
    backtest_parser.add_argument('--stock', type=str, help='单个股票代码 (特定股票回测)')
    
    # 投资组合管理模式
    portfolio_parser = subparsers.add_parser('portfolio', help='管理投资组合')
    portfolio_parser.add_argument('--status', action='store_true', help='查看投资组合状态')
    portfolio_parser.add_argument('--report', action='store_true', help='生成投资组合报告')
    
    # 调度器模式
    scheduler_parser = subparsers.add_parser('scheduler', help='启动调度器')
    scheduler_parser.add_argument('--run-now', action='store_true', help='立即执行一次任务')
    
    # 全局参数
    parser.add_argument('--config', type=str, help='配置文件路径')
    parser.add_argument('--verbose', action='store_true', help='显示详细日志')
    
    return parser.parse_args()


def ensure_directories():
    """
    确保必要的目录存在
    """
    directories = [
        os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'raw_data'),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'processed_data'),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'portfolio_data'),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)


def run_data_fetch(args, config):
    """
    运行数据获取功能
    
    Args:
        args: 命令行参数
        config: 配置字典
    """
    data_fetcher = DataFetcher(config=config.get('data_fetch', {}))
    
    if args.full:
        logger.info("开始执行完整数据获取...")
        data_fetcher.fetch_all_data()
    elif args.daily:
        logger.info("开始执行每日数据更新...")
        data_fetcher.update_daily_data()
    else:
        logger.info("请指定数据获取类型: --full 或 --daily")


def run_strategy_select(args, config):
    """
    运行策略选股功能
    
    Args:
        args: 命令行参数
        config: 配置字典
    """
    # 首先确保数据已处理
    data_processor = DataProcessor(config=config.get('data_processor', {}))
    data_processor.process_daily_data()
    
    # 执行选股策略
    strategy = FlexStrategy(config=config.get('strategy', {}))
    candidates = strategy.get_candidate_stocks()
    top_stocks = strategy.score_and_rank_stocks(candidates)[:args.top]
    
    # 输出结果
    logger.info(f"\n选出的Top {len(top_stocks)} 股票:")
    for i, stock in enumerate(top_stocks, 1):
        logger.info(f"{i:2d}. {stock['code']} {stock['name']} - 评分: {stock['score']:.2f}")
    
    # 保存到文件
    if args.output:
        import pandas as pd
        df = pd.DataFrame(top_stocks)
        df.to_csv(args.output, index=False, encoding='utf-8-sig')
        logger.info(f"\n结果已保存到: {args.output}")


def run_backtest(args, config):
    """
    运行回测功能
    
    Args:
        args: 命令行参数
        config: 配置字典
    """
    # 导入必要的模块
    from datetime import datetime, timedelta
    
    # 设置回测参数
    start_date = args.start_date or (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
    end_date = args.end_date or datetime.now().strftime('%Y-%m-%d')
    
    # 初始化组件
    data_processor = DataProcessor(config=config.get('data_processor', {}))
    strategy = FlexStrategy(config=config.get('strategy', {}))
    
    # 创建回测器
    backtester = Backtester(
        start_date=start_date,
        end_date=end_date,
        initial_capital=config.get('backtester', {}).get('initial_capital', 1000000),
        max_stocks=config.get('backtester', {}).get('max_positions', 5),
        strategy=strategy,
        data_processor=data_processor
    )
    
    # 运行回测
    stock_codes = [args.stock] if args.stock else None
    results = backtester.run_backtest(stock_codes=stock_codes)
    
    # 绘制结果
    backtester.plot_results()


def run_portfolio(args, config):
    """
    运行投资组合管理功能
    
    Args:
        args: 命令行参数
        config: 配置字典
    """
    portfolio_manager = PortfolioManager(config=config.get('portfolio', {}))
    
    if args.status:
        logger.info("投资组合当前状态:")
        positions = portfolio_manager.get_current_positions()
        total_value = portfolio_manager.get_total_portfolio_value()
        
        logger.info(f"总市值: {total_value:.2f} 元")
        logger.info(f"持仓数量: {len(positions)} 只")
        
        if positions:
            logger.info("持仓详情:")
            for code, pos in positions.items():
                logger.info(f"{code}: {pos['shares']} 股, 均价: {pos['avg_price']:.2f} 元")
    
    elif args.report:
        logger.info("生成投资组合报告...")
        report = portfolio_manager.generate_portfolio_report()
        logger.info(f"报告已保存到: {report}")
    
    else:
        logger.info("请指定投资组合操作: --status 或 --report")


def run_scheduler(args, config):
    """
    运行调度器功能
    
    Args:
        args: 命令行参数
        config: 配置字典
    """
    scheduler = StrategyScheduler(config=config)
    
    if args.run_now:
        scheduler.manual_run()
    else:
        scheduler.start_scheduler()


def main():
    """
    主函数
    """
    # 确保必要的目录存在
    ensure_directories()
    
    # 解析命令行参数
    args = parse_arguments()
    
    # 加载配置
    config = load_config(args.config)
    
    # 根据模式执行相应功能
    if args.mode == 'fetch':
        run_data_fetch(args, config)
    elif args.mode == 'select':
        run_strategy_select(args, config)
    elif args.mode == 'backtest':
        run_backtest(args, config)
    elif args.mode == 'portfolio':
        run_portfolio(args, config)
    elif args.mode == 'scheduler':
        run_scheduler(args, config)
    else:
        # 如果没有指定模式，显示帮助信息
        print("请指定运行模式，使用 -h 或 --help 查看帮助")
        print("\n可用模式:")
        print("  fetch     - 获取股票数据")
        print("  select    - 执行策略选股")
        print("  backtest  - 执行回测")
        print("  portfolio - 管理投资组合")
        print("  scheduler - 启动调度器")
        print("\n示例:")
        print("  python main.py fetch --daily     # 更新每日数据")
        print("  python main.py select --top 10   # 选出Top 10股票")
        print("  python main.py backtest          # 执行回测")


if __name__ == "__main__":
    main()