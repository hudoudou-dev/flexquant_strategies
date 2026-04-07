#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
@Author:            hudoudou-dev
@Email:             humengnju@qq.com
@Create Time:       2025-11-20
@Last Modified:     2025-11-20
@Modified By:       hudoudou-dev
@Version:           1.0
@Description:       FlexQuant-Strategies, main entrance with command line interface integrating data fetch, processing, strategy, backtesting, and scheduling functionalities.
@Notes:             none.
@History:
                    v1.0, create.
"""

# 1. 获取数据:
#    python main.py fetch --full        # 完整数据更新
#    python main.py fetch --daily       # 每日数据更新
#    python main.py fetch --incremental # 增量数据更新
#    python main.py fetch --stocks 000001 000002 600000   # 指定股票代码数据更新
#    python main.py fetch --stocks 000001 000002 --start-date 2023-01-01 --end-date 2023-12-31  # 指定股票代码和日期范围数据更新
#    python main.py fetch --stock-file stock_list.txt     # 指定股票代码数据更新. stock_list.txt文件, 每行一个股票代码

# 2. 执行选股：
#    python main.py select --top 10

# 3. 运行回测：
#    python main.py backtest

# 4. 管理投资组合：
#    python main.py portfolio --status

# 5. 启动调度器：
#    python main.py scheduler


import os
import sys
import argparse
import yaml
import logging
from datetime import datetime, timedelta

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.data_fetch import DataFetcher
from src.data_processor import DataProcessor
from src.strategy import FlexStrategy
from src.backtester import Backtester
from src.scheduler import StrategyScheduler
from src.portfolio import PortfolioManager

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs', 'main.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('main')


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


def parse_arguments():
    """
    解析命令行参数
    
    Returns:
        argparse.Namespace: 解析后的参数
    """
    parser = argparse.ArgumentParser(description='FlexQuant-Strategies')
    
    # 子命令解析器
    subparsers = parser.add_subparsers(dest='mode', help='运行模式')

    # 数据获取模式
    fetch_parser = subparsers.add_parser('fetch', help='获取股票数据')
    fetch_parser.add_argument('--full', action='store_true', help='执行完整数据获取')
    fetch_parser.add_argument('--daily', action='store_true', help='执行每日数据更新')
    fetch_parser.add_argument('--incremental', action='store_true', help='增量获取数据')
    fetch_parser.add_argument('--stocks', nargs='+', help='指定股票代码列表')
    fetch_parser.add_argument('--start-date', type=str, help='开始日期 (YYYY-MM-DD)')
    fetch_parser.add_argument('--end-date', type=str, help='结束日期 (YYYY-MM-DD)')
    fetch_parser.add_argument('--stock-file', type=str, help='从文件中读取股票代码列表')
    
    # 策略选股模式
    select_parser = subparsers.add_parser('select', help='执行策略选股')
    select_parser.add_argument('--top', type=int, default=10, help='返回前N只股票')
    select_parser.add_argument('--output', type=str, default="top10.csv", help='输出文件路径')
    
    # 回测模式
    backtest_parser = subparsers.add_parser('backtest', help='执行回测')
    backtest_parser.add_argument('--bt-start-date', type=str, help='回测开始日期 (YYYY-MM-DD)')
    backtest_parser.add_argument('--bt-end-date', type=str, help='回测结束日期 (YYYY-MM-DD)')
    backtest_parser.add_argument('--bt-stock', type=str, help='单个股票代码 (特定股票回测)')
    
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


def run_data_fetch(args, config):
    """
    运行数据获取功能
    
    Args:
        args: 命令行参数
        config: 配置字典
    """
    data_fetcher = DataFetcher(config=config.get('data_fetch', {}))
    
    if args.full:
        from datetime import datetime, timedelta
        if start_date is None:
            # 从config中获取duration_dates，如果不存在则使用默认值
            duration_days = config.get('data_fetch', {}).get('duration_dates', 180)
            start_date = (datetime.now() - timedelta(days=duration_days)).strftime('%Y-%m-%d')
        if end_date is None:
            end_date = datetime.now().strftime('%Y-%m-%d')

        logger.info("开始执行完整数据获取...")
        data_fetcher.fetch_all_stocks_kline_datas(start_date, end_date)
    elif args.daily:
        logger.info("开始执行每日数据更新...")
        data_fetcher.fetch_all_stocks_kline_datas_daily_auto_update()
    elif args.incremental:
        logger.info("开始执行增量数据获取...")
        data_fetcher.fetch_all_stocks_kline_datas_incremental()
    elif args.stocks:
        logger.info(f"开始获取指定股票数据: {', '.join(args.stocks)}")
        # 支持指定日期范围
        start_date = args.start_date if hasattr(args, 'start_date') else None
        end_date = args.end_date if hasattr(args, 'end_date') else None
        data_fetcher.fetch_all_stocks_kline_datas_specific(args.stocks, start_date, end_date)
    elif args.stock_file:
        if os.path.exists(args.stock_file):
            try:
                with open(args.stock_file, 'r', encoding='utf-8') as f:
                    stock_codes = [line.strip() for line in f if line.strip()]
                logger.info(f"开始从文件获取股票数据，共 {len(stock_codes)} 只股票")
                # 支持指定日期范围
                start_date = args.start_date if hasattr(args, 'start_date') else None
                end_date = args.end_date if hasattr(args, 'end_date') else None
                data_fetcher.fetch_all_stocks_kline_datas_specific(stock_codes, start_date, end_date)
            except Exception as e:
                logger.error(f"读取股票代码文件失败: {str(e)}")
        else:
            logger.error(f"股票代码文件不存在: {args.stock_file}")
    else:
        logger.info("请指定数据获取类型:")
        logger.info("  --full      - 执行完整数据获取")
        logger.info("  --daily     - 执行每日数据更新")
        logger.info("  --incremental - 增量获取数据")
        logger.info("  --stocks    - 指定股票代码列表")
        logger.info("  --stock-file - 从文件中读取股票代码列表")


def run_strategy_select(args, config):
    """
    运行策略选股功能
    
    Args:
        args: 命令行参数
        config: 配置字典
    """
    # 初始化数据处理器
    data_processor = DataProcessor(config=config.get('data_processor', {}))
    
    # 处理每日数据
    logger.info("处理每日数据...")
    data_processor.process_daily_data()
    
    # 初始化策略
    strategy = FlexStrategy(data_processor, config=config.get('strategy', {}))
    
    # 获取候选股票, 使用最近90天作为时间范围
    end_date = datetime.now().strftime('%Y-%m-%d')
    duration_days = config.get('data_processor', {}).get('price_change_period', 90)
    start_date = (datetime.now() - timedelta(days=duration_days)).strftime('%Y-%m-%d')
    logger.info(f"获取候选股票 (日期范围: {start_date} 至 {end_date})...")

    candidates = strategy.get_candidate_stocks(start_date, end_date)
    
    # 评分和排序股票
    logger.info("对候选股票进行评分和排序...")
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
    
    # 设置回测参数
    max_backtest_period = config.get('backtester', {}).get('max_backtest_period', 180)
    start_date = args.bt_start_date or (datetime.now() - timedelta(days=max_backtest_period)).strftime('%Y-%m-%d')
    end_date = args.bt_end_date or datetime.now().strftime('%Y-%m-%d')
    
    # 初始化组件
    data_processor = DataProcessor(config=config.get('data_processor', {}))
    strategy = FlexStrategy(config=config.get('strategy', {}))
    
    # 创建回测器
    backtester = Backtester(
        start_date=start_date,
        end_date=end_date,
        initial_capital=config.get('backtester', {}).get('initial_capital', 1000000),
        max_stocks=config.get('backtester', {}).get('max_stocks', 5),
        strategy=strategy,
        data_processor=data_processor
    )
    
    # 运行回测
    stock_codes = [args.bt_stock] if args.bt_stock else None
    results = backtester.run_backtest(stock_codes=stock_codes)
    print ("backtest results:", results)
    
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
    main
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