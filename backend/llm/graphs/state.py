"""
Typed state objects for LangGraph workflows.
"""

from typing import Any, Dict, TypedDict


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
    skip_due_to_ogp: bool
    matches: bool
    confidence: float
    reasoning: str
