import streamlit as st
import pandas as pd
import yfinance as yf
import matplotlib.pyplot as plt

# 读取Excel结果
df = pd.read_excel('kdj_j_below_0_multi_20250618.xlsx')  # 替换为你的实际文件名

st.title("KDJ J值为负的美股筛选结果（多周期分组）")

j_levels = df['J级别'].unique().tolist()
tabs = st.tabs(j_levels)

for i, level in enumerate(j_levels):
    with tabs[i]:
        st.subheader(f"{level} J值为负的股票")
        sub_df = df[df['J级别'] == level].reset_index(drop=True)
        if sub_df.empty:
            st.write("本周期无筛选结果")
            continue

        sub_df['显示'] = sub_df['name'] + "（" + sub_df['code'] + "）"
        selected = st.selectbox(
            f"选择要查看K线图的股票（{level}）", 
            sub_df['显示'], 
            key=level
        )

        row = sub_df[sub_df['显示'] == selected].iloc[0]
        code = row['code']
        name = row['name']

        # 富途牛牛K线链接
        futu_url = f"https://www.futunn.com/stock/{code}-US"
        st.markdown(f"**股票名称：** {name}  \n**股票代码：** [{code}]({futu_url}) （点击可跳转富途牛牛K线）")

        # 本地K线图
        st.subheader("本地K线图（近30日）")
        data = yf.download(code, period="2mo", interval="1d")
        if not data.empty:
            fig, ax = plt.subplots(figsize=(10, 4))
            ax.plot(data.index, data['Close'], label='收盘价')
            ax.set_title(f"{name}（{code}）近30日收盘价")
            ax.set_xlabel("日期")
            ax.set_ylabel("价格")
            ax.legend()
            st.pyplot(fig)
        else:
            st.write("未能获取到该股票的K线数据。")