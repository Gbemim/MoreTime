"""
LangGraph workflow for check-metadata pipeline.
"""

from langgraph.graph import START, END, StateGraph

from .runtime import compile_graph
from .state import CheckMetadataState
from ..matching import (
    matching_node_ogp_guard,
    matching_route_after_ogp_guard,
    matching_node_embedding_similarity,
    matching_route_after_similarity,
    matching_node_high_similarity_decision,
    matching_node_llm_decision,
    matching_node_finalize,
)

_CHECK_METADATA_GRAPH = None


def get_check_metadata_graph():
    global _CHECK_METADATA_GRAPH
    if _CHECK_METADATA_GRAPH is None:
        builder = StateGraph(CheckMetadataState)
        builder.add_node("ogp_guard", matching_node_ogp_guard)
        builder.add_node("embedding_similarity", matching_node_embedding_similarity)
        builder.add_node("high_similarity_decision", matching_node_high_similarity_decision)
        builder.add_node("llm_decision", matching_node_llm_decision)
        builder.add_node("finalize", matching_node_finalize)

        builder.add_edge(START, "ogp_guard")
        builder.add_conditional_edges(
            "ogp_guard",
            matching_route_after_ogp_guard,
            {
                "embedding_similarity": "embedding_similarity",
                "finalize": "finalize",
            },
        )
        builder.add_conditional_edges(
            "embedding_similarity",
            matching_route_after_similarity,
            {
                "high_similarity_decision": "high_similarity_decision",
                "llm_decision": "llm_decision",
            },
        )
        builder.add_edge("high_similarity_decision", "finalize")
        builder.add_edge("llm_decision", "finalize")
        builder.add_edge("finalize", END)

        _CHECK_METADATA_GRAPH = compile_graph(builder)
    return _CHECK_METADATA_GRAPH
