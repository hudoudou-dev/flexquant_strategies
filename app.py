import streamlit as st
import yaml
import os
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import subprocess
import time
import signal

# Set page config
st.set_page_config(page_title="FlexQuant Strategies", layout="wide")

# Constants
CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'config', 'config.yaml')
DATA_DIR = os.path.join(os.path.dirname(__file__), 'data', 'raw_data')
LOGS_DIR = os.path.join(os.path.dirname(__file__), 'logs')
SERVICE_PID_FILE = os.path.join(LOGS_DIR, 'service.pid')

# Helper functions
def load_config():
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def save_config(config):
    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
        yaml.dump(config, f, allow_unicode=True, default_flow_style=False)

def get_service_status():
    if os.path.exists(SERVICE_PID_FILE):
        try:
            with open(SERVICE_PID_FILE, 'r') as f:
                pid = int(f.read().strip())
            # Check if process is running
            os.kill(pid, 0)
            return True, pid
        except (ValueError, ProcessLookupError, OSError):
            return False, None
    return False, None

def start_service():
    # Start scheduler.py as a background process
    cmd = [os.sys.executable, os.path.join(os.path.dirname(__file__), 'src', 'scheduler.py')]
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    with open(SERVICE_PID_FILE, 'w') as f:
        f.write(str(process.pid))
    return process.pid

def stop_service():
    status, pid = get_service_status()
    if status:
        try:
            os.kill(pid, signal.SIGTERM)
            if os.path.exists(SERVICE_PID_FILE):
                os.remove(SERVICE_PID_FILE)
            return True
        except Exception as e:
            st.error(f"Failed to stop service: {e}")
    return False

# Sidebar Navigation
st.sidebar.title("FlexQuant Strategies")
# 页面映射关系
pages_mapping = {
    "Home": "首页说明",
    "Data Browser": "股票数据概览",
    "Data Management": "股票数据更新",
    "Configuration": "选股策略配置",
    "Stock Selection": "选股生成排序",
    "Backtest Analysis": "回测分析",
    "Service Management": "服务管理记录"
}
# 翻转映射用于逻辑判断
reverse_mapping = {v: k for k, v in pages_mapping.items()}

# 按照用户要求的顺序排列
display_pages = [
    pages_mapping["Home"],
    pages_mapping["Data Browser"],
    pages_mapping["Data Management"],
    pages_mapping["Configuration"],
    pages_mapping["Stock Selection"],
    pages_mapping["Backtest Analysis"],
    pages_mapping["Service Management"]
]

# 从query_params获取当前页面，用于初始化侧边栏
query_page = st.query_params.get("page", None)
initial_page_index = 0
if query_page and query_page in reverse_mapping: # Use reverse_mapping to check if the query_page is a valid internal page name
    initial_page_index = display_pages.index(pages_mapping[query_page])

selected_display_page = st.sidebar.radio("导航栏", display_pages, index=initial_page_index)
page = reverse_mapping[selected_display_page]

# 如果query_params中有page，且与当前page不符，则更新query_params
if query_page and query_page != selected_display_page:
    st.query_params["page"] = selected_display_page
    st.experimental_rerun()

if page == "Home":
    st.title("欢迎使用 FlexQuant Strategies")
    st.markdown("""
    这是一个自动化的股票数据获取和策略筛选系统。
    
    ### 核心功能:
    1. **后台服务**: 全天候自动更新 A 股股票每日走势数据。
    2. **数据管理**: 手动触发不同的数据获取策略（全量、增量、特定股票）。
    3. **选股策略**: 根据设定的参数运行策略，发现具有潜力的股票。
    4. **数据浏览器**: 可视化股票数据，绘制 K 线图并分析历史趋势。
    5. **配置管理**: 调整策略超参数和系统设置。
    
    请使用左侧侧边栏导航至不同的功能模块。
    """)
    
    status, pid = get_service_status()
    if status:
        st.success(f"后台服务当前状态：**正在运行** (PID: {pid})")
    else:
        st.warning("后台服务当前状态：**已停止**")

