"""
LLM integration for checking if metadata matches blocking rules
"""

import json
import asyncio
import logging
from typing import Dict, Any, List

from anthropic import Anthropic
from anthropic.types import TextBlock

from schemas import CheckMetadataResponse
from config import require_anthropic_api_key
from constants import (
    ANTHROPIC_MODEL,
    MAX_TOKENS_MATCHING,
    HIGH_SIMILARITY_THRESHOLD,
    LOW_SIMILARITY_THRESHOLD,
    ERROR_METADATA_CHECK_FAILED,
)
from .utils import extract_json_from_response
from .embeddings import get_embedding, cosine_similarity

logger = logging.getLogger(__name__)


def _metadata_author_names(metadata: Dict[str, Any]) -> List[str]:
    """Channel/uploader names from extension (list); support legacy single author_name string."""
    raw = metadata.get("author_names")
    if isinstance(raw, list):
        return [str(x).strip() for x in raw if str(x).strip()]
    legacy = metadata.get("author_name")
    if isinstance(legacy, str) and legacy.strip():
        return [legacy.strip()]
    return []


def _format_authors_for_prompt(metadata: Dict[str, Any]) -> str:
    names = _metadata_author_names(metadata)
    if not names:
        return "N/A"
    return "; ".join(names)


def _create_anthropic_client(api_key: str) -> Anthropic:
    """
    Create and return an Anthropic client
    
    Args:
        api_key: Anthropic API key
        
    Returns:
        Anthropic client instance
    """
    return Anthropic(api_key=api_key)


def _extract_text_from_response(message) -> str:
    """
    Extract text content from Anthropic API response
    
    Args:
        message: Anthropic API message response
        
    Returns:
        Extracted text content
    """
    content = ""
    if message.content:
        for block in message.content:
            if isinstance(block, TextBlock):
                content += block.text
    return content


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

