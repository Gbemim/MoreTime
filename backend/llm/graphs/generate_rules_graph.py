"""
LangGraph workflow for generate-block-rules pipeline.
"""

from langgraph.graph import START, END, StateGraph

from .runtime import compile_graph
from .state import GenerateRulesState
from ..generation import (
    generation_node_build_prompt,
    generation_node_invoke_model,
    generation_node_parse_output,
    generation_node_normalize_summary,
)

_GENERATE_RULES_GRAPH = None


def get_generate_rules_graph():
    global _GENERATE_RULES_GRAPH
    if _GENERATE_RULES_GRAPH is None:
        builder = StateGraph(GenerateRulesState)
        builder.add_node("build_prompt", generation_node_build_prompt)
        builder.add_node("invoke_model", generation_node_invoke_model)
        builder.add_node("parse_output", generation_node_parse_output)
        builder.add_node("normalize_summary", generation_node_normalize_summary)
        builder.add_edge(START, "build_prompt")
        builder.add_edge("build_prompt", "invoke_model")
        builder.add_edge("invoke_model", "parse_output")
        builder.add_edge("parse_output", "normalize_summary")
        builder.add_edge("normalize_summary", END)
        _GENERATE_RULES_GRAPH = compile_graph(builder)
    return _GENERATE_RULES_GRAPH
