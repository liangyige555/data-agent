import os
import pandas as pd
import matplotlib.pyplot as plt
from dotenv import load_dotenv
from langchain_community.chat_models import ChatTongyi
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from langchain_core.tools import tool
from typing import List
import json
import io
import sys

load_dotenv()

# 全局数据
df_global = None

# 1. 初始化模型
llm = ChatTongyi(model="qwen-plus", temperature=0)

# 2. 定义工具（使用新版 langchain_core.tools）
@tool
def python_repl(code: str) -> str:
    """执行Python代码，处理名为df的DataFrame。
    代码必须用print()输出最终结果，或用plt.savefig('output.png')保存图表。
    """
    global df_global
    if df_global is None:
        return "错误：没有数据，请先上传CSV文件。"

    # 捕获 print 输出
    old_stdout = sys.stdout
    sys.stdout = captured_output = io.StringIO()

    try:
        namespace = {"pd": pd, "plt": plt, "df": df_global}
        exec(code, namespace)

        # 拿回被捕获的输出
        sys.stdout = old_stdout
        printed = captured_output.getvalue()

        if 'plt' in code and 'savefig' in code:
            return f"{printed}图表已生成并保存为 'output.png'"
        if printed.strip():
            return printed.strip()
        return "代码执行完成，但没有产生任何输出。请确保使用 print() 输出结果。"
    except Exception as e:
        sys.stdout = old_stdout  # 出错时也要恢复
        return f"代码执行错误: {str(e)}"




tools = [python_repl]
llm_with_tools = llm.bind_tools(tools)

# 3. 手动 Function Calling 循环
def run_agent(user_input: str, dataframe, chat_history: list = None) -> str:
    global df_global
    df_global = dataframe  # 用传入的数据覆盖全局变量

    messages = []
    if chat_history:
        messages = chat_history.copy()
    else:
        system_prompt = (
            "你是一个数据分析助手，用户已上传一个名为df的DataFrame。"
            "当用户提问时，你必须调用 python_repl 工具执行Python代码来获取答案。"
            "代码要求：用 print() 输出结果，如需绘图请用 plt.savefig('output.png')。"
        )
        messages = [HumanMessage(content=user_input)]
        messages[0] = HumanMessage(content=f"{system_prompt}\n\n用户问题：{user_input}")

    # 后面保持原样...

    max_turns = 5
    for _ in range(max_turns):
        response = llm_with_tools.invoke(messages)
        messages.append(response)

        # 检查是否有工具调用
        if response.tool_calls:
            for tool_call in response.tool_calls:
                tool_name = tool_call['name']
                tool_args = tool_call['args']
                # 执行工具
                if tool_name == 'python_repl':
                    result = python_repl.invoke(tool_args)
                else:
                    result = f"未知工具: {tool_name}"
                # 将工具结果加入消息
                messages.append(ToolMessage(content=result, tool_call_id=tool_call['id']))
        else:
            # 没有工具调用，返回最终文本
            return response.content

    return "抱歉，分析过程超时，请简化您的问题。"

# 这个 executor 变量是为了和 app.py 兼容，保持接口一致
class SimpleExecutor:
    def invoke(self, input_dict):
        user_input = input_dict["input"]
        output = run_agent(user_input)
        return {"output": output}

agent_executor = SimpleExecutor()