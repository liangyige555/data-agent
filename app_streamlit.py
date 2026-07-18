import streamlit as st
import pandas as pd
import os
from agent import run_agent

st.set_page_config(page_title="数据分析智能Agent", layout="wide")
st.title("📊 数据分析智能Agent")

# 初始化会话状态
if "df" not in st.session_state:
    st.session_state.df = None
if "messages" not in st.session_state:
    st.session_state.messages = []

# 侧边栏：上传文件
with st.sidebar:
    st.header("1. 上传数据")
    uploaded_file = st.file_uploader("选择CSV文件", type="csv")
    if uploaded_file:
        st.session_state.df = pd.read_csv(uploaded_file)
        st.success(f"已加载 {len(st.session_state.df)} 行 × {len(st.session_state.df.columns)} 列")
        st.write("列名：", list(st.session_state.df.columns))
        # 预览数据
        st.dataframe(st.session_state.df.head())

# 主界面：对话
st.header("2. 对话分析")

# 显示历史消息
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# 输入框
if prompt := st.chat_input("输入你的分析需求，比如“销售额最高的是哪一天？”"):
    # 显示用户消息
    st.chat_message("user").markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    # 调用Agent
    with st.spinner("Agent 正在分析中..."):
        response = run_agent(prompt, dataframe=st.session_state.df)

    # 显示Agent回复
    with st.chat_message("assistant"):
        st.markdown(response)
        # 如果有图片，显示图片
        img_path = "output.png"
        if os.path.exists(img_path):
            st.image(img_path, caption="生成的图表", use_container_width=True)

    st.session_state.messages.append({"role": "assistant", "content": response})