elif page == "Data Management":
    st.title("股票数据更新")
    st.info("注意：所有数据更新策略默认仅获取并保留最近180个交易日的股票数据。")
    
    from src.data_fetch import DataFetcher
    config = load_config()
    fetcher = DataFetcher(config=config.get('data_fetch', {}))
    
    st.subheader("数据更新策略")
    
    strategy_type_display = st.radio(
        "选择更新策略",
        ["全量股票数据全局更新", "全量股票数据增量式更新", "指定股票数据更新"]
    )
    
    # 将显示名称映射回内部函数名
    strategy_type_map = {
        "全量股票数据全局更新": "fetch_all_stocks_kline_datas",
        "全量股票数据增量式更新": "fetch_all_stocks_kline_datas_incremental",
        "指定股票数据更新": "fetch_all_stocks_kline_datas_specific"
    }
    strategy_type = strategy_type_map[strategy_type_display]
    
    with st.expander("策略说明"):
        if strategy_type == "fetch_all_stocks_kline_datas":
            st.warning("警告：此策略将获取所有A股股票的历史数据。这可能需要很长时间，并可能触发API限流。")
        elif strategy_type == "fetch_all_stocks_kline_datas_incremental":
            st.info("为现有股票增量更新自上次更新以来的缺失数据。")
        elif strategy_type == "fetch_all_stocks_kline_datas_specific":
            st.info("获取指定股票代码列表的数据。股票代码为必填项。")

    if strategy_type == "fetch_all_stocks_kline_datas_specific":
        stock_input = st.text_input("输入股票代码（例如：000001, 600000, 000002）", "")
        start_date = st.date_input("开始日期", value=datetime.now() - timedelta(days=180))
        end_date = st.date_input("结束日期", value=datetime.now())
    
    if strategy_type == "fetch_all_stocks_kline_datas":
        start_date_full = st.date_input("开始日期（全量更新）", value=datetime.now() - timedelta(days=180))
        end_date_full = st.date_input("结束日期", value=datetime.now())

    if st.button("执行策略", type="primary"):
        try:
            with st.spinner(f"正在执行 {strategy_type_display}..."):
                if strategy_type == "fetch_all_stocks_kline_datas_incremental":
                    count = fetcher.fetch_all_stocks_kline_datas_incremental()
                    st.success(f"成功增量更新 {count} 只股票。")
                
                elif strategy_type == "fetch_all_stocks_kline_datas":
                    count = fetcher.fetch_all_stocks_kline_datas(start_date=start_date_full.strftime('%Y-%m-%d'), 
                                                end_date=end_date_full.strftime('%Y-%m-%d'))
                    st.success(f"成功获取 {count} 只股票的全部数据。")
                
                elif strategy_type == "fetch_all_stocks_kline_datas_specific":
                    if not stock_input:
                        st.error("请输入至少一个股票代码。")
                    else:
                        codes = [c.strip() for c in stock_input.split(',')]
                        count = fetcher.fetch_all_stocks_kline_datas_specific(codes, 
                                                            start_date=start_date.strftime('%Y-%m-%d'),
                                                            end_date=end_date.strftime('%Y-%m-%d'))
                        st.success(f"成功获取 {count} 只股票的数据。")
        except Exception as e:
            st.error(f"执行策略时发生错误: {e}")

