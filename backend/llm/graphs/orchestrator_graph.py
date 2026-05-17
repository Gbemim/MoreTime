"""
Programmatic orchestrator: routes by `task` into check-metadata or generate-rules subgraphs.
"""

from typing import Any, Dict

from langgraph.graph import END, START, StateGraph

from .check_metadata_graph import get_check_metadata_graph
from .generate_rules_graph import get_generate_rules_graph
from .runtime import compile_graph
from .state import OrchestratorState, OrchestratorTask

_ORCHESTRATOR_GRAPH = None


def _route_from_start(state: OrchestratorState) -> OrchestratorTask:
    task = state.get("task")
    if task == "check_metadata":
        return "check_metadata"
    if task == "generate_rules":
        return "generate_rules"
    raise ValueError(f"orchestrator: missing or unknown task: {task!r}")


async def orchestrator_node_check_metadata(state: OrchestratorState) -> Dict[str, Any]:
    user_description = state.get("user_description")
    metadata = state.get("metadata")
    url = state.get("url")
    if user_description is None or metadata is None or url is None:
        raise ValueError(
            "orchestrator: check_metadata requires user_description, metadata, and url"
        )

    graph = get_check_metadata_graph()
    result = await graph.ainvoke(
        {
            "user_description": user_description,
            "metadata": metadata,
            "url": url,
        }
    )
    out: Dict[str, Any] = {
        "matches": result.get("matches"),
        "confidence": result.get("confidence"),
        "reasoning": result.get("reasoning"),
        "reason_code": result.get("reason_code"),
    }
    if result.get("matched_rule_id") is not None:
        out["matched_rule_id"] = result.get("matched_rule_id")
    return out


async def orchestrator_node_generate_rules(state: OrchestratorState) -> Dict[str, Any]:
    description = state.get("description")
    if description is None:
        raise ValueError("orchestrator: generate_rules requires description")

    graph = get_generate_rules_graph()
    result = await graph.ainvoke({"description": description})
    return {"summary": result.get("summary")}


def get_orchestrator_graph():
    global _ORCHESTRATOR_GRAPH
    if _ORCHESTRATOR_GRAPH is None:
        builder = StateGraph(OrchestratorState)
        builder.add_node("check_metadata_agent", orchestrator_node_check_metadata)
        builder.add_node("generate_rules_agent", orchestrator_node_generate_rules)
        builder.add_conditional_edges(
            START,
            _route_from_start,
            {
                "check_metadata": "check_metadata_agent",
                "generate_rules": "generate_rules_agent",
            },
        )
        builder.add_edge("check_metadata_agent", END)
        builder.add_edge("generate_rules_agent", END)
        _ORCHESTRATOR_GRAPH = compile_graph(builder)
    return _ORCHESTRATOR_GRAPH
