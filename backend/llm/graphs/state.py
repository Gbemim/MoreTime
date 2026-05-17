"""
Typed state objects for LangGraph workflows.
"""

from typing import Any, Dict, Literal, TypedDict

OrchestratorTask = Literal["check_metadata", "generate_rules"]


class GenerateRulesState(TypedDict, total=False):
    description: str
    prompt: str
    raw_content: str
    parsed: Dict[str, Any]
    summary: str


class CheckMetadataState(TypedDict, total=False):
    user_description: str
    metadata: Dict[str, Any]
    url: str
    author: Dict[str, Any]
    metadata_text: str
    similarity: float
    skip_due_to_insufficient_metadata: bool
    matches: bool
    confidence: float
    reasoning: str
    reason_code: str


class OrchestratorState(TypedDict, total=False):
    """Parent graph: programmatic task routing into specialist subgraphs."""

    task: OrchestratorTask
    # check_metadata inputs
    user_description: str
    metadata: Dict[str, Any]
    url: str
    # generate_rules input
    description: str
    # check_metadata outputs (merged after subgraph)
    matches: bool
    confidence: float
    reasoning: str
    reason_code: str
    matched_rule_id: str | None
    # generate_rules output
    summary: str
