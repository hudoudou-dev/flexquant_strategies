#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
@Author:            hudoudou-dev
@Email:             humengnju@qq.com
@Create Time:       2025-11-20
@Last Modified:     2025-12-17
@Modified By:       hudoudou-dev
@Version:           1.0
@Description:       backtesting intergface script, provide stock strategy backtesting functionality, supporting full-market backtesting and specific stock backtesting, 
                    with calculations of return rates and trading performance metrics.
@Notes:             none.
@History:
                    v1.0, create.
"""


import os
import sys
import argparse
import yaml
import logging
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 导入自定义模块
from src.data_processor import DataProcessor
from src.strategy import FlexStrategy
from src.backtester import Backtester

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs', 'backtest_main.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('backtest_main')


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
        # 返回默认配置
        return {
            'backtester': {
                'initial_capital': 1000000,
                'max_positions': 5
            },
            'strategy': {
                'stock_selection': {
                    'max_price': 20.0,
                    'max_market_cap': 500.0,
                    'min_limit_up_count': 2,
                    'max_limit_up_count': 3,
                    'limit_up_days': 90
                }
            }
        }


def get_stock_codes(args):
    """
    获取股票代码列表
    
    Args:
        args: 命令行参数
        
    Returns:
        list: 股票代码列表
    """
    stock_codes = []
    
    # 从命令行参数获取
    if args.stock_codes:
        stock_codes.extend([code.strip() for code in args.stock_codes.split(',')])
    
    # 从文件获取
    if args.stock_file:
        try:
            with open(args.stock_file, 'r', encoding='utf-8') as f:
                file_codes = [line.strip() for line in f if line.strip()]
                stock_codes.extend(file_codes)
            logger.info(f"从文件 {args.stock_file} 加载了 {len(file_codes)} 个股票代码")
        except Exception as e:
            logger.error(f"读取股票代码文件失败: {str(e)}")
    
    # 去重
    stock_codes = list(set(stock_codes))
    if not stock_codes:
        logger.warning("未指定股票代码，将使用全市场回测模式")
    else:
        logger.info(f"总共加载了 {len(stock_codes)} 个股票代码")
    
    return stock_codes if stock_codes else None


def validate_dates(start_date, end_date):
    """
    验证日期格式和范围
    
    Args:
        start_date (str): 开始日期
        end_date (str): 结束日期
        
    Returns:
        tuple: (验证后的开始日期, 验证后的结束日期)
    """
    try:
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        
        # 验证日期范围
        if start_dt >= end_dt:
            logger.error("开始日期必须早于结束日期")
            sys.exit(1)
        
        # 验证日期不能太旧（最多10年）
        max_backtest_period = 365*5 # 最多5年内数据回测
        min_date = datetime.now() - timedelta(days=max_backtest_period)
        if start_dt < min_date:
            logger.warning("回测开始日期较早，可能会影响数据质量")
        
        # 验证日期不能是未来日期
        if end_dt > datetime.now():
            logger.warning("结束日期不能是未来日期，已调整为今天")
            end_dt = datetime.now()
        
        return start_dt.strftime('%Y-%m-%d'), end_dt.strftime('%Y-%m-%d')
    except ValueError as e:
        logger.error(f"日期格式错误: {str(e)}")
        sys.exit(1)


def setup_output_directory(args, config):
    """
    设置输出目录
    
    Args:
        args: 命令行参数
        config: 配置字典
        
    Returns:
        str: 输出目录路径
    """
    output_dir = args.output_dir
    if not output_dir:
        output_dir = config.get('backtester', {}).get('results_dir', '../logs/backtest_results/')
    
    # 转换为绝对路径
    if not os.path.isabs(output_dir):
        output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), output_dir)
    
    # 确保目录存在
    os.makedirs(output_dir, exist_ok=True)
    logger.info(f"回测结果将保存到: {output_dir}")
    
    return output_dir


def run_backtest(args, config):
    """
    运行回测
    
    Args:
        args: 命令行参数
        config: 配置字典
        
    Returns:
        dict: 回测结果
    """
    # 设置回测参数
    max_backtest_period = config.get('backtester', {}).get('max_backtest_period', 1825) # 最多5年内数据回测
    start_date = args.start_date or (datetime.now() - timedelta(days=max_backtest_period)).strftime('%Y-%m-%d')
    end_date = args.end_date or datetime.now().strftime('%Y-%m-%d')
    start_date, end_date = validate_dates(start_date, end_date)
    
    initial_capital = args.initial_capital or config.get('backtester', {}).get('initial_capital', 1000000)
    max_positions = args.max_positions or config.get('backtester', {}).get('max_positions', 5)
    
    logger.info(f"回测参数设置:")
    logger.info(f"- 时间范围: {start_date} 到 {end_date}")
    logger.info(f"- 初始资金: {initial_capital} 元")
    logger.info(f"- 最大持仓数: {max_positions} 只")
    logger.info(f"- 回测模式: {'全市场' if args.mode == 'market' else '特定股票'}")
    
    # 初始化组件
    data_processor = DataProcessor(config=config.get('data_processor', {}))
    strategy = FlexStrategy(config=config.get('strategy', {}))

    # 获取股票代码（如果是特定股票回测模式）
    stock_codes = None
    if args.mode == 'stock':
        stock_codes = get_stock_codes(args)
 
    # 创建回测器
    backtester = Backtester(
        start_date=start_date,
        end_date=end_date,
        initial_capital=initial_capital,
        max_stocks=max_positions,
        strategy=strategy,
        data_processor=data_processor
    )
    
    # 运行回测
    results = backtester.run_backtest(stock_codes=stock_codes)
    
    # 可视化结果
    if args.plot or args.save_plot:
        output_dir = setup_output_directory(args, config)
        plt.figure(figsize=(14, 12))
        
        # 绘制累计收益率
        plt.subplot(3, 1, 1)
        if hasattr(backtester, 'portfolio_history') and not backtester.portfolio_history.empty:
            plt.plot(backtester.portfolio_history['date'], backtester.portfolio_history['total_value'] / initial_capital - 1)
            plt.title('累计收益率')
            plt.ylabel('收益率')
            plt.grid(True)
        
        # 绘制最大回撤
        plt.subplot(3, 1, 2)
        if hasattr(backtester, 'portfolio_history') and not backtester.portfolio_history.empty:
            cumulative_max = backtester.portfolio_history['total_value'].cummax()
            drawdown = (backtester.portfolio_history['total_value'] - cumulative_max) / cumulative_max
            plt.plot(backtester.portfolio_history['date'], drawdown)
            plt.title('最大回撤')
            plt.ylabel('回撤')
            plt.grid(True)
        
        # 绘制持仓数量
        plt.subplot(3, 1, 3)
        if hasattr(backtester, 'portfolio_history') and not backtester.portfolio_history.empty:
            plt.plot(backtester.portfolio_history['date'], backtester.portfolio_history['num_positions'])
            plt.title('持仓数量变化')
            plt.ylabel('持仓数量')
            plt.grid(True)
        plt.tight_layout()
        
        # 保存图表
        if args.save_plot:
            plot_path = os.path.join(output_dir, f"backtest_results_{start_date}_{end_date}.png")
            plt.savefig(plot_path)
            logger.info(f"回测结果图表已保存到: {plot_path}")
        
        # 显示图表
        if args.plot:
            try:
                plt.show()
            except:
                logger.warning("无法显示图表，已保存到文件")
    
    # 保存详细结果
    if results and args.output_dir:
        output_dir = setup_output_directory(args, config)
        results_file = os.path.join(output_dir, f"backtest_summary_{start_date}_{end_date}.csv")
        
        # 将结果转换为DataFrame并保存
        results_df = pd.DataFrame([results])
        results_df.to_csv(results_file, index=False, encoding='utf-8-sig')
        logger.info(f"回测结果已保存到: {results_file}")
    
    return results


def parse_arguments():
    """
    解析命令行参数
    
    Returns:
        argparse.Namespace: 解析后的参数
    """
    parser = argparse.ArgumentParser(description='股票策略回测系统')
    
    # 回测时间范围
    parser.add_argument('--start-date', type=str, help='回测开始日期 (YYYY-MM-DD)')
    parser.add_argument('--end-date', type=str, help='回测结束日期 (YYYY-MM-DD)')
    
    # 回测模式
    parser.add_argument('--mode', type=str, choices=['market', 'stock'], default='market',
                        help='回测模式: market(全市场回测) 或 stock(特定股票回测)')
    
    # 特定股票回测参数
    parser.add_argument('--stock-codes', type=str, help='股票代码列表，逗号分隔，如: 600000,600036')
    parser.add_argument('--stock-file', type=str, help='包含股票代码的文件路径，每行一个股票代码')
    
    # 资金和持仓配置
    parser.add_argument('--initial-capital', type=float, help='初始资金')
    parser.add_argument('--max-positions', type=int, help='最大持仓数量')
    
    # 输出配置
    parser.add_argument('--output-dir', type=str, help='结果输出目录')
    parser.add_argument('--plot', action='store_true', help='是否显示回测结果图表')
    parser.add_argument('--save-plot', action='store_true', help='是否保存回测结果图表')
    
    # 配置文件
    parser.add_argument('--config', type=str, help='配置文件路径')
    
    return parser.parse_args()


def main():
    """
    主函数
    """
    # 确保日志目录存在
    log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
    os.makedirs(log_dir, exist_ok=True)
    
    # 解析命令行参数
    args = parse_arguments()
    
    # 加载配置
    config = load_config(args.config)
    
    # 运行回测
    results = run_backtest(args, config)
    
    if results:
        logger.info("回测完成！")
        logger.info(f"最终资金: {results['final_capital']:.2f} 元")
        logger.info(f"总收益率: {results['total_return']*100:.2f}%")
        logger.info(f"年化收益率: {results['annual_return']*100:.2f}%")
        logger.info(f"夏普比率: {results['sharpe_ratio']:.2f}")
        logger.info(f"最大回撤: {results['max_drawdown']*100:.2f}%")
    else:
        logger.error("回测失败，请检查日志获取详细信息")


if __name__ == "__main__":
    main()


# bash
# python backtest.py     
# python backtest.py --start-date 2022-01-01 --end-date 2023-12-31    # 指定时间范围的全市场回测
# python backtest.py --mode stock --stock-codes 600000,600036,601318  # 制定股票进行回测
# python backtest.py --mode stock --stock-file stocks.txt   # 从文件读取股票代码进行回测
# python backtest.py --initial-capital 500000 --max-positions 3 --save-plot --output-dir ./results    # 自定义参数并保存图表