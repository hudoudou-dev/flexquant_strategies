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
import requests # Add requests for webhooks

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入自定义模块
from src.data_fetch import DataFetcher
from src.data_processor import DataProcessor
from src.strategy import FlexStrategy
from src.portfolio import PortfolioManager
from src.backtester import Backtester # Import Backtester

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

def send_feishu_notification(webhook_url, message):
    """
    发送飞书通知
    """
    headers = {'Content-Type': 'application/json'}
    payload = {
        "msg_type": "text",
        "content": {
            "text": message
        }
    }
    try:
        response = requests.post(webhook_url, headers=headers, json=payload)
        response.raise_for_status()
        logger.info(f"飞书通知发送成功: {response.json()}")
    except requests.exceptions.RequestException as e:
        logger.error(f"发送飞书通知失败: {e}")

def send_dingtalk_notification(webhook_url, message):
    """
    发送钉钉通知
    """
    headers = {'Content-Type': 'application/json'}
    payload = {
        "msgtype": "text",
        "text": {
            "content": message
        }
    }
    try:
        response = requests.post(webhook_url, headers=headers, json=payload)
        response.raise_for_status()
        logger.info(f"钉钉通知发送成功: {response.json()}")
    except requests.exceptions.RequestException as e:
        logger.error(f"发送钉钉通知失败: {e}")


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
        self.strategy = FlexStrategy(data_processor=self.data_processor, config=self.config.get('strategy', {}))
        self.portfolio_manager = PortfolioManager(config=self.config.get('portfolio', {}))
        self.backtester = Backtester(
            start_date=(datetime.now() - timedelta(days=self.config['backtester'].get('max_backtest_period', 180))).strftime('%Y-%m-%d'),
            end_date=datetime.now().strftime('%Y-%m-%d'),
            initial_capital=self.config['backtester'].get('initial_capital', 1000000),
            max_stocks=self.config['backtester'].get('max_stocks', 5),
            strategy=self.strategy,
            data_processor=self.data_processor
        )
        
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
            self.data_fetcher.fetch_all_stocks_kline_datas_daily_auto_update()
            
            # 2. 处理数据
            logger.info("正在处理数据...")
            self.data_processor.process_daily_data()
            
            # 3. 执行策略筛选
            logger.info("正在执行策略筛选...")
            stock_pool = self.strategy.get_candidate_stocks()
            top_stocks = self.strategy.score_and_rank_stocks(stock_pool)
            
            # 4. 执行策略筛选
            logger.info("正在执行策略筛选...")
            stock_pool = self.strategy.get_candidate_stocks()
            top_stocks = self.strategy.score_and_rank_stocks(stock_pool)
            
            # 5. 执行回测
            logger.info("正在对推荐股票进行回测...")
            backtest_results = None
            if top_stocks:
                # 提取推荐股票代码
                recommended_stock_codes = [stock['code'] for stock in top_stocks]
                # 运行回测
                backtest_results = self.backtester.run_backtest(stock_codes=recommended_stock_codes)
            else:
                logger.warning("没有推荐股票，跳过回测。")

            # 6. 构建推送消息
            notification_message = f"## FlexQuant 每日任务报告 - {datetime.now().strftime('%Y-%m-%d')}\n\n"
            notification_message += "### 今日推荐股票:\n"
            if top_stocks:
                for i, stock in enumerate(top_stocks[:10]): # 最多显示前10只
                    notification_message += f"{i+1}. {stock['name']} ({stock['code']}), 评分: {stock['score']:.2f}\n"
            else:
                notification_message += "无推荐股票。\n"
            
            notification_message += "\n### 回测结果概览:\n"
            if backtest_results:
                notification_message += f"总收益率: {backtest_results['total_return']*100:.2f}%\n"
                notification_message += f"年化收益率: {backtest_results['annual_return']*100:.2f}%\n"
                notification_message += f"夏普比率: {backtest_results['sharpe_ratio']:.2f}\n"
                notification_message += f"最大回撤: {backtest_results['max_drawdown']*100:.2f}%\n"
                notification_message += f"交易次数: {backtest_results['num_trades']}\n"
                notification_message += f"胜率: {backtest_results['win_rate']*100:.2f}%\n"
            else:
                notification_message += "无回测结果。\n"

            # 7. 发送通知
            feishu_webhook_url = self.config.get('scheduler', {}).get('feishu_webhook_url')
            dingtalk_webhook_url = self.config.get('scheduler', {}).get('dingtalk_webhook_url')

            if feishu_webhook_url:
                send_feishu_notification(feishu_webhook_url, notification_message)
            else:
                logger.warning("未配置飞书 Webhook URL，跳过飞书通知。")
            
            if dingtalk_webhook_url:
                send_dingtalk_notification(dingtalk_webhook_url, notification_message)
            else:
                logger.warning("未配置钉钉 Webhook URL，跳过钉钉通知。")

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
        
        # 如果配置了启动时立即执行，则先运行一次
        if self.config.get('scheduler', {}).get('run_on_startup', False):
            logger.info("配置为启动时立即执行任务...")
            self.daily_task()
        
        # 持续运行调度器
        try:
            while True:
                schedule.run_pending()
                time.sleep(10)  # 缩短检查周期到 10 秒，增加灵敏度
        except KeyboardInterrupt:
            logger.info("调度器手动停止")
        except Exception as e:
            logger.error(f"调度器运行时发生未捕获异常: {str(e)}", exc_info=True)
            # 休息一段时间后尝试重新启动或继续循环，确保 24 小时运行
            time.sleep(60)
            self.start_scheduler()


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