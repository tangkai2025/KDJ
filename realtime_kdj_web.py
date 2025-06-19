import streamlit as st
import pandas as pd
import yfinance as yf
from concurrent.futures import ThreadPoolExecutor, as_completed

def stqdm(futures, total=None, desc=None):
    if total is None:
        total = len(futures)
    progress_bar = st.progress(0)
    results = []
    for i, future in enumerate(as_completed(futures)):
        results.append(future.result())
        progress_bar.progress((i + 1) / total)
    progress_bar.empty()
    return results

def calculate_kdj(df, n=9, k_period=3, d_period=3):
    low_list = df['low'].rolling(window=n, min_periods=1).min()
    high_list = df['high'].rolling(window=n, min_periods=1).max()
    rsv = (df['close'] - low_list) / (high_list - low_list) * 100
    df['K'] = rsv.ewm(com=k_period-1, adjust=False).mean()
    df['D'] = df['K'].ewm(com=d_period-1, adjust=False).mean()
    df['J'] = 3 * df['K'] - 2 * df['D']
    return df

@st.cache_data(ttl=3600)
def get_sp500_stocks():
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    df = pd.read_html(url, header=0)[0]
    return df[['Symbol', 'Security']].rename(columns={'Symbol': 'code', 'Security': 'name'})

@st.cache_data(ttl=3600)
def get_nasdaq100_stocks():
    url = "https://en.wikipedia.org/wiki/NASDAQ-100"
    df = pd.read_html(url, header=0)[4]
    return df[['Ticker', 'Company']].rename(columns={'Ticker': 'code', 'Company': 'name'})

@st.cache_data(ttl=1800)
def get_us_kline(code, period, interval):
    try:
        ticker = yf.Ticker(code)
        df = ticker.history(period=period, interval=interval)
        df = df.rename(columns={'Open': 'open', 'High': 'high', 'Low': 'low', 'Close': 'close'})
        return df[['open', 'high', 'low', 'close']]
    except:
        return None

def analyze_stock(code, name, index_name, cycles):
    result = []
    for cycle in cycles:
        level = cycle["level"]
        period = cycle["period"]
        interval = cycle["interval"]

        if level == "季线":
            df = get_us_kline(code, "10y", "1mo")
            if df is not None and len(df) >= 3:
                df_season = df[-3:]
                df_season = calculate_kdj(df_season)
                if df_season['J'].iloc[-1] < 0:
                    result.append({'name': name, 'code': code, 'index': index_name, 'J级别': '季线'})
        elif level == "年线":
            df = get_us_kline(code, "20y", "1mo")
            if df is not None and len(df) >= 12:
                df_year = df[-12:]
                df_year = calculate_kdj(df_year)
                if df_year['J'].iloc[-1] < 0:
                    result.append({'name': name, 'code': code, 'index': index_name, 'J级别': '年线'})
        else:
            df = get_us_kline(code, period, interval)
            if df is not None and len(df) > 10:
                df = calculate_kdj(df)
                if df['J'].iloc[-1] < 0:
                    result.append({'name': name, 'code': code, 'index': index_name, 'J级别': level})
    return result

st.title("美股KDJ J值小于0实时筛选（标普500 & 纳斯达克100，多线程加速）")

cycles = [
    {"level": "日线", "period": "3mo", "interval": "1d"},
    {"level": "周线", "period": "2y", "interval": "1wk"},
    {"level": "月线", "period": "10y", "interval": "1mo"},
    {"level": "季线", "period": "10y", "interval": "3mo"},
    {"level": "年线", "period": "20y", "interval": "1mo"},
]

index_options = ["标普500", "纳斯达克100", "全部"]
index_choice = st.selectbox("选择要分析的指数", index_options)

max_workers = st.slider("线程数（建议8-32，越大越快，视电脑性能）", min_value=4, max_value=32, value=16)

if st.button("开始实时分析"):
    st.info("正在分析，请耐心等待（美股数量较多，建议只选一个指数加快速度）...")
    result = []
    tasks = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        if index_choice in ["标普500", "全部"]:
            sp500 = get_sp500_stocks()
            for idx, row in sp500.iterrows():
                code = row['code']
                name = row['name']
                tasks.append(executor.submit(analyze_stock, code, name, "标普500", cycles))
        if index_choice in ["纳斯达克100", "全部"]:
            nasdaq100 = get_nasdaq100_stocks()
            for idx, row in nasdaq100.iterrows():
                code = row['code']
                name = row['name']
                tasks.append(executor.submit(analyze_stock, code, name, "纳斯达克100", cycles))
        all_results = stqdm(tasks, total=len(tasks))
        for res in all_results:
            if res:
                result.extend(res)

    df_result = pd.DataFrame(result)
    if df_result.empty:
        st.warning("没有筛选出J值小于0的股票。")
        st.stop()

    st.success(f"共筛选出 {len(df_result)} 条记录。")

    # 增加富途牛牛超链接列
    df_result['富途牛牛'] = df_result['code'].apply(
        lambda x: f"[{x}](https://www.futunn.com/stock/{x}-US)"
    )

    # 只显示需要的列
    show_df = df_result[['name', '富途牛牛', 'index', 'J级别']].rename(
        columns={'name': '股票名称', '富途牛牛': '股票代码（可点击）', 'index': '指数', 'J级别': 'J值级别'}
    )

    # 用markdown表格显示超链接
    st.markdown("### 筛选结果")
    st.markdown(show_df.to_markdown(index=False), unsafe_allow_html=True)

    # 导出按钮
        # 导出按钮
    csv = df_result[['name', 'code', 'index', 'J级别']].to_csv(index=False, encoding='utf-8-sig')
    st.download_button(
        label="下载筛选结果CSV",
        data=csv,
        file_name='kdj_j_below_0_result.csv',
        mime='text/csv',
    )

else:
    st.info("点击上方按钮开始实时分析。")