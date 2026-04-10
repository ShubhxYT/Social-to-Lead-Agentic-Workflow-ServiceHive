from langgraph.graph import END, START, StateGraph

from agent.nodes import capture_lead, classify_intent, lead_collect, rag_respond
from agent.state import AgentState


def route_by_intent(state: AgentState) -> str:
    """Route after classify_intent based on detected intent."""
    intent = state.get("intent", "inquiry")
    if intent == "high_intent":
        return "lead_collect"
    return "rag_respond"


def route_after_lead_collect(state: AgentState) -> str:
    """Route after lead_collect — capture when all fields are present."""
    if (
        state.get("lead_name")
        and state.get("lead_email")
        and state.get("lead_platform")
    ):
        return "capture_lead"
    return END


def build_graph():
    """Compile and return the AutoStream agent graph."""
    builder = StateGraph(AgentState)

    builder.add_node("classify_intent", classify_intent)
    builder.add_node("rag_respond", rag_respond)
    builder.add_node("lead_collect", lead_collect)
    builder.add_node("capture_lead", capture_lead)

    builder.add_edge(START, "classify_intent")

    builder.add_conditional_edges(
        "classify_intent",
        route_by_intent,
        {
            "rag_respond": "rag_respond",
            "lead_collect": "lead_collect",
        },
    )

    builder.add_edge("rag_respond", END)

    builder.add_conditional_edges(
        "lead_collect",
        route_after_lead_collect,
        {
            "capture_lead": "capture_lead",
            END: END,
        },
    )

    builder.add_edge("capture_lead", END)

    return builder.compile()
