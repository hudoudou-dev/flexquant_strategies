#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
@Author:            hudoudou-dev
@Email:             humengnju@qq.com
@Create Time:       2026-04-15
@Last Modified:     2026-04-15
@Modified By:       hudoudou-dev
@Version:           1.0
@Description:       Parameter optimization tool for scoring strategy.
                    Supports grid search, random search, and bayesian optimization.
@Notes:             This script optimizes scoring weights based on historical backtest performance.
@History:
                    v1.0, create. Implemented grid search optimization.
"""

import os
import sys
import yaml
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from itertools import product
import json

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.backtester import Backtester
from src.strategy import FlexStrategy
from src.data_processor import DataProcessor

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/parameter_optimization.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('param_optimizer')


class ParameterOptimizer:
    """参数优化器，用于优化评分策略的因子权重"""
    
    def __init__(self, config_path='config/config.yaml'):
        """
        初始化参数优化器
        
        参数:
            config_path (str): 配置文件路径
        """
        self.config_path = config_path
        self.config = self._load_config()
        self.optimization_config = self.config.get('strategy', {}).get('scoring_optimization', {})
        self.results = []
        
    def _load_config(self):
        """加载配置文件"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"加载配置文件失败: {str(e)}")
            return {}
    
    def _save_config(self, config):
        """保存配置文件"""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                yaml.dump(config, f, allow_unicode=True, default_flow_style=False)
            logger.info(f"配置已保存到 {self.config_path}")
        except Exception as e:
            logger.error(f"保存配置文件失败: {str(e)}")
    
    def _generate_weight_combinations(self, method='grid_search', n_samples=100):
        """
        生成权重组合
        
        参数:
            method (str): 搜索方法
            n_samples (int): 随机搜索的采样数量
            
        返回:
            list: 权重组合列表
        """
        search_ranges = self.optimization_config.get('weight_search_ranges', {})
        
        if method == 'grid_search':
            # 网格搜索：生成所有可能的组合
            param_names = list(search_ranges.keys())
            param_values = [range(r[0], r[1]+1, 5) for r in search_ranges.values()]
            
            combinations = []
            for combo in product(*param_values):
                # 确保权重总和接近100
                if 90 <= sum(combo) <= 110:
                    weight_dict = dict(zip(param_names, combo))
                    combinations.append(weight_dict)
            
            logger.info(f"网格搜索生成了 {len(combinations)} 个权重组合")
            return combinations
            
        elif method == 'random_search':
            # 随机搜索：随机采样
            combinations = []
            for _ in range(n_samples):
                weight_dict = {}
                for param_name, (min_val, max_val) in search_ranges.items():
                    weight_dict[param_name] = np.random.randint(min_val, max_val+1)
                
                # 归一化权重
                total = sum(weight_dict.values())
                if total > 0:
                    weight_dict = {k: int(v * 100 / total) for k, v in weight_dict.items()}
                    combinations.append(weight_dict)
            
            logger.info(f"随机搜索生成了 {len(combinations)} 个权重组合")
            return combinations
        
        else:
            logger.warning(f"未知的优化方法: {method}")
            return []
    
    def _run_backtest_with_weights(self, weights, start_date, end_date):
        """
        使用指定权重运行回测
        
        参数:
            weights (dict): 权重字典
            start_date (str): 开始日期
            end_date (str): 结束日期
            
        返回:
            dict: 回测结果
        """
        # 更新配置中的权重
        test_config = self.config.copy()
        test_config['strategy']['scoring_weights'].update(weights)
        
        # 初始化组件 - 传递完整配置
        data_processor = DataProcessor(config=test_config)
        strategy = FlexStrategy(data_processor=data_processor, config=test_config.get('strategy', {}))
        
        # 获取预热期配置，但在优化时禁用预热期以加快速度
        warm_up_period = 0  # 优化时禁用预热期
        
        # 创建回测器
        backtester = Backtester(
            start_date=start_date,
            end_date=end_date,
            initial_capital=test_config['backtester']['initial_capital'],
            max_stocks=test_config['backtester']['max_stocks'],
            strategy=strategy,
            data_processor=data_processor,
            warm_up_period=warm_up_period,
            min_buy_score=test_config['backtester'].get('min_buy_score', 0),
            score_thresholds=test_config['backtester'].get('score_thresholds', {}),
            position_management=test_config['backtester'].get('position_management', {})
        )
        
        # 运行回测
        results = backtester.run_backtest()
        
        return results
    
    def optimize(self, start_date=None, end_date=None):
        """
        执行参数优化
        
        参数:
            start_date (str): 优化开始日期
            end_date (str): 优化结束日期
            
        返回:
            dict: 最优参数
        """
        logger.info("="*60)
        logger.info("开始参数优化")
        logger.info("="*60)
        
        # 设置优化周期
        optimization_period = self.optimization_config.get('optimization_period', 180)
        if not end_date:
            end_date = datetime.now().strftime('%Y-%m-%d')
        if not start_date:
            start_date = (datetime.now() - timedelta(days=optimization_period)).strftime('%Y-%m-%d')
        
        logger.info(f"优化周期: {start_date} 到 {end_date}")
        
        # 生成权重组合
        method = self.optimization_config.get('optimization_method', 'grid_search')
        weight_combinations = self._generate_weight_combinations(method)
        
        if not weight_combinations:
            logger.error("未生成任何权重组合，优化终止")
            return None
        
        # 遍历所有权重组合
        best_result = None
        best_weights = None
        best_score = -np.inf
        
        for i, weights in enumerate(weight_combinations):
            logger.info(f"\n测试组合 {i+1}/{len(weight_combinations)}: {weights}")
            
            try:
                # 运行回测
                results = self._run_backtest_with_weights(weights, start_date, end_date)
                
                if results:
                    # 计算综合得分（年化收益率 - 最大回撤）
                    score = results.get('annual_return', 0) - abs(results.get('max_drawdown', 0))
                    
                    # 记录结果
                    result_record = {
                        'weights': weights,
                        'annual_return': results.get('annual_return', 0),
                        'max_drawdown': results.get('max_drawdown', 0),
                        'sharpe_ratio': results.get('sharpe_ratio', 0),
                        'win_rate': results.get('win_rate', 0),
                        'score': score
                    }
                    self.results.append(result_record)
                    
                    logger.info(f"  年化收益率: {results.get('annual_return', 0)*100:.2f}%")
                    logger.info(f"  最大回撤: {results.get('max_drawdown', 0)*100:.2f}%")
                    logger.info(f"  夏普比率: {results.get('sharpe_ratio', 0):.2f}")
                    logger.info(f"  综合得分: {score:.4f}")
                    
                    # 更新最优结果
                    if score > best_score:
                        best_score = score
                        best_result = results
                        best_weights = weights
                        
            except Exception as e:
                logger.error(f"测试组合 {i+1} 时出错: {str(e)}")
                continue
        
        # 输出最优结果
        if best_weights:
            logger.info("\n" + "="*60)
            logger.info("优化完成！最优参数:")
            logger.info("="*60)
            logger.info(f"最优权重: {best_weights}")
            logger.info(f"年化收益率: {best_result.get('annual_return', 0)*100:.2f}%")
            logger.info(f"最大回撤: {best_result.get('max_drawdown', 0)*100:.2f}%")
            logger.info(f"夏普比率: {best_result.get('sharpe_ratio', 0):.2f}")
            logger.info(f"综合得分: {best_score:.4f}")
            
            # 保存结果
            self._save_optimization_results(best_weights, best_result)
            
            return best_weights
        else:
            logger.warning("未找到有效的优化结果")
            return None
    
    def _save_optimization_results(self, best_weights, best_result):
        """
        保存优化结果
        
        参数:
            best_weights (dict): 最优权重
            best_result (dict): 最优回测结果
        """
        # 保存到JSON文件
        output_dir = 'logs/optimization_results'
        os.makedirs(output_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = os.path.join(output_dir, f'optimization_{timestamp}.json')
        
        result_data = {
            'timestamp': timestamp,
            'best_weights': best_weights,
            'best_result': {
                'annual_return': best_result.get('annual_return', 0),
                'max_drawdown': best_result.get('max_drawdown', 0),
                'sharpe_ratio': best_result.get('sharpe_ratio', 0),
                'win_rate': best_result.get('win_rate', 0)
            },
            'all_results': self.results
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"优化结果已保存到 {output_file}")
        
        # 询问是否应用最优参数
        logger.info("\n是否将最优参数应用到配置文件？")
        logger.info("如需应用，请手动修改 config/config.yaml 文件中的 scoring_weights 部分")


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='评分策略参数优化工具')
    parser.add_argument('--config', type=str, default='config/config.yaml',
                       help='配置文件路径')
    parser.add_argument('--start-date', type=str, default=None,
                       help='优化开始日期 (YYYY-MM-DD)')
    parser.add_argument('--end-date', type=str, default=None,
                       help='优化结束日期 (YYYY-MM-DD)')
    
    args = parser.parse_args()
    
    # 创建优化器
    optimizer = ParameterOptimizer(config_path=args.config)
    
    # 执行优化
    best_weights = optimizer.optimize(start_date=args.start_date, end_date=args.end_date)
    
    if best_weights:
        logger.info("\n优化成功！建议使用以下权重配置:")
        for key, value in best_weights.items():
            logger.info(f"  {key}: {value}")


if __name__ == '__main__':
    main()
