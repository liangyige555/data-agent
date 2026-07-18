# 数据分析智能 Agent

基于大语言模型（通义千问）的智能数据分析系统，用户上传CSV数据后，可直接用自然语言提问，Agent自动编写Python代码进行分析并生成可视化图表。

## 功能演示
（这里放几张你 Streamlit 界面的截图，包括提问和出图的画面）

## 技术栈
- 大模型：通义千问（qwen-plus）
- 框架：LangChain + 手动 Function Calling
- 数据处理：Pandas、Matplotlib
- 前端：Streamlit

## 快速开始
1. 克隆项目
2. 安装依赖：`pip install -r requirements.txt`
3. 在 `.env` 文件中设置 `DASHSCOPE_API_KEY`
4. 运行：`streamlit run app_streamlit.py`