elif page == "Stock Selection":
    st.title("选股生成排序")
    
    from src.data_processor import DataProcessor
    from src.strategy import FlexStrategy
    
    config = load_config()
    processor = DataProcessor(config=config)
    strategy = FlexStrategy(data_processor=processor, config=config)

    # Initialize session state for stock selection results
    if 'stock_selection_results' not in st.session_state:
        st.session_state['stock_selection_results'] = None
    
    st.subheader("当前选股参数")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.write(f"**价格区间:** {config['strategy']['stock_selection'].get('min_price', 10.0)} - {config['strategy']['stock_selection'].get('max_price', 20.0)}")
    with col2:
        st.write(f"**最高总市值:** {config['strategy']['stock_selection'].get('max_market_cap', 500.0)} (亿元)")
    with col3:
        st.write(f"**涨停次数:** {config['strategy']['stock_selection'].get('min_limit_up_count', 2)} - {config['strategy']['stock_selection'].get('max_limit_up_count', 5)}")

    with st.expander("查看选股策略详情与计算方式"):
        st.markdown("### 选股策略概述")
        st.markdown("""
        本选股策略旨在识别具有特定技术和基本面特征的股票。
        它通过一系列筛选条件和评分机制，从市场中选出符合预设标准的股票。
        """)
        
        st.markdown("### 策略超参数")
        st.json(config['strategy']['stock_selection']) # Display all selection hyperparameters
        
        st.markdown("### 核心计算方式")
        st.markdown("""
        1. **数据加载与预处理**:
           - 加载每只股票的历史K线数据。
           - 对数据进行清洗和标准化，确保数据质量。
        2. **特征计算**:
           - 根据配置中的技术指标（如KDJ、MACD）和自定义特征（如涨停次数、价格波动）计算股票的各项指标。
           - 这些特征将作为后续评分的依据。
        3. **股票筛选**:
           - 根据超参数中设定的条件（如价格区间、市值范围、涨停次数要求等）过滤不符合条件的股票。
           - 剔除ST股票、停牌股票以及北交所股票。
        4. **评分与排序**:
           - 对通过筛选的股票，根据其特征值和预设的权重进行综合评分。
           - 评分高的股票将被推荐，并按分数从高到低排序。
        5. **结果展示**:
           - 展示得分最高的股票列表，并提供K线图预览功能。
        """)
 
    if st.button("运行选股策略", type="primary"):
        stock_codes = processor.get_all_available_stocks()
        if not stock_codes:
            st.error("未找到股票数据。请先获取数据。")
        else:
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            candidates = {}
            total = len(stock_codes)
            
            for i, code in enumerate(stock_codes):
                status_text.text(f"正在处理 {code} ({i+1}/{total})...")
                try:
                    df = processor.load_stock_data(code)
                    if df is not None and not df.empty:
                        # Calculate features needed for scoring
                        df_with_features = strategy._calculate_features(df)
                        candidates[code] = df_with_features
                except Exception as e:
                    st.warning(f"处理股票 {code} 时发生错误: {e}")
                    continue
                progress_bar.progress((i + 1) / total)
            
            status_text.text("正在对股票进行评分和排序...")
            results = strategy.score_and_rank_stocks(candidates)
            st.session_state['stock_selection_results'] = results # Store results in session state
            
    # Display results if available in session state
    if st.session_state['stock_selection_results']:
        results = st.session_state['stock_selection_results']
        if results:
            st.subheader(f"策略推荐 (前 {min(50, len(results))} 名)")
            # Convert results to DataFrame for better display
            results_df = pd.DataFrame(results).head(50) # Limit to top 50
            # Reorder and rename columns for display
            display_df = results_df[['code', 'name', 'score', 'price', 'date']]
            display_df.columns = ['代码', '名称', '得分', '价格', '日期']
            
            st.dataframe(display_df.style.format({'得分': '{:.2f}', '价格': '{:.2f}'}), use_container_width=True)
            
            # Allow user to select a recommended stock to view K-line
            selected_stock_code = st.selectbox("选择一只推荐股票查看K线图", display_df['代码'].tolist())
            if selected_stock_code:
                file_name = f"{selected_stock_code}.parquet"
                file_path = os.path.join(DATA_DIR, file_name)
                if not os.path.exists(file_path):
                    # 兼容旧的 csv
                    file_path = os.path.join(DATA_DIR, f"{selected_stock_code}.csv")
                
                if os.path.exists(file_path):
                    if file_path.endswith('.parquet'):
                        df_plot = pd.read_parquet(file_path)
                    else:
                        df_plot = pd.read_csv(file_path)
                    
                    fig = go.Figure(data=[go.Candlestick(x=df_plot['日期'],
                                    open=df_plot['开盘价'],
                                    high=df_plot['最高价'],
                                    low=df_plot['最低价'],
                                    close=df_plot['收盘价'])])
                    fig.update_layout(title=f'{selected_stock_code} K线图', yaxis_title='价格 (人民币)', xaxis_rangeslider_visible=True)
                    st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("没有股票符合筛选条件。")
    else:
        st.info("请点击 '运行选股策略' 按钮来生成推荐。")

