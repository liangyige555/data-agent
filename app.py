import gradio as gr
import pandas as pd
import os
from agent import agent_executor, df_global

def handle_upload(file):
    global df_global
    if file is not None:
        df_global = pd.read_csv(file.name)
        return f"文件上传成功！共 {len(df_global)} 行，{len(df_global.columns)} 列。\n列名：{list(df_global.columns)}"
    return "请上传文件"

# app.py 的 chat 函数里
from agent import run_agent, df_global

def chat(message, history):
    global df_global
    if df_global is None:
        reply = "请先上传CSV文件。"
        img_path = None
    else:
        try:
            result = run_agent(message, dataframe=df_global)  # 直接用 run_agent
            reply = result  # run_agent 直接返回字符串
            img_path = "output.png"
            if not os.path.exists(img_path):
                img_path = None
        except Exception as e:
            reply = f"出错: {str(e)}"
            img_path = None
    # ...

    history.append((message, reply))
    return history, img_path

with gr.Blocks() as demo:
    gr.Markdown("# 数据分析智能Agent")
    with gr.Row():
        file_input = gr.File(label="上传CSV数据")
        upload_status = gr.Textbox(label="状态")
    chatbot = gr.Chatbot(label="对话")  # 去掉了 type 参数
    msg = gr.Textbox(label="输入你的分析需求")
    img_output = gr.Image(label="生成的图表")

    file_input.upload(handle_upload, file_input, upload_status)
    msg.submit(chat, [msg, chatbot], [chatbot, img_output])

if __name__ == "__main__":
    demo.launch()