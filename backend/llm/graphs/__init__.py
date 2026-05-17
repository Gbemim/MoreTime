"""
LangGraph graph exports.

Imports are lazy so `from llm.graphs.state import CheckMetadataState` does not pull in
`matching` (avoids circular import: matching -> graphs.state -> graphs.__init__).
"""

from typing import Any

__all__ = [
    "get_generate_rules_graph",
    "get_check_metadata_graph",
    "get_orchestrator_graph",
]


def __getattr__(name: str) -> Any:
    if name == "get_generate_rules_graph":
        from .generate_rules_graph import get_generate_rules_graph

        return get_generate_rules_graph
    if name == "get_check_metadata_graph":
        from .check_metadata_graph import get_check_metadata_graph

        return get_check_metadata_graph
    if name == "get_orchestrator_graph":
        from .orchestrator_graph import get_orchestrator_graph

        return get_orchestrator_graph
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
