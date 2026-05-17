"""
Compiled LangGraph prebuilt ReAct agent for ambiguous metadata match decisions.
Invoked from matching_node_llm_decision (parent has different state schema).
"""

from __future__ import annotations

import contextvars
import logging
from typing import Any, Dict, Optional

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool
from langchain.agents import create_agent
from config import require_anthropic_api_key
from constants import ANTHROPIC_MODEL, MAX_TOKENS_MATCHING, MAX_METADATA_REACT_RECURSION
from ..metadata_match_policy import build_react_system_prompt

logger = logging.getLogger(__name__)

# Per-invocation context (avoids stale data across concurrent requests).
_match_bundle: contextvars.ContextVar[Optional[Dict[str, Any]]] = contextvars.ContextVar(
    "metadata_react_bundle", default=None
)
_match_submission: contextvars.ContextVar[Optional[Dict[str, Any]]] = contextvars.ContextVar(
    "metadata_react_submission", default=None
)


def _format_context_from_bundle(bundle: Dict[str, Any]) -> str:
    return (
        f"User blocking rule:\n{bundle.get('user_description', '')}\n\n"
        f"Precomputed embedding similarity (rule vs metadata text): "
        f"{float(bundle.get('similarity', 0.0)):.4f}\n\n"
        f"Formatted metadata:\n{bundle.get('metadata_str', '')}"
    )


@tool
def get_match_context() -> str:
    """Load the user rule, video metadata, URL context, and embedding similarity. Call before deciding."""
    bundle = _match_bundle.get()
    if not bundle:
        return "Error: no match context is available."
    return _format_context_from_bundle(bundle)


@tool
def submit_match_decision(matches: bool, confidence: float, reasoning: str) -> str:
    """Submit the final decision. Call exactly once when finished. matches=true means the video matches the blocking rule."""
    _match_submission.set(
        {
            "matches": bool(matches),
            "confidence": float(confidence),
            "reasoning": str(reasoning).strip() or "No reasoning provided",
        }
    )
    logger.info(
        "[MATCH][ReAct] submit_match_decision matches=%s confidence=%.2f",
        matches,
        confidence,
    )
    return "Decision recorded. Stop and do not call tools again."


_METADATA_REACT_GRAPH = None


def _create_chat_model(api_key: str) -> ChatAnthropic:
    return ChatAnthropic(
        model_name=ANTHROPIC_MODEL,
        api_key=api_key,
        max_tokens=MAX_TOKENS_MATCHING,  # type: ignore[call-arg]
        timeout=None,
        stop=None,
        base_url=None,
    )


def get_metadata_react_graph():
    """Singleton compiled create_agent graph."""
    global _METADATA_REACT_GRAPH
    if _METADATA_REACT_GRAPH is None:
        api_key = require_anthropic_api_key()
        model = _create_chat_model(api_key)
        system = build_react_system_prompt()
        _METADATA_REACT_GRAPH = create_agent(
            model,
            [get_match_context, submit_match_decision],
            system_prompt=SystemMessage(content=system),
            name="metadata_match_react",
        )
    return _METADATA_REACT_GRAPH


def set_react_invocation_context(bundle: Dict[str, Any]) -> tuple[Any, Any]:
    """Set contextvars for this request; returns tokens for reset()."""
    t_bundle = _match_bundle.set(bundle)
    t_sub = _match_submission.set(None)
    return t_bundle, t_sub


def reset_react_invocation_context(t_bundle: Any, t_sub: Any) -> None:
    _match_bundle.reset(t_bundle)
    _match_submission.reset(t_sub)


def get_last_submission() -> Optional[Dict[str, Any]]:
    return _match_submission.get()


def build_react_user_message() -> HumanMessage:
    return HumanMessage(
        content=(
            "Decide if this YouTube video should count as matching the user's blocking rule. "
            "Use get_match_context, then submit_match_decision with your final structured answer."
        )
    )


def react_recursion_config() -> Dict[str, Any]:
    return {"recursion_limit": MAX_METADATA_REACT_RECURSION}
