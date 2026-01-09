"""
LLM integration for checking if metadata matches blocking rules
"""

import json
import asyncio
import logging
from typing import Dict, Any

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


## edit
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

Open Graph Protocol Metadata (from https://ogp.me/):
- og:title: {metadata.get('og_title', 'N/A')}
- og:type: {metadata.get('og_type', 'N/A')}
- og:description: {metadata.get('og_description', 'N/A')}
- og:site_name: {metadata.get('og_site_name', 'N/A')}
"""


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
- The video's title and description (from og:title and og:description)
- The video's content category and topic
- Whether it falls into the category the user wants to block
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
- If matches: true, your confidence should be at least 0.7 (you should be confident when blocking)
- If matches: false, confidence can be lower (it's okay to be uncertain about non-matches)
- Confidence represents how sure you are that your matches decision is correct
- Use the Open Graph Protocol metadata (og:title, og:description) as the primary source of information"""


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
        logger.info(f"[LLM] Checking metadata match for URL: {url}")
        logger.info(f"[LLM] User description: {user_description}")
        logger.info(f"[LLM] Metadata: {json.dumps(metadata, indent=2)}")
        
        message = await asyncio.to_thread(_call_anthropic)
        content = _extract_text_from_response(message)
        
        logger.info(f"[LLM] Raw LLM response:\n{content}")

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
    
    metadata_text = _format_metadata_for_embedding(metadata)
    
    # Fast embedding check
    try:
        logger.info("[OPTIMIZED] Computing embeddings...")
        rule_embedding = await get_embedding(user_description)
        metadata_embedding = await get_embedding(metadata_text)
        similarity = cosine_similarity(rule_embedding, metadata_embedding)
        
        logger.info(f"[OPTIMIZED] Embedding similarity: {similarity:.3f}")
        
        # High confidence - return immediately
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
        
        # Low confidence - definitely doesn't match
        if similarity < LOW_SIMILARITY_THRESHOLD:
            logger.info(
                f"[OPTIMIZED] Low similarity ({similarity:.1%}) - not blocking"
            )
            return CheckMetadataResponse(
                matches=False,
                confidence=float(1.0 - similarity),
                reasoning=f"Low similarity ({similarity:.1%}) - does not match"
            )
        
        # Medium confidence - use LLM for accurate decision
        logger.info(
            f"[OPTIMIZED] Medium similarity ({similarity:.1%}) - "
            f"using LLM for decision"
        )
        return await check_metadata_matches_rule(user_description, metadata, url)
        
    except Exception as e:
        # Fallback to LLM if embeddings fail
        logger.warning(f"[OPTIMIZED] Embedding check failed, using LLM: {e}")
        return await check_metadata_matches_rule(user_description, metadata, url)

