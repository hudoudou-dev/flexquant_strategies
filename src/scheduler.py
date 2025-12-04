#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
@Author:            hudoudou-dev
@Email:             humengnju@qq.com
@Create Time:       2025-11-20
@Last Modified:     2025-11-20
@Modified By:       hudoudou-dev
@Version:           1.0
@Description:       implement a daily scheduled task function to automatically run the processes of stock data acquisition, processing, and strategy screening.
@Notes:             none.
@History:
                    v1.0, create.
"""


import os
import sys
import time
import logging
import yaml
import schedule
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入自定义模块
from src.data_fetch import DataFetcher
from src.data_processor import DataProcessor
from src.strategy import FlexStrategy
from src.portfolio import PortfolioManager

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs', 'scheduler.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('scheduler')


class StrategyScheduler:
    """
    策略调度器类，负责定时执行数据获取和策略筛选任务
    """
    
    def __init__(self, config_path=None):
        """
        初始化调度器
        
        Args:
            config_path: 配置文件路径
        """
        self.config = self._load_config(config_path)
        self.data_fetcher = DataFetcher(config=self.config.get('data_fetch', {}))
        self.data_processor = DataProcessor(config=self.config.get('data_processor', {}))
        self.strategy = FlexStrategy(config=self.config.get('strategy', {}))
        self.portfolio_manager = PortfolioManager(config=self.config.get('portfolio', {}))
        
        # 从配置中读取调度时间
        self.schedule_time = self.config.get('scheduler', {}).get('daily_run_time', '20:00')
        
    def _load_config(self, config_path=None):
        """
        加载配置文件
        
        Args:
            config_path: 配置文件路径
            
        Returns:
            dict: 配置字典
        """
        if config_path is None:
            config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config', 'config.yaml')
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            logger.info(f"成功加载配置文件: {config_path}")
            return config
        except Exception as e:
            logger.error(f"加载配置文件失败: {str(e)}")
            # 返回默认配置
            return {
                'scheduler': {
                    'daily_run_time': '20:00'
                }
            }
    
    def daily_task(self):
        """
        每日定时任务，执行完整的数据获取、处理和策略筛选流程
        """
        logger.info(f"开始执行每日任务 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        try:
            # 1. 更新股票数据
            logger.info("正在更新股票数据...")
            self.data_fetcher.update_daily_data()
            
            # 2. 处理数据
            logger.info("正在处理数据...")
            self.data_processor.process_daily_data()
            
            # 3. 执行策略筛选
            logger.info("正在执行策略筛选...")
            stock_pool = self.strategy.get_candidate_stocks()
            top_stocks = self.strategy.score_and_rank_stocks(stock_pool)
            
            # 4. 输出今日推荐股票
            logger.info(f"今日推荐股票 (Top {len(top_stocks)}):")
            for stock in top_stocks[:10]:  # 最多显示前10只
                logger.info(f"股票代码: {stock['code']}, 股票名称: {stock['name']}, 评分: {stock['score']:.2f}")
            
            # 5. 更新投资组合（如果需要）
            if self.config.get('portfolio', {}).get('auto_update', False):
                logger.info("正在更新投资组合...")
                # 这里可以根据需要实现投资组合的自动更新逻辑
                # 例如：卖出不符合条件的股票，买入新推荐的股票
                
            logger.info("每日任务执行完成")
            
            # 保存任务执行记录
            self._save_execution_record()
            
        except Exception as e:
            logger.error(f"每日任务执行失败: {str(e)}", exc_info=True)
    
    def _save_execution_record(self):
        """
        保存任务执行记录
        """
        record_file = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'logs',
            'execution_records.log'
        )
        
        try:
            with open(record_file, 'a', encoding='utf-8') as f:
                f.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Task executed\n")
        except Exception as e:
            logger.error(f"保存执行记录失败: {str(e)}")
    
    def manual_run(self):
        """
        手动运行任务（用于测试或立即执行）
        """
        logger.info("手动触发任务执行")
        self.daily_task()
    
    def start_scheduler(self):
        """
        启动调度器
        """
        # 设置每日定时任务
        schedule.every().day.at(self.schedule_time).do(self.daily_task)
        logger.info(f"调度器已启动，将在每日 {self.schedule_time} 执行任务")
        logger.info("按 Ctrl+C 停止调度器")
        
        # 持续运行调度器
        try:
            while True:
                schedule.run_pending()
                time.sleep(60)  # 每分钟检查一次是否有待执行的任务
        except KeyboardInterrupt:
            logger.info("调度器已停止")
        except Exception as e:
            logger.error(f"调度器运行出错: {str(e)}", exc_info=True)


def main():
    """
    主函数
    """
    # 确保日志目录存在
    log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs')
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # 创建并启动调度器
    scheduler = StrategyScheduler()
    
    # 检查是否需要立即运行一次（可选）
    if len(sys.argv) > 1 and sys.argv[1] == '--run-now':
        scheduler.manual_run()
    else:
        scheduler.start_scheduler()


if __name__ == "__main__":
    main()

# 启动定时调度器：python src/scheduler.py
# 立即执行一次任务：python src/scheduler.py --run-now