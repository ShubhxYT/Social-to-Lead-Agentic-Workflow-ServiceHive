import os

import streamlit as st
from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage

load_dotenv()

from agent.graph import build_graph
from agent.state import AgentState

st.set_page_config(page_title="AutoStream Assistant", page_icon="🎬", layout="centered")
st.title("🎬 AutoStream AI Assistant")
st.caption("Ask me about pricing, features, or get started with the Pro plan!")

# Guard: ensure knowledge base is ingested
if not os.path.exists("chroma_db"):
    st.error(
        "Knowledge base not found. "
        "Run `python knowledge_base/ingest.py` from the project root first, then restart."
    )
    st.stop()

# ── Initialise session state ──────────────────────────────────────────────────

if "agent_state" not in st.session_state:
    st.session_state.agent_state: AgentState = {
        "messages": [],
        "intent": "",
        "lead_name": None,
        "lead_email": None,
        "lead_platform": None,
        "lead_captured": False,
        "collecting_lead": False,
    }

if "graph" not in st.session_state:
    with st.spinner("Loading agent..."):
        st.session_state.graph = build_graph()

# ── Lead captured banner ──────────────────────────────────────────────────────

if st.session_state.agent_state.get("lead_captured"):
    st.success(
        "🎉 **Lead Captured!** Our team will be in touch with "
        f"{st.session_state.agent_state.get('lead_name', 'you')} soon."
    )

# ── Render conversation history ───────────────────────────────────────────────

for msg in st.session_state.agent_state["messages"]:
    role = "user" if isinstance(msg, HumanMessage) else "assistant"
    with st.chat_message(role):
        st.markdown(msg.content)

# ── Chat input ────────────────────────────────────────────────────────────────

if user_input := st.chat_input("Type your message..."):
    # Show user bubble immediately (before rerun)
    with st.chat_message("user"):
        st.markdown(user_input)

    # Append HumanMessage and invoke graph
    st.session_state.agent_state["messages"].append(HumanMessage(content=user_input))

    with st.spinner("Thinking..."):
        st.session_state.agent_state = st.session_state.graph.invoke(
            st.session_state.agent_state
        )

    # Rerun to render full updated history (prevents double-render of user bubble)
    st.rerun()

