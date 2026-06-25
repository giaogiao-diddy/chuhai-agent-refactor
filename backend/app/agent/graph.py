from langgraph.graph import END, StateGraph

from app.agent.nodes import (
    dialogue_node,
    extract_answers_node,
    opening_node,
    report_node,
    score_node,
    trim_history_node,
)
from app.schemas.agent_state import AgentState


def _to_agent_state(raw: dict | AgentState) -> AgentState:
    if isinstance(raw, AgentState):
        return raw
    return AgentState(**raw)


def _route_after_opening(state: AgentState) -> str:
    if state.messages and state.messages[-1].role == "user":
        return "dialogue"
    return "trim_history"


def create_dialogue_graph() -> StateGraph:
    graph = StateGraph(AgentState)

    graph.add_node("opening", opening_node)
    graph.add_node("dialogue", dialogue_node)
    graph.add_node("trim_history", trim_history_node)

    graph.set_entry_point("opening")
    graph.add_conditional_edges(
        "opening",
        _route_after_opening,
        {"dialogue": "dialogue", "trim_history": "trim_history"},
    )
    graph.add_edge("dialogue", "trim_history")
    graph.add_edge("trim_history", END)

    return graph.compile()


async def run_dialogue_graph(state: AgentState) -> AgentState:
    graph = create_dialogue_graph()
    raw = await graph.ainvoke(state)
    return _to_agent_state(raw)


async def run_scoring_pipeline(state: AgentState | dict) -> AgentState:
    graph = StateGraph(AgentState)
    graph.add_node("extract_answers", extract_answers_node)
    graph.add_node("score", score_node)
    graph.set_entry_point("extract_answers")
    graph.add_edge("extract_answers", "score")
    graph.add_edge("score", END)
    compiled = graph.compile()
    raw = await compiled.ainvoke(
        state if isinstance(state, AgentState) else AgentState(**state)
    )
    return _to_agent_state(raw)


async def run_report_pipeline(state: AgentState | dict) -> AgentState:
    graph = StateGraph(AgentState)
    graph.add_node("report", report_node)
    graph.set_entry_point("report")
    graph.add_edge("report", END)
    compiled = graph.compile()
    raw = await compiled.ainvoke(
        state if isinstance(state, AgentState) else AgentState(**state)
    )
    return _to_agent_state(raw)
