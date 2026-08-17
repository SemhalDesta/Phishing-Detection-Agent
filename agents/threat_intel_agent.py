"""
Agent 2: Threat Intelligence Agent.
Reasons over the domain/sender using external tools -- WHOIS, VirusTotal,
SPF/DKIM -- deciding for itself which are actually needed. Internally
follows the same ReAct loop structure as the original single-agent system.
"""
from typing import Annotated, TypedDict

from pydantic import BaseModel, Field
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages

from config import GOOGLE_API_KEY, LLM_MODEL, MAX_REACT_STEPS
from tools.whois_lookup import check_domain_age
from tools.virus_total import check_domain_reputation
from tools.header_check import check_spf_dkim

TOOLS = [check_domain_age, check_domain_reputation, check_spf_dkim]
TOOLS_BY_NAME = {t.name: t for t in TOOLS}

THREAT_INTEL_PROMPT = """You are the Threat Intelligence Agent in a multi-agent \
phishing detection system. Your job is to investigate the sender's domain \
using external verification tools -- domain age (WHOIS), domain reputation \
(VirusTotal), and email authentication (SPF/DKIM).

Only call a tool if it's likely to add real evidence -- for example, skip \
WHOIS if the domain is obviously a major, long-established company. Reason \
step by step before each tool call. Once you have enough evidence, stop \
calling tools and summarize your findings in plain text.

Sender domain: {domain}
Authentication-Results header (if available): {auth_header}
"""


class ThreatIntelAssessment(BaseModel):
    risk_score: int = Field(description="0-100 risk score based on threat intelligence findings")
    reasoning: str = Field(description="Summary of what the tools found and how it informs the score")
    tools_used: list[str] = Field(default_factory=list, description="Names of tools actually called")


class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    step_count: int


def _build_llm():
    llm = ChatGoogleGenerativeAI(model=LLM_MODEL, google_api_key=GOOGLE_API_KEY)
    return llm.bind_tools(TOOLS)


def reason_node(state: AgentState) -> dict:
    llm = _build_llm()
    response = llm.invoke(state["messages"])
    return {"messages": [response], "step_count": state["step_count"] + 1}


def execute_tool_node(state: AgentState) -> dict:
    last_message: AIMessage = state["messages"][-1]
    tool_messages = []
    for tool_call in last_message.tool_calls:
        tool_fn = TOOLS_BY_NAME.get(tool_call["name"])
        result = tool_fn.invoke(tool_call["args"]) if tool_fn else f"Unknown tool: {tool_call['name']}"
        tool_messages.append(ToolMessage(content=str(result), tool_call_id=tool_call["id"]))
    return {"messages": tool_messages}


def should_continue(state: AgentState) -> str:
    last_message = state["messages"][-1]
    wants_tool = isinstance(last_message, AIMessage) and last_message.tool_calls
    if state["step_count"] >= MAX_REACT_STEPS:
        return "end"
    return "continue" if wants_tool else "end"


def build_graph():
    graph = StateGraph(AgentState)
    graph.add_node("reason", reason_node)
    graph.add_node("execute_tool", execute_tool_node)
    graph.set_entry_point("reason")
    graph.add_conditional_edges("reason", should_continue, {"continue": "execute_tool", "end": END})
    graph.add_edge("execute_tool", "reason")
    return graph.compile()

def _content_to_string(content) -> str:
    """Normalizes message content -- some providers/messages return a list
    of content blocks instead of a plain string."""
    if isinstance(content, list):
        return "".join(
            block.get("text", "") if isinstance(block, dict) else str(block)
            for block in content
        )
    return content or ""

def run_threat_intel_agent(domain: str, auth_header: str = "") -> ThreatIntelAssessment:
    """Runs Agent 2's internal ReAct loop, then formalizes the result into
    a structured assessment for the Decision Agent to consume."""
    graph = build_graph()

    initial_state: AgentState = {
        "messages": [
            SystemMessage(content="You are a threat intelligence investigator."),
            HumanMessage(content=THREAT_INTEL_PROMPT.format(domain=domain, auth_header=auth_header or "not available")),
        ],
        "step_count": 0,
    }

    final_state = graph.invoke(initial_state)

    tools_used = []
    for m in final_state["messages"]:
        if isinstance(m, AIMessage) and m.tool_calls:
            tools_used.extend(tc["name"] for tc in m.tool_calls)

    raw_findings = "\n".join(
        _content_to_string(m.content) for m in final_state["messages"]
        if isinstance(m, (AIMessage, ToolMessage)) and m.content
    )

    llm = ChatGoogleGenerativeAI(model=LLM_MODEL, google_api_key=GOOGLE_API_KEY)
    structured_llm = llm.with_structured_output(ThreatIntelAssessment)
    assessment = structured_llm.invoke(
        f"Based on this threat intelligence investigation, provide a final risk "
        f"score (0-100) and reasoning:\n\n{raw_findings}"
    )
    assessment.tools_used = list(set(tools_used))
    return assessment