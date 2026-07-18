import streamlit as st
import pandas as pd
import os
import re
from agent import run_agent
from langchain_core.messages import HumanMessage, AIMessage
from langchain_community.chat_models import ChatTongyi
import PyPDF2
import docx
from datetime import datetime

st.set_page_config(page_title="QueryX", layout="wide")
st.title("📊 QueryX - 用提问探索数据的无限可能")

# ========== 初始化会话状态 ==========
if "df" not in st.session_state:
    st.session_state.df = None
if "messages" not in st.session_state:
    st.session_state.messages = []
if "chat_history_langchain" not in st.session_state:
    st.session_state.chat_history_langchain = []
if "doc_text" not in st.session_state:
    st.session_state.doc_text = ""
if "archived_conversations" not in st.session_state:
    st.session_state.archived_conversations = []
if "current_archive_index" not in st.session_state:
    st.session_state.current_archive_index = None
if "pending_prompt" not in st.session_state:
    st.session_state.pending_prompt = None

# ========== 辅助函数 ==========
def extract_text_from_file(uploaded_file):
    file_type = uploaded_file.name.split(".")[-1].lower()
    if file_type == "txt":
        return uploaded_file.getvalue().decode("utf-8")
    elif file_type == "pdf":
        pdf_reader = PyPDF2.PdfReader(uploaded_file)
        text = ""
        for page in pdf_reader.pages:
            extracted = page.extract_text()
            if extracted:
                text += extracted + "\n"
        return text
    elif file_type == "docx":
        doc = docx.Document(uploaded_file)
        return "\n".join([para.text for para in doc.paragraphs])
    else:
        return None

def generate_title(question, answer):
    """用 AI 根据问答生成简短标题（不超过15字）"""
    try:
        title_llm = ChatTongyi(model="qwen-plus", temperature=0)
        prompt = f"根据以下对话内容，生成一个不超过15个字的简短标题，直接输出标题，不要加引号：\n用户：{question[:200]}\n助手：{answer[:200]}"
        title = title_llm.invoke(prompt).content.strip()
        if len(title) > 20:
            title = title[:18] + "..."
        return title
    except:
        return question[:15] + "..."

