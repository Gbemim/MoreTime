"""
LLM integration for checking if metadata matches blocking rules
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from typing import Any, Dict, cast

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig

from schemas import CheckMetadataResponse
from config import require_anthropic_api_key
from constants import (
    ANTHROPIC_MODEL,
    MAX_TOKENS_MATCHING,
    HIGH_SIMILARITY_THRESHOLD,
    LOW_SIMILARITY_THRESHOLD,
    CONFIDENCE_THRESHOLD,
    ERROR_METADATA_CHECK_FAILED,
    MAX_METADATA_REACT_RECURSION,
)
from .utils import extract_json_from_response
from .embeddings import get_embedding, cosine_similarity
from .metadata_match_policy import build_single_shot_matching_prompt, format_metadata_block
from .metadata_source import (
    metadata_author_names,
    resolve_metadata,
)
from .graphs.state import CheckMetadataState

logger = logging.getLogger(__name__)


def _create_chat_model(api_key: str) -> ChatAnthropic:
    return ChatAnthropic(
        model_name=ANTHROPIC_MODEL,
        api_key=api_key,
        max_tokens=MAX_TOKENS_MATCHING,  # type: ignore[call-arg]
        timeout=None,
        stop=None,
        base_url=None,
    )


def _youtube_metadata_insufficient(metadata: Dict[str, Any]) -> bool:
    """
    True when metadata is missing or still the generic YouTube shell (SPA not hydrated).
    In that state the model may guess and return matches: true incorrectly.
    Non-empty author_names (e.g. from oEmbed or JSON-LD) counts as usable signal.
    """
    has_authors = bool(metadata_author_names(metadata))
    title = (metadata.get("title") or "").strip()
    desc = (metadata.get("description") or "").strip()
    t_low = title.lower()
    generic_titles = frozenset(
        {"youtube", "youtube - broadcast yourself", "youtube.com"}
    )
    if t_low in generic_titles and len(desc) < 40:
        return not has_authors
    if not title and len(desc) < 40:
        return not has_authors
    if len(title) <= 1 and len(desc) < 20:
        return not has_authors
    return False


async def check_metadata_matches_rule(
    user_description: str,
    url: str,
    metadata_override: Dict[str, Any] | None = None,
) -> CheckMetadataResponse:
    """
    Use LLM to check if website metadata matches the user's rule description
    
    Args:
        user_description: User's blocking rule description
        url: Website URL
        
    Returns:
        CheckMetadataResponse with match result, confidence, and reasoning
        
    Raises:
        ValueError: If API key is not set or check fails
    """
    try:
        from .graphs.orchestrator_graph import get_orchestrator_graph

        # Metadata is resolved oEmbed-first with OGP fallback into normalized fields.
        effective_metadata = (
            metadata_override if isinstance(metadata_override, dict) else await resolve_metadata(url)
        )

        graph = get_orchestrator_graph()
        result = await graph.ainvoke(
            {
                "task": "check_metadata",
                "user_description": user_description,
                "metadata": effective_metadata,
                "url": url,
            }
        )
        return CheckMetadataResponse(
            matches=bool(result.get("matches", False)),
            block=bool(result.get("matches", False))
            and float(result.get("confidence", 0.0)) >= CONFIDENCE_THRESHOLD,
            confidence=float(result.get("confidence", 0.0)),
            reasoning=str(result.get("reasoning", "No reasoning provided")),
            reason_code=str(result.get("reason_code", "llm_evaluation")),
            decision_id=str(uuid.uuid4()),
            matched_rule_id=str(result.get("matched_rule_id")) if result.get("matched_rule_id") else None,
            model_name=ANTHROPIC_MODEL,
            evaluated_at=int(time.time() * 1000),
        )

    except ValueError:
        raise
    except Exception as e:
        logger.error(f"[LLM] Error checking metadata: {e}", exc_info=True)
        raise ValueError(f"{ERROR_METADATA_CHECK_FAILED}: {str(e)}") from e


def _format_metadata_for_embedding(metadata: Dict[str, Any]) -> str:
    """
    Format metadata dictionary into text for embedding
    
    Args:
        metadata: Website metadata dictionary
        
    Returns:
        Formatted text string
    """
    metadata_text = f"YouTube Video: {metadata.get('title', '')}\n"
    author_names = metadata_author_names(metadata)
    if author_names:
        metadata_text += f"Channels: {'; '.join(author_names)}\n"
    if metadata.get('description'):
        metadata_text += f"Description: {metadata.get('description', '')}\n"
    if metadata.get('site_name'):
        metadata_text += f"Site: {metadata.get('site_name', '')}"
    return metadata_text


async def matching_node_metadata_quality_guard(
    state: CheckMetadataState, config: RunnableConfig
) -> Dict[str, Any]:
    metadata = state.get("metadata")
    if metadata is None:
        raise ValueError("metadata is required for metadata_quality_guard")
    if _youtube_metadata_insufficient(metadata):
        logger.info("[MATCH] Skipping embeddings/LLM — metadata insufficient (generic/stale)")
        return {
            "skip_due_to_insufficient_metadata": True,
            "matches": False,
            "confidence": 0.9,
            "reason_code": "insufficient_metadata",
            "reasoning": (
                "Video metadata is not loaded or only shows a generic YouTube placeholder; "
                "cannot evaluate the rule — not blocking."
            ),
        }
    return {
        "skip_due_to_insufficient_metadata": False,
        "metadata_text": _format_metadata_for_embedding(metadata),
    }


async def matching_node_embedding_similarity(
    state: CheckMetadataState, config: RunnableConfig
) -> Dict[str, Any]:
    logger.info("[MATCH] Computing embeddings...")
    rule_embedding = await get_embedding(state["user_description"])  # type: ignore[typeddict-item]
    metadata_embedding = await get_embedding(state["metadata_text"])  # type: ignore[typeddict-item]
    similarity = cosine_similarity(rule_embedding, metadata_embedding)
    logger.info(f"[MATCH] Embedding similarity: {similarity:.3f}")
    return {"similarity": similarity}


def matching_route_after_metadata_quality_guard(
    state: CheckMetadataState, config: RunnableConfig
) -> str:
    return (
        "finalize"
        if state.get("skip_due_to_insufficient_metadata")
        else "embedding_similarity"
    )


def matching_route_after_similarity(
    state: CheckMetadataState, config: RunnableConfig
) -> str:
    similarity = float(state.get("similarity", 0.0))
    if similarity >= HIGH_SIMILARITY_THRESHOLD:
        return "high_similarity_decision"
    return "llm_decision"



async def matching_node_high_similarity_decision(
    state: CheckMetadataState, config: RunnableConfig
) -> Dict[str, Any]:
    similarity = float(state.get("similarity", 0.0))
    return {
        "matches": True,
        "confidence": similarity,
        "reason_code": "high_similarity_match",
        "reasoning": f"High semantic similarity ({similarity:.1%})",
    }


async def _single_shot_metadata_decision(
    api_key: str, user_description: str, metadata_str: str, url: str
) -> Dict[str, Any]:
    prompt = build_single_shot_matching_prompt(user_description, metadata_str)
    model = _create_chat_model(api_key)
    logger.info("[MATCH] Single-shot LLM fallback for URL: %s", url)
    response = await model.ainvoke([HumanMessage(content=prompt)])
    content = response.content
    if isinstance(content, list):
        content = "".join(
            str(getattr(block, "text", block)) for block in content
        )
    parsed = extract_json_from_response(str(content))
    return {
        "matches": bool(parsed.get("matches", False)),
        "confidence": float(parsed.get("confidence", 0.0)),
        "reasoning": str(parsed.get("reasoning", "No reasoning provided")),
        "reason_code": "llm_evaluation",
    }


async def matching_node_llm_decision(
    state: CheckMetadataState, config: RunnableConfig
) -> Dict[str, Any]:
    similarity = float(state.get("similarity", 0.0))
    if similarity < LOW_SIMILARITY_THRESHOLD:
        logger.info(
            f"[MATCH] Low embedding similarity ({similarity:.1%}) - "
            f"using LLM (embeddings are not used to auto-reject)"
        )
    else:
        logger.info(
            f"[MATCH] Medium similarity ({similarity:.1%}) - using LLM for decision"
        )

    metadata = state.get("metadata")
    url = state.get("url")
    user_description = state.get("user_description")
    if metadata is None or url is None or user_description is None:
        raise ValueError("metadata, url, and user_description are required for llm_decision")

    api_key = require_anthropic_api_key()
    metadata_str = format_metadata_block(metadata, url)
    logger.info("[MATCH] Checking metadata match for URL: %s", url)
    logger.debug("[MATCH] User description: %s", user_description)
    logger.debug("[MATCH] Metadata: %s", json.dumps(metadata, indent=2))

    from .graphs.metadata_react_subgraph import (
        build_react_user_message,
        get_last_submission,
        get_metadata_react_graph,
        react_recursion_config,
        reset_react_invocation_context,
        set_react_invocation_context,
    )

    bundle = {
        "user_description": user_description,
        "metadata_str": metadata_str,
        "similarity": similarity,
    }
    t_bundle, t_sub = set_react_invocation_context(bundle)
    submission = None
    try:
        react_graph = get_metadata_react_graph()
        logger.info(
            "[MATCH][ReAct] Invoking metadata subgraph (recursion_limit=%s)",
            MAX_METADATA_REACT_RECURSION,
        )
        await react_graph.ainvoke(
            {"messages": [build_react_user_message()]},
            cast(RunnableConfig, react_recursion_config()),
        )
        submission = get_last_submission()
    except Exception as e:
        logger.warning("[MATCH][ReAct] Subgraph failed, using single-shot: %s", e)
    finally:
        reset_react_invocation_context(t_bundle, t_sub)

    if submission and isinstance(submission, dict) and "matches" in submission:
        matches = bool(submission["matches"])
        confidence = float(submission["confidence"])
        reasoning = str(submission.get("reasoning", "No reasoning provided"))
        logger.info(
            "[MATCH][ReAct] Result - matches: %s, confidence: %.2f, reasoning: %s",
            matches,
            confidence,
            reasoning,
        )
        return {
            "matches": matches,
            "confidence": confidence,
            "reason_code": "llm_evaluation",
            "reasoning": reasoning,
        }

    logger.info("[MATCH][ReAct] No submit_match_decision; falling back to single-shot JSON")
    out = await _single_shot_metadata_decision(
        api_key,
        user_description,
        metadata_str,
        url,
    )
    logger.info(
        "[MATCH] Result - matches: %s, confidence: %.2f, reasoning: %s",
        out["matches"],
        out["confidence"],
        out["reasoning"],
    )
    return out


async def matching_node_finalize(
    state: CheckMetadataState, config: RunnableConfig
) -> Dict[str, Any]:
    return {
        "matches": bool(state.get("matches", False)),
        "confidence": float(state.get("confidence", 0.0)),
        "reason_code": str(state.get("reason_code", "llm_evaluation")),
        "reasoning": str(state.get("reasoning", "No reasoning provided")),
    }

