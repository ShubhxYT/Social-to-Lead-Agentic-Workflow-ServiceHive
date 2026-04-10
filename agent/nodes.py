import json
import os

from dotenv import load_dotenv
from langchain_community.vectorstores import Chroma
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_groq import ChatGroq
from langchain_huggingface import HuggingFaceEmbeddings

from agent.state import AgentState
from tools.lead_capture import mock_lead_capture

load_dotenv()

CHROMA_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "chroma_db"
)

# Module-level singletons — initialised once, reused across graph invocations
_llm: ChatGroq | None = None
_retriever = None


def get_llm() -> ChatGroq:
    global _llm
    if _llm is None:
        _llm = ChatGroq(
            model="llama-3.3-70b-versatile",
            temperature=0.0,
        )
    return _llm


def get_retriever():
    global _retriever
    if _retriever is None:
        if not os.path.exists(CHROMA_PATH):
            raise FileNotFoundError(
                f"Chroma DB not found at {CHROMA_PATH}. "
                "Run `python knowledge_base/ingest.py` first."
            )
        embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        vectorstore = Chroma(
            persist_directory=CHROMA_PATH,
            embedding_function=embeddings,
        )
        _retriever = vectorstore.as_retriever(search_kwargs={"k": 3})
    return _retriever


# ─────────────────────────────────────────────
# Node 1: classify_intent
# ─────────────────────────────────────────────

def classify_intent(state: AgentState) -> dict:
    """Classify the latest user message as greeting, inquiry, or high_intent."""
    # If already collecting lead, stay in lead collection mode
    if state.get("collecting_lead", False) and not state.get("lead_captured", False):
        return {"intent": "high_intent"}

    last_msg = state["messages"][-1].content
    llm = get_llm()

    system_prompt = (
        "Classify this user message into EXACTLY ONE of these intent labels:\n"
        '- "greeting": casual hello, small talk, not asking about the product\n'
        '- "inquiry": asking about features, pricing, policies, or how the product works\n'
        '- "high_intent": expressing readiness to buy, sign up, or start a trial\n\n'
        "Respond with ONLY the intent label. No explanation, no punctuation."
    )

    response = llm.invoke(
        [
            SystemMessage(content=system_prompt),
            HumanMessage(content=last_msg),
        ]
    )

    raw = response.content.strip().lower().strip('"').strip("'")
    intent = raw if raw in ("greeting", "inquiry", "high_intent") else "inquiry"
    
    # If classified as high_intent, set collecting_lead flag
    updates = {"intent": intent}
    if intent == "high_intent":
        updates["collecting_lead"] = True
    
    return updates



# ─────────────────────────────────────────────
# Node 2: rag_respond
# ─────────────────────────────────────────────

def rag_respond(state: AgentState) -> dict:
    """Answer product/pricing questions using RAG retrieval from Chroma."""
    last_msg = state["messages"][-1].content
    llm = get_llm()
    retriever = get_retriever()

    retrieved_docs = retriever.invoke(last_msg)
    context = "\n\n".join([doc.page_content for doc in retrieved_docs])

    system_prompt = (
        "You are AutoStream's friendly AI assistant. Answer the user's question accurately "
        "using only the context provided below. If the answer is not covered by the context, "
        "say so honestly and suggest contacting support at support@autostream.io.\n\n"
        f"Context:\n{context}"
    )

    # Include full conversation history for follow-up coherence
    history = list(state["messages"][:-1])
    messages_to_send = (
        [SystemMessage(content=system_prompt)]
        + history
        + [HumanMessage(content=last_msg)]
    )

    response = llm.invoke(messages_to_send)
    return {"messages": [AIMessage(content=response.content)]}


# ─────────────────────────────────────────────
# Node 3: lead_collect
# ─────────────────────────────────────────────

def lead_collect(state: AgentState) -> dict:
    """Extract lead info from the conversation and ask for the next missing field."""
    llm = get_llm()
    updates: dict = {}

    # Build conversation text for extraction
    conv_lines = []
    for m in state["messages"]:
        role = "User" if isinstance(m, HumanMessage) else "Assistant"
        conv_lines.append(f"{role}: {m.content}")
    conv_text = "\n".join(conv_lines)

    extraction_prompt = (
        "From this conversation, extract lead information the user has provided.\n\n"
        f"Conversation:\n{conv_text}\n\n"
        "Already known:\n"
        f"- name: {state.get('lead_name') or 'unknown'}\n"
        f"- email: {state.get('lead_email') or 'unknown'}\n"
        f"- platform: {state.get('lead_platform') or 'unknown'}\n\n"
        "Platform means the CREATOR PLATFORM they use (e.g., YouTube, TikTok, Instagram, Twitch, etc.). "
        "It is NOT the product name (AutoStream). Extract only NEW information not already known. "
        'Respond with ONLY a JSON object: {"name": "...", "email": "...", "platform": "..."}\n'
        "Use null for fields you could not find. Do not wrap in markdown code fences."
    )

    try:
        extraction_response = llm.invoke([HumanMessage(content=extraction_prompt)])
        raw_json = extraction_response.content.strip()
        # Strip markdown code fences if the model adds them anyway
        if raw_json.startswith("```"):
            raw_json = raw_json.split("```")[1]
            if raw_json.startswith("json"):
                raw_json = raw_json[4:]
        extracted = json.loads(raw_json.strip())

        if extracted.get("name") and not state.get("lead_name"):
            updates["lead_name"] = extracted["name"]
        if extracted.get("email") and not state.get("lead_email"):
            updates["lead_email"] = extracted["email"]
        if extracted.get("platform") and not state.get("lead_platform"):
            updates["lead_platform"] = extracted["platform"]
    except (json.JSONDecodeError, Exception):
        pass  # Extraction failed — continue without updates, ask again

    # Determine current totals after this turn's updates
    current_name = updates.get("lead_name") or state.get("lead_name")
    current_email = updates.get("lead_email") or state.get("lead_email")
    current_platform = updates.get("lead_platform") or state.get("lead_platform")

    if not current_name:
        ask_msg = (
            "I'd love to get you started with AutoStream! "
            "Could you share your full name?"
        )
    elif not current_email:
        ask_msg = (
            f"Great, {current_name}! "
            "What's your email address so we can set up your account?"
        )
    elif not current_platform:
        ask_msg = (
            "Almost there! Which platform do you primarily create content on? "
            "(e.g., YouTube, Instagram, TikTok)"
        )
    else:
        # All fields collected — capture_lead node will send the confirmation
        return updates

    updates["messages"] = [AIMessage(content=ask_msg)]
    return updates


# ─────────────────────────────────────────────
# Node 4: capture_lead
# ─────────────────────────────────────────────

def capture_lead(state: AgentState) -> dict:
    """Call mock_lead_capture and send confirmation to the user."""
    name = state["lead_name"]
    email = state["lead_email"]
    platform = state["lead_platform"]

    mock_lead_capture(name, email, platform)

    confirmation = (
        f"You're all set, {name}! We've registered your interest in AutoStream Pro. "
        f"Our team will reach out to {email} shortly. "
        f"We can't wait to help you supercharge your {platform} content! 🎬"
    )
    return {
        "lead_captured": True,
        "messages": [AIMessage(content=confirmation)],
    }