# ========== 侧边栏（会话管理）==========
with st.sidebar:
    st.header("📁 会话管理")

    # 开启新对话 -> 重置消息和文件
    if st.button("＋ 开启新对话", use_container_width=True):
        # 如果当前对话有内容，先存档
        if st.session_state.current_archive_index is not None and st.session_state.messages:
            idx = st.session_state.current_archive_index
            # 存档当前对话的 messages、chat_history、df、doc_text
            st.session_state.archived_conversations[idx]["messages"] = st.session_state.messages.copy()
            st.session_state.archived_conversations[idx]["chat_history"] = st.session_state.chat_history_langchain.copy()
            st.session_state.archived_conversations[idx]["time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            st.session_state.archived_conversations[idx]["df"] = st.session_state.df
            st.session_state.archived_conversations[idx]["doc_text"] = st.session_state.doc_text
            # 移动到最后
            archive = st.session_state.archived_conversations.pop(idx)
            st.session_state.archived_conversations.append(archive)
            # 生成标题
            if archive["title"] == "新对话":
                first_user = archive["messages"][0]["content"] if archive["messages"] else ""
                first_assistant = archive["messages"][1]["content"] if len(archive["messages"]) > 1 else ""
                archive["title"] = generate_title(first_user, first_assistant) if first_assistant else first_user[:20]

        # 清空当前对话状态（消息 + 文件）
        st.session_state.messages = []
        st.session_state.chat_history_langchain = []
        st.session_state.df = None
        st.session_state.doc_text = ""
        st.session_state.current_archive_index = None
        st.session_state.pending_prompt = None
        st.rerun()

    # 导出当前对话
    if st.session_state.messages:
        chat_md = ""
        for msg in st.session_state.messages:
            if msg["role"] == "user":
                chat_md += f"**用户**: {msg['content']}\n\n"
            else:
                chat_md += f"**助手**: {msg['content']}\n\n"
        st.download_button(
            label="📥 导出当前对话",
            data=chat_md,
            file_name="queryx_report.md",
            mime="text/markdown",
            use_container_width=True
        )

    st.divider()
    st.subheader("📦 已存档的对话")
    if st.session_state.archived_conversations:
        sorted_archives = sorted(
            enumerate(st.session_state.archived_conversations),
            key=lambda x: x[1]["time"],
            reverse=True
        )
        for original_idx, archive in sorted_archives:
            is_active = (st.session_state.current_archive_index == original_idx)
            title_display = archive["title"]
            if is_active:
                title_display = "🔵 " + title_display
            with st.container():
                st.markdown(f"**{title_display}**")
                st.caption(archive["time"])
                col1, col2 = st.columns([2, 1])
                with col1:
                    if st.button("💬 继续对话", key=f"continue_{original_idx}"):
                        # 加载存档内容
                        st.session_state.messages = archive["messages"].copy()
                        st.session_state.chat_history_langchain = archive["chat_history"].copy()
                        # ★ 恢复该对话当时的文件
                        st.session_state.df = archive.get("df", None)
                        st.session_state.doc_text = archive.get("doc_text", "")
                        st.session_state.current_archive_index = original_idx
                        st.session_state.pending_prompt = None
                        st.rerun()
                with col2:
                    if st.button("🗑️", key=f"del_{original_idx}"):
                        if st.session_state.current_archive_index == original_idx:
                            st.session_state.current_archive_index = None
                        st.session_state.archived_conversations.pop(original_idx)
                        st.rerun()
    else:
        st.caption("暂无存档的对话")

# ========== 主界面 ==========
st.header("💬 对话分析")

# ----- 文件上传区（放在消息列表上方）-----
uploaded_file = st.file_uploader(
    "",
    type=["csv", "pdf", "txt", "docx"],
    help="上传的文件将仅用于当前对话，切换对话时自动保留"
)

if uploaded_file is not None:
    file_type = uploaded_file.name.split(".")[-1].lower()
    if file_type == "csv":
        st.session_state.df = pd.read_csv(uploaded_file)
        st.session_state.doc_text = ""
        st.success(f"✅ 已加载表格：{uploaded_file.name}")
        st.caption(f"📊 {len(st.session_state.df)} 行 × {len(st.session_state.df.columns)} 列")
        with st.expander("🔍 预览数据（前10行）"):
            st.dataframe(st.session_state.df.head(10))
    elif file_type in ["pdf", "txt", "docx"]:
        extracted = extract_text_from_file(uploaded_file)
        if extracted:
            st.session_state.doc_text = extracted
            st.session_state.df = None
            st.success(f"✅ 已加载文档：{uploaded_file.name}（{len(extracted)} 字符）")
            with st.expander("📄 预览文档（前1000字）"):
                st.text(extracted[:1000])
        else:
            st.error("❌ 无法提取文本内容")
    else:
        st.warning("暂不支持此文件格式")

# 如果已加载文件但未显示预览（比如从存档加载），显示简要状态
elif st.session_state.df is not None:
    st.success(f"📊 当前数据表：{len(st.session_state.df)} 行 × {len(st.session_state.df.columns)} 列")
    with st.expander("🔍 预览数据（前10行）"):
        st.dataframe(st.session_state.df.head(10))
elif st.session_state.doc_text:
    st.success(f"📄 已加载文档（{len(st.session_state.doc_text)} 字符）")
    with st.expander("📄 预览文档（前1000字）"):
        st.text(st.session_state.doc_text[:1000])

# ----- 显示当前对话消息 -----
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        content = msg["content"]
        if "```python" in content:
            parts = re.split(r'(```python.*?```)', content, flags=re.DOTALL)
            for part in parts:
                if part.startswith("```python"):
                    code = part.replace("```python", "").replace("```", "").strip()
                    with st.expander("🔍 查看分析代码"):
                        st.code(code, language="python")
                else:
                    st.markdown(part)
        else:
            st.markdown(content)
        if msg.get("has_image"):
            if os.path.exists("output.png"):
                st.image("output.png", caption="生成的图表", use_container_width=True)

# ----- 处理 pending_prompt -----
if st.session_state.pending_prompt is not None:
    prompt = st.session_state.pending_prompt
    st.session_state.pending_prompt = None

    history_with_current = st.session_state.chat_history_langchain + [HumanMessage(content=prompt)]

    if os.path.exists("output.png"):
        os.remove("output.png")

    final_input = prompt
    if st.session_state.doc_text:
        context = st.session_state.doc_text[:5000]
        final_input = f"以下是一份文档的文本内容：\n---\n{context}\n---\n用户问题：{prompt}\n请根据文档内容回答。"

    with st.spinner("🤔 Agent 正在分析..."):
        try:
            response = run_agent(
                user_input=final_input,
                dataframe=st.session_state.df,
                chat_history=history_with_current
            )
        except Exception as e:
            response = f"❌ 出错了：{str(e)}"

    st.session_state.chat_history_langchain.append(HumanMessage(content=prompt))
    st.session_state.chat_history_langchain.append(AIMessage(content=response))

    has_image = os.path.exists("output.png")

    st.session_state.messages.append({
        "role": "assistant",
        "content": response,
        "has_image": has_image
    })

    # 如果当前对话有存档索引，更新存档（包括文件）
    if st.session_state.current_archive_index is not None:
        idx = st.session_state.current_archive_index
        archive = st.session_state.archived_conversations[idx]
        archive["messages"] = st.session_state.messages.copy()
        archive["chat_history"] = st.session_state.chat_history_langchain.copy()
        archive["time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        # ★ 更新文件到存档
        archive["df"] = st.session_state.df
        archive["doc_text"] = st.session_state.doc_text
        if archive["title"] == "新对话":
            first_user = archive["messages"][0]["content"] if archive["messages"] else ""
            first_assistant = archive["messages"][1]["content"] if len(archive["messages"]) > 1 else ""
            archive["title"] = generate_title(first_user, first_assistant) if first_assistant else first_user[:20]
        # 移动到最后
        st.session_state.archived_conversations.pop(idx)
        st.session_state.archived_conversations.append(archive)
        st.session_state.current_archive_index = len(st.session_state.archived_conversations) - 1

    st.rerun()

# ----- 聊天输入框 -----
if prompt := st.chat_input("给QueryX发送消息"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.session_state.pending_prompt = prompt

    # 如果当前对话没有存档索引，则自动创建一个新存档
    if st.session_state.current_archive_index is None:
        new_archive = {
            "title": "新对话",
            "messages": [],
            "chat_history": [],
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "df": None,      # 新对话开始时文件为空
            "doc_text": ""
        }
        st.session_state.archived_conversations.append(new_archive)
        st.session_state.current_archive_index = len(st.session_state.archived_conversations) - 1

    st.rerun()