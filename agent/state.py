from typing import Annotated, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    intent: str
    lead_name: str | None
    lead_email: str | None
    lead_platform: str | None
    lead_captured: bool
    collecting_lead: bool  # Flag: once high_intent triggers, stay in lead_collect until captured