Open Graph Protocol Metadata (from https://ogp.me/):
- og:title: {metadata.get('og_title', 'N/A')}
- og:type: {metadata.get('og_type', 'N/A')}
- og:description: {metadata.get('og_description', 'N/A')}
- og:site_name: {metadata.get('og_site_name', 'N/A')}
"""


def _youtube_ogp_insufficient(metadata: Dict[str, Any]) -> bool:
    """
    True when OGP is missing or still the generic YouTube shell (SPA not hydrated).
    In that state the model may guess and return matches: true incorrectly.
    Non-empty author_names (e.g. from oEmbed or JSON-LD) counts as usable signal.
    """
    has_authors = bool(_metadata_author_names(metadata))
    title = (metadata.get("og_title") or "").strip()
    desc = (metadata.get("og_description") or "").strip()
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

YouTube Video Open Graph Protocol Metadata:
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
- Use the Open Graph Protocol metadata (og:title, og:description) as the primary source of information
- If og:title is only the generic word \"YouTube\" (or empty) and og:description is missing or generic, you MUST return matches: false — do not infer video topic from the platform name
- Do not treat marketing boilerplate in the description (e.g. \"Enjoy the videos and music you love\") as evidence the video matches the rule"""


async def check_metadata_matches_rule(
    user_description: str,
    metadata: Dict[str, Any],
    url: str
) -> CheckMetadataResponse:
    """
    Use LLM to check if website metadata matches the user's rule description
    
    Args:
        user_description: User's blocking rule description
        metadata: Website metadata dictionary
        url: Website URL
        
    Returns:
        CheckMetadataResponse with match result, confidence, and reasoning
        
    Raises:
        ValueError: If API key is not set or check fails
    """
    if _youtube_ogp_insufficient(metadata):
        logger.info("[LLM] Skipping model call — OGP insufficient (generic/stale)")
        return CheckMetadataResponse(
            matches=False,
            confidence=0.9,
            reasoning=(
                "Video metadata is not loaded or only shows a generic YouTube placeholder; "
                "cannot evaluate the rule — not blocking."
            ),
        )

    api_key = require_anthropic_api_key()
    metadata_str = _format_metadata_string(metadata, url)
    prompt = _build_matching_prompt(user_description, metadata_str)

    def _call_anthropic():
        client = _create_anthropic_client(api_key)
        return client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=MAX_TOKENS_MATCHING,
            messages=[{"role": "user", "content": prompt}]
        )

    try:
        logger.info("[LLM] Checking metadata match for URL: %s", url)
        logger.debug("[LLM] User description: %s", user_description)
        logger.debug("[LLM] Metadata: %s", json.dumps(metadata, indent=2))
        message = await asyncio.to_thread(_call_anthropic)
        content = _extract_text_from_response(message)
        logger.debug("[LLM] Raw LLM response:\n%s", content)

        # Parse JSON using utility function
        parsed = extract_json_from_response(content)

        matches = bool(parsed.get("matches", False))
        confidence = float(parsed.get("confidence", 0.0))
        reasoning = str(parsed.get("reasoning", "No reasoning provided"))
        
        logger.info(
            f"[LLM] Result - matches: {matches}, "
            f"confidence: {confidence:.2f}, reasoning: {reasoning}"
        )

        return CheckMetadataResponse(
            matches=matches,
            confidence=confidence,
            reasoning=reasoning
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
    metadata_text = f"YouTube Video: {metadata.get('og_title', '')}\n"
    author_names = _metadata_author_names(metadata)
    if author_names:
        metadata_text += f"Channels: {'; '.join(author_names)}\n"
    if metadata.get('og_description'):
        metadata_text += f"Description: {metadata.get('og_description', '')}\n"
    if metadata.get('og_site_name'):
        metadata_text += f"Site: {metadata.get('og_site_name', '')}"
    return metadata_text


async def check_metadata_matches_rule_optimized(
    user_description: str,
    metadata: Dict[str, Any],
    url: str
) -> CheckMetadataResponse:
    """
    Optimized hybrid approach: Use embeddings for fast check, LLM only when needed
    
    Args:
        user_description: User's blocking rule description
        metadata: Website metadata dictionary
        url: Website URL
        
    Returns:
        CheckMetadataResponse with match result, confidence, and reasoning
    """
    logger.info(f"[OPTIMIZED] Checking URL: {url}")
    logger.info(f"[OPTIMIZED] User description: {user_description}")

    if _youtube_ogp_insufficient(metadata):
        logger.info("[OPTIMIZED] Skipping embeddings/LLM — OGP insufficient (generic/stale)")
        return CheckMetadataResponse(
            matches=False,
            confidence=0.9,
            reasoning=(
                "Video metadata is not loaded or only shows a generic YouTube placeholder; "
                "cannot evaluate the rule — not blocking."
            ),
        )

    metadata_text = _format_metadata_for_embedding(metadata)

    # Fast embedding check
    try:
        logger.info("[OPTIMIZED] Computing embeddings...")
        rule_embedding = await get_embedding(user_description)
        metadata_embedding = await get_embedding(metadata_text)
        similarity = cosine_similarity(rule_embedding, metadata_embedding)

        logger.info(f"[OPTIMIZED] Embedding similarity: {similarity:.3f}")

        # High similarity — fast path to block (embedding agrees with rule)
        if similarity >= HIGH_SIMILARITY_THRESHOLD:
            logger.info(
                f"[OPTIMIZED] High similarity ({similarity:.1%}) - "
                f"blocking without LLM"
            )
            return CheckMetadataResponse(
                matches=True,
                confidence=float(similarity),
                reasoning=f"High semantic similarity ({similarity:.1%})"
            )

        # Below high threshold: never auto-reject on low embedding similarity —
        # cosine distance often misses lexical overlaps (e.g. rule vs. title phrasing).
        if similarity < LOW_SIMILARITY_THRESHOLD:
            logger.info(
                f"[OPTIMIZED] Low embedding similarity ({similarity:.1%}) - "
                f"using LLM (embeddings are not used to auto-reject)"
            )
        else:
            logger.info(
                f"[OPTIMIZED] Medium similarity ({similarity:.1%}) - "
                f"using LLM for decision"
            )

        return await check_metadata_matches_rule(
            user_description, metadata, url
        )

    except Exception as e:
        # Fallback to LLM if embeddings fail
        logger.warning(f"[OPTIMIZED] Embedding check failed, using LLM: {e}")
        return await check_metadata_matches_rule(user_description, metadata, url)

