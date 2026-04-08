"""
LLM integration for checking if metadata matches blocking rules
"""

import json
import logging
import time
import uuid
from typing import Dict, Any, List

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage
from pydantic.v1 import SecretStr

from schemas import CheckMetadataResponse
from config import require_anthropic_api_key
from constants import (
    ANTHROPIC_MODEL,
    MAX_TOKENS_MATCHING,
    HIGH_SIMILARITY_THRESHOLD,
    LOW_SIMILARITY_THRESHOLD,
    CONFIDENCE_THRESHOLD,
    ERROR_METADATA_CHECK_FAILED,
)
from .utils import extract_json_from_response
from .embeddings import get_embedding, cosine_similarity
from .metadata_source import (
    metadata_author_names,
    resolve_metadata,
)

logger = logging.getLogger(__name__)


def _format_authors_for_prompt(metadata: Dict[str, Any]) -> str:
    names = metadata_author_names(metadata)
    if not names:
        return "N/A"
    return "; ".join(names)


def _create_chat_model(api_key: str) -> ChatAnthropic:
    params: Dict[str, Any] = {
        "model_name": ANTHROPIC_MODEL,
        "timeout": None,
        "stop": None,
        "base_url": None,
        "api_key": SecretStr(api_key),
        "max_tokens": MAX_TOKENS_MATCHING,
    }
    return ChatAnthropic(**params)


def _format_metadata_string(metadata: Dict[str, Any], url: str) -> str:
    """
    Format metadata dictionary into a readable string
    
    Args:
        metadata: Website metadata dictionary
        url: Website URL
        
    Returns:
        Formatted metadata string
    """
    return f"""
YouTube Video URL: {url}
Video ID: {metadata.get('video_id', 'N/A')}

Channels (uploaders / collaborations):
- author_names: {_format_authors_for_prompt(metadata)}

Video Metadata (normalized fields; oEmbed-first, OGP fallback):
- title: {metadata.get('title', 'N/A')}
- content_type: {metadata.get('content_type', 'N/A')}
- description: {metadata.get('description', 'N/A')}
- site_name: {metadata.get('site_name', 'N/A')}
"""


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


def _build_matching_prompt(user_description: str, metadata_str: str) -> str:
    """
    Build the prompt for checking metadata matches
    
    Args:
        user_description: User's blocking rule description
        metadata_str: Formatted metadata string
        
    Returns:
        Formatted prompt string
    """
    return f"""You are helping determine if a YouTube video should be blocked based on a user's rule.

User's blocking rule description (what kind of videos they want to block):
"{user_description}"

YouTube Video Metadata (oEmbed-first, OGP fallback):
{metadata_str}

Determine if this YouTube video matches the user's blocking rule. Consider:
- The video's title and description
- The video's content and topic
- Whether it falls into what the user wants to block
- The context and intent of the user's rule

Return your response as a JSON object with this exact structure:
{{
  "matches": true or false,
  "confidence": 0.0 to 1.0 (how confident you are in your decision),
  "reasoning": "Brief explanation of why this YouTube video matches or doesn't match the user's rule"
}}

IMPORTANT:
- This is specifically for YouTube videos - focus on video content, not general websites
- Be strict - only return matches: true if the video clearly falls under the user's blocking rule
- If matches: true, your confidence should be at least 0.5 (you should be confident when blocking)
- If matches: false, confidence can be lower (it's okay to be uncertain about non-matches)
- Confidence represents how sure you are that your matches decision is correct
- Metadata fields may be populated from YouTube oEmbed first, with OGP as fallback; treat provided title/description fields as the primary evidence
- If title is only the generic word \"YouTube\" (or empty) and description is missing or generic, you MUST return matches: false — do not infer video topic from the platform name
- Do not treat marketing boilerplate in the description (e.g. \"Enjoy the videos and music you love\") as evidence the video matches the rule"""


async def check_metadata_matches_rule(
    user_description: str,
    url: str
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
        from .graphs.check_metadata_graph import get_check_metadata_graph

        # Metadata is resolved oEmbed-first with OGP fallback into normalized fields.
        effective_metadata = await resolve_metadata(url)

        graph = get_check_metadata_graph()
        result = await graph.ainvoke(
            {
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


async def check_metadata_matches_rule_optimized(
    user_description: str,
    url: str
) -> CheckMetadataResponse:
    """
    Optimized hybrid approach: Use embeddings for fast check, LLM only when needed
    
    Args:
        user_description: User's blocking rule description
        url: Website URL
        
    Returns:
        CheckMetadataResponse with match result, confidence, and reasoning
    """
    return await check_metadata_matches_rule(
        user_description=user_description,
        url=url,
    )


async def matching_node_metadata_quality_guard(state: Dict[str, Any]) -> Dict[str, Any]:
    metadata = state["metadata"]
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


async def matching_node_embedding_similarity(state: Dict[str, Any]) -> Dict[str, Any]:
    logger.info("[MATCH] Computing embeddings...")
    rule_embedding = await get_embedding(state["user_description"])
    metadata_embedding = await get_embedding(state["metadata_text"])
    similarity = cosine_similarity(rule_embedding, metadata_embedding)
    logger.info(f"[MATCH] Embedding similarity: {similarity:.3f}")
    return {"similarity": similarity}


def matching_route_after_metadata_quality_guard(state: Dict[str, Any]) -> str:
    return (
        "finalize"
        if state.get("skip_due_to_insufficient_metadata")
        else "embedding_similarity"
    )


def matching_route_after_similarity(state: Dict[str, Any]) -> str:
    similarity = float(state.get("similarity", 0.0))
    if similarity >= HIGH_SIMILARITY_THRESHOLD:
        return "high_similarity_decision"
    return "llm_decision"


async def matching_node_high_similarity_decision(state: Dict[str, Any]) -> Dict[str, Any]:
    similarity = float(state.get("similarity", 0.0))
    return {
        "matches": True,
        "confidence": similarity,
        "reason_code": "high_similarity_match",
        "reasoning": f"High semantic similarity ({similarity:.1%})",
    }


async def matching_node_llm_decision(state: Dict[str, Any]) -> Dict[str, Any]:
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

    api_key = require_anthropic_api_key()
    metadata_str = _format_metadata_string(state["metadata"], state["url"])
    prompt = _build_matching_prompt(state["user_description"], metadata_str)
    model = _create_chat_model(api_key)
    logger.info("[MATCH] Checking metadata match for URL: %s", state["url"])
    logger.debug("[MATCH] User description: %s", state["user_description"])
    logger.debug("[MATCH] Metadata: %s", json.dumps(state["metadata"], indent=2))
    response = await model.ainvoke([HumanMessage(content=prompt)])
    content = response.content
    if isinstance(content, list):
        content = "".join(
            str(getattr(block, "text", block)) for block in content
        )
    parsed = extract_json_from_response(str(content))
    matches = bool(parsed.get("matches", False))
    confidence = float(parsed.get("confidence", 0.0))
    reasoning = str(parsed.get("reasoning", "No reasoning provided"))
    logger.info(
        f"[MATCH] Result - matches: {matches}, "
        f"confidence: {confidence:.2f}, reasoning: {reasoning}"
    )
    return {
        "matches": matches,
        "confidence": confidence,
        "reason_code": "llm_evaluation",
        "reasoning": reasoning,
    }


async def matching_node_finalize(state: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "matches": bool(state.get("matches", False)),
        "confidence": float(state.get("confidence", 0.0)),
        "reason_code": str(state.get("reason_code", "llm_evaluation")),
        "reasoning": str(state.get("reasoning", "No reasoning provided")),
    }

