import re
from typing import Annotated, TypedDict
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from langchain_anthropic import ChatAnthropic
import time

from config import ANTHROPIC_API_KEY, LLM_MODEL, MAX_REACT_STEPS
from tools.whois_lookup import check_domain_age
from tools.virus_total import check_domain_reputation
from tools.header_check import check_spf_dkim
from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.messages import HumanMessage
from langgraph.graph import END, StateGraph

from langchain_core.messages import SystemMessage
from agent.prompts import SYSTEM_PROMPT
TOOLS = [check_domain_age, check_domain_reputation, check_spf_dkim]
TOOLS_BY_NAME = {t.name: t for t in TOOLS}

class AgentState(TypedDict):
    """The shared state LangGraph passes between every node in the graph."""
    messages: Annotated[list[BaseMessage], add_messages]
    step_count: int


def _build_llm():
    """Builds an LLM client that knows about our three tools."""
    llm = ChatAnthropic(model=LLM_MODEL, api_key=ANTHROPIC_API_KEY)
    return llm.bind_tools(TOOLS)


def reason_node(state: AgentState) -> dict:
    """Sends the current conversation to the LLM and gets back its next
    move -- either a tool call or a final classification."""
    llm = _build_llm()
    response = llm.invoke(state["messages"])
    return {"messages": [response], "step_count": state["step_count"] + 1}


def execute_tool_node(state: AgentState) -> dict:
    """Runs whichever tool(s) the LLM asked for in its last message, and
    feeds the results back into the conversation as observations."""
    last_message: AIMessage = state["messages"][-1]
    tool_messages = []

    for tool_call in last_message.tool_calls:
        tool_fn = TOOLS_BY_NAME.get(tool_call["name"])

        if tool_fn is None:
            result = f"Unknown tool: {tool_call['name']}"
        else:
            result = tool_fn.invoke(tool_call["args"])

        tool_messages.append(
            ToolMessage(content=str(result), tool_call_id=tool_call["id"])
        )

    return {"messages": tool_messages}


def force_conclude_node(state: AgentState) -> dict:
    """Forces a final answer once the safety cap is hit, using whatever
    evidence has been gathered so far. Uses a plain LLM with no tools bound,
    so it can't ask for yet another tool call."""
    conclude_request = HumanMessage(
        content="You have reached the maximum number of investigation steps. "
        "Based on the evidence gathered so far, give your final answer now "
        "in the required format. Do not call any more tools."
    )
    llm = ChatAnthropic(model=LLM_MODEL, api_key=ANTHROPIC_API_KEY)  # not bound to tools
    response = llm.invoke(state["messages"] + [conclude_request])
    return {"messages": [conclude_request, response]}

def should_continue(state: AgentState) -> str:
    """Conditional edge: continue investigating, force a conclusion because
    the safety cap was hit mid-investigation, or end normally."""
    last_message = state["messages"][-1]
    wants_tool = isinstance(last_message, AIMessage) and last_message.tool_calls

    if wants_tool and state["step_count"] >= MAX_REACT_STEPS:
        return "force_conclude"
    if wants_tool:
        return "continue"
    return "end"

def build_graph():
    """Wires the four nodes together into the actual ReAct loop."""
    graph = StateGraph(AgentState)

    graph.add_node("reason", reason_node)
    graph.add_node("execute_tool", execute_tool_node)
    graph.add_node("force_conclude", force_conclude_node)

    graph.set_entry_point("reason")

    graph.add_conditional_edges(
        "reason",
        should_continue,
        {
            "continue": "execute_tool",
            "force_conclude": "force_conclude",
            "end": END,
        },
    )

    graph.add_edge("execute_tool", "reason")
    graph.add_edge("force_conclude", END)

    return graph.compile()


def parse_final_answer(text) -> dict:
    """Extracts Classification/Confidence/Reasoning from the LLM's final message."""
    # Some models return content as a list of blocks instead of a plain string
    if isinstance(text, list):
        text = "".join(
            block.get("text", "") if isinstance(block, dict) else str(block)
            for block in text
        )

    classification = re.search(r"Classification:\s*(\w+)", text)
    confidence = re.search(r"Confidence:\s*(\d+)", text)
    reasoning = re.search(r"Reasoning:\s*(.+)", text, re.DOTALL)

    return {
        "classification": classification.group(1) if classification else "Unknown",
        "confidence": float(confidence.group(1)) if confidence else 0.0,
        "reasoning": reasoning.group(1).strip() if reasoning else text,
    }


def run_agent(email_context: str) -> dict:
    """Entry point: give the agent an email's context (Phase 2 observations
    plus basic sender/subject info), get back a decision plus the full
    reasoning trace for logging."""
    graph = build_graph()

    initial_state: AgentState = {
        "messages": [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=email_context),
        ],
        "step_count": 0,
    }

    start_time = time.time()
    final_state = graph.invoke(initial_state)
    execution_time = time.time() - start_time

    final_text = final_state["messages"][-1].content
    result = parse_final_answer(final_text)
    result["execution_time_seconds"] = execution_time
    result["messages"] = final_state["messages"]  # full trace, for logging later

    return result