elif page == "Data Browser":
    st.title("股票数据概览")
    
    if not os.path.exists(DATA_DIR):
        st.error(f"数据目录未找到: {DATA_DIR}")
    else:
        # 支持查看 csv 和 parquet 文件
        files = [f for f in os.listdir(DATA_DIR) if f.endswith(('.csv', '.parquet'))]
        if not files:
            st.info("在 data/raw_data/ 目录下未找到股票数据文件。")
        else:
            selected_file = st.selectbox("选择一个股票文件", sorted(files))
            file_path = os.path.join(DATA_DIR, selected_file)
            
            if file_path.endswith('.parquet'):
                df = pd.read_parquet(file_path)
            else:
                df = pd.read_csv(file_path)
            
            # 列名汉化转换映射
            browser_col_mapping = {
                'preclose': '昨收价',
                'pctChg': '涨跌幅',
                'code': '代码',
                'date': '日期',
                'open': '开盘价',
                'close': '收盘价',
                'high': '最高价',
                'low': '最低价',
                'volume': '成交量',
                'amount': '成交额',
                'turn': '换手率'
            }
            # 仅重命名存在的列
            existing_browser_mapping = {k: v for k, v in browser_col_mapping.items() if k in df.columns and v not in df.columns}
            if existing_browser_mapping:
                df.rename(columns=existing_browser_mapping, inplace=True)

            # 尝试获取本地缓存的市值信息
            try:
                basics_path = os.path.join(os.path.dirname(__file__), 'data', 'stock_basics.parquet')
                if os.path.exists(basics_path):
                    basics_df = pd.read_parquet(basics_path)
                    
                    # 获取股票核心6位代码
                    stock_code_raw = selected_file.split('.')[0]
                    if len(stock_code_raw) > 6:
                        stock_code_6 = stock_code_raw[-6:]
                    else:
                        stock_code_6 = stock_code_raw
                    
                    stock_info = basics_df[basics_df['代码'] == stock_code_6]
                    if not stock_info.empty:
                        market_cap = stock_info['总市值'].values[0]
                        st.metric("最新总市值", f"{market_cap/1e8:.2f} 亿元")
            except Exception as e:
                pass

            st.subheader(f"数据预览: {selected_file}")
            # 按日期倒序排序，让最新数据显示在前面
            if '日期' in df.columns:
                df = df.sort_values('日期', ascending=False)
            elif 'date' in df.columns:
                df = df.sort_values('date', ascending=False)
            # 显示全部数据并支持滚动
            st.dataframe(df, use_container_width=True)
            
            st.subheader("K线图")
            # Create Plotly K-line chart
            fig = go.Figure(data=[go.Candlestick(x=df['日期'],
                            open=df['开盘价'],
                            high=df['最高价'],
                            low=df['最低价'],
                            close=df['收盘价'])])
            
            fig.update_layout(
                title=f'{selected_file} K线图',
                yaxis_title='价格 (人民币)',
                xaxis_title='日期',
                xaxis_rangeslider_visible=True
            )
            st.plotly_chart(fig, use_container_width=True)

elif page == "Configuration":
    st.title("策略超参数配置")
    config = load_config()
    
    with st.form("config_form"):
        # Scheduler Configuration
        st.header("定时任务设置")
        col1, col2 = st.columns(2)
        with col1:
            config['scheduler']['daily_run_time'] = st.text_input("每日运行时间 (HH:MM)", config['scheduler'].get('daily_run_time', '20:00'))
        with col2:
            config['scheduler']['log_level'] = st.selectbox("日志级别", ["DEBUG", "INFO", "WARNING", "ERROR"], index=["DEBUG", "INFO", "WARNING", "ERROR"].index(config['scheduler'].get('log_level', 'INFO')))
        
        st.subheader("通知设置")
        col_notify1, col_notify2 = st.columns(2)
        with col_notify1:
            config['scheduler']['feishu_webhook_url'] = st.text_input("飞书 Webhook URL", value=config['scheduler'].get('feishu_webhook_url', ''))
        with col_notify2:
            config['scheduler']['dingtalk_webhook_url'] = st.text_input("钉钉 Webhook URL", value=config['scheduler'].get('dingtalk_webhook_url', ''))
        
        # Data Fetch Configuration
        st.header("数据抓取设置")
        col3, col4 = st.columns(2)
        with col3:
            config['data_fetch']['primary_source'] = st.selectbox("主数据源", ["akshare", "baostock", "tushare"], index=["akshare", "baostock", "tushare"].index(config['data_fetch'].get('primary_source', 'akshare')))
            config['data_fetch']['incremental_update'] = st.checkbox("启用增量更新", config['data_fetch'].get('incremental_update', True))
            config['data_fetch']['include_gem_stocks'] = st.checkbox("包含创业板", config['data_fetch'].get('include_gem_stocks', True))
        with col4:
            config['data_fetch']['backup_source'] = st.selectbox("备用数据源", ["akshare", "baostock", "tushare"], index=["akshare", "baostock", "tushare"].index(config['data_fetch'].get('backup_source', 'baostock')))
            config['data_fetch']['max_retries'] = st.number_input("最大重试次数", value=config['data_fetch'].get('max_retries', 5))
            config['data_fetch']['include_sci_tech_board'] = st.checkbox("包含科创板", config['data_fetch'].get('include_sci_tech_board', True))
        
        # Data Processor Configuration
        st.header("数据处理设置")
        col5, col6 = st.columns(2)
        with col5:
            config['data_processor']['price_data_days'] = st.number_input("价格数据保留天数", value=config['data_processor'].get('price_data_days', 180))
            config['data_processor']['limit_up_threshold'] = st.number_input("涨停阈值 (%)", value=float(config['data_processor'].get('limit_up_threshold', 9.8)))
            config['data_processor']['filter_st_stocks'] = st.checkbox("过滤 ST 股票", config['data_processor'].get('filter_st_stocks', True))
        with col6:
            config['data_processor']['price_change_period'] = st.number_input("价格变化统计周期 (天)", value=config['data_processor'].get('price_change_period', 90))
            config['data_processor']['parallel_workers'] = st.number_input("并行工作线程数", value=config['data_processor'].get('parallel_workers', 5))
            config['data_processor']['filter_suspended_stocks'] = st.checkbox("过滤停牌股票", config['data_processor'].get('filter_suspended_stocks', True))

        # Strategy Configuration
        st.header("选股策略筛选参数")
        col7, col8 = st.columns(2)
        with col7:
            # Price Range Options
            price_options = [10.0, 20.0, 30.0, 50.0, 100.0]
            current_max_price = float(config['strategy']['stock_selection'].get('max_price', 20.0))
            if current_max_price not in price_options:
                price_options.append(current_max_price)
                price_options.sort()
            config['strategy']['stock_selection']['max_price'] = st.selectbox("最高价格 (人民币)", options=price_options, index=price_options.index(current_max_price))
            
            min_price_options = [0.0, 5.0, 10.0, 15.0, 20.0]
            current_min_price = float(config['strategy']['stock_selection'].get('min_price', 10.0))
            if current_min_price not in min_price_options:
                min_price_options.append(current_min_price)
                min_price_options.sort()
            config['strategy']['stock_selection']['min_price'] = st.selectbox("最低价格 (人民币)", options=min_price_options, index=min_price_options.index(current_min_price))
            
            # Market Cap Options
            cap_options = [50.0, 100.0, 200.0, 500.0, 1000.0]
            current_cap = float(config['strategy']['stock_selection'].get('max_market_cap', 500.0))
            if current_cap not in cap_options:
                cap_options.append(current_cap)
                cap_options.sort()
            config['strategy']['stock_selection']['max_market_cap'] = st.selectbox("最高总市值 (亿元)", options=cap_options, index=cap_options.index(current_cap))
            
        with col8:
            # Limit Up Count Options
            count_options = [1, 2, 3, 5, 10]
            current_min_count = int(config['strategy']['stock_selection'].get('min_limit_up_count', 2))
            if current_min_count not in count_options:
                count_options.append(current_min_count)
                count_options.sort()
            config['strategy']['stock_selection']['min_limit_up_count'] = st.selectbox("最小涨停次数", options=count_options, index=count_options.index(current_min_count))
            
            current_max_count = int(config['strategy']['stock_selection'].get('max_limit_up_count', 5))
            if current_max_count not in count_options:
                count_options.append(current_max_count)
                count_options.sort()
            config['strategy']['stock_selection']['max_limit_up_count'] = st.selectbox("最大涨停次数", options=count_options, index=count_options.index(current_max_count))
            
            config['strategy']['stock_selection']['limit_up_period'] = st.number_input("涨停统计周期 (天)", value=int(config['strategy']['stock_selection'].get('limit_up_period', 20)))
            config['strategy']['stock_selection']['require_profit'] = st.checkbox("要求盈利 (Require Profit)", config['strategy']['stock_selection'].get('require_profit', True))
        
        submitted = st.form_submit_button("保存配置")
        if submitted:
            save_config(config)
            st.success("配置保存成功！")

