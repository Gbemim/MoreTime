"""
Shared runtime helpers for building graph-backed pipelines.
"""

from langgraph.graph import StateGraph


def compile_graph(builder: StateGraph):
    """Compile a graph builder into an executable graph."""
    return builder.compile()