elif page == "Service Management":
    st.title("Service Management")
    
    status, pid = get_service_status()
    
    col1, col2 = st.columns(2)
    
    with col1:
        if status:
            st.success(f"Service is Running (PID: {pid})")
            if st.button("Stop Service"):
                if stop_service():
                    st.rerun()
        else:
            st.warning("Service is Stopped")
            if st.button("Start Service"):
                new_pid = start_service()
                st.success(f"Service started with PID: {new_pid}")
                st.rerun()
    
    with col2:
        st.subheader("Recent Logs")
        log_file = os.path.join(LOGS_DIR, 'scheduler.log')
        if os.path.exists(log_file):
            with open(log_file, 'r') as f:
                # Show last 20 lines
                lines = f.readlines()
                st.code("".join(lines[-20:]))
        else:
            st.info("No log file found.")

elif page == "Backtest Analysis":
    st.title("回测分析")
    
    from src.backtester import Backtester
    from src.strategy import FlexStrategy
    from src.data_processor import DataProcessor
    
    config = load_config()
    
    st.subheader("回测参数设置")

    recommended_stocks = []
    if 'stock_selection_results' in st.session_state and st.session_state['stock_selection_results']:
        results_df = pd.DataFrame(st.session_state['stock_selection_results']).head(50)
        recommended_stocks = results_df['code'].tolist()
        st.info(f"将对以下 {len(recommended_stocks)} 只推荐股票进行回测: {', '.join(recommended_stocks)}")
    else:
        st.warning("请先在 '选股生成排序' 页面运行选股策略以获取推荐股票。")
    
    with st.form("backtest_params_form"):
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("回测开始日期", value=datetime.now() - timedelta(days=365))
            initial_capital = st.number_input("初始资金", value=config['backtester'].get('initial_capital', 1000000), min_value=10000)
        with col2:
            end_date = st.date_input("回测结束日期", value=datetime.now())
            max_stocks = st.number_input("最大持仓股票数量", value=config['backtester'].get('max_stocks', 5), min_value=1, max_value=100)
        
        submitted = st.form_submit_button("运行回测")
        
        if submitted:
            if not recommended_stocks:
                st.warning("没有推荐股票可用于回测。请先在 '选股生成排序' 页面运行选股策略。")
            else:
                with st.spinner("正在运行回测..."):
                    processor = DataProcessor(config=config)
                    strategy_instance = FlexStrategy(data_processor=processor, config=config)
                    
                    backtester = Backtester(
                        start_date=start_date.strftime('%Y-%m-%d'),
                        end_date=end_date.strftime('%Y-%m-%d'),
                        initial_capital=float(initial_capital),
                        max_stocks=int(max_stocks),
                        strategy=strategy_instance,
                        data_processor=processor
                    )
                    
                    backtest_results = backtester.run_backtest(stock_codes=recommended_stocks)
                    
                    if backtest_results:
                        st.session_state['backtest_results'] = backtest_results
                        st.session_state['backtest_portfolio_history'] = backtester.portfolio_history
                        st.session_state['backtest_transactions'] = backtester.transactions
                        st.success("回测运行成功！")
                    else:
                        st.error("回测运行失败，请检查日志。")
    
    # Display backtest results if available in session state
    if 'backtest_results' in st.session_state and st.session_state['backtest_results']:
        results = st.session_state['backtest_results']
        portfolio_history = st.session_state['backtest_portfolio_history']
        transactions = st.session_state['backtest_transactions']
        
        st.subheader("回测结果概览")
        col1, col2, col3 = st.columns(3)
        col1.metric("总收益率", f"{results['total_return']*100:.2f}%")
        col2.metric("年化收益率", f"{results['annual_return']*100:.2f}%")
        col3.metric("夏普比率", f"{results['sharpe_ratio']:.2f}")
        
        col4, col5, col6 = st.columns(3)
        col4.metric("最大回撤", f"{results['max_drawdown']*100:.2f}%")
        col5.metric("交易次数", f"{results['num_trades']}")
        col6.metric("胜率", f"{results['win_rate']*100:.2f}%")

        st.subheader("资金曲线")
        if not portfolio_history.empty:
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=portfolio_history['date'], y=portfolio_history['total_value'], mode='lines', name='总资产'))
            fig.update_layout(title='总资产随时间变化', xaxis_title='日期', yaxis_title='总资产 (¥)')
            st.plotly_chart(fig, use_container_width=True)
        
        st.subheader("交易记录")
        if transactions:
            transactions_df = pd.DataFrame(transactions)
            st.dataframe(transactions_df, use_container_width=True)
        else:
            st.info("没有交易记录。")
