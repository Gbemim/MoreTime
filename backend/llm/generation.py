"""
LLM integration for generating blocking rules
"""

import asyncio
import logging
from typing import Callable

from anthropic import Anthropic
from anthropic.types import TextBlock

from schemas import GenerateRulesResponse
from config import require_anthropic_api_key
from constants import (
    ANTHROPIC_MODEL,
    MAX_TOKENS_GENERATION,
    ERROR_GENERATION_FAILED,
)
from .utils import extract_json_from_response

logger = logging.getLogger(__name__)


def _build_generation_prompt(description: str) -> str:
    """
    Build the prompt for generating blocking rules
    
    Args:
        description: User's description of videos to block
        
    Returns:
        Formatted prompt string
    """
    return f"""You are helping a user create YouTube video blocking rules for productivity.

The user wants to block YouTube videos based on this description:
"{description}"

The blocking system uses metadata analysis to identify and block YouTube videos. The system analyzes the video's title, description, type, etc. and compares it against the user's blocking rule description using semantic similarity. If the video's metadata matches the blocking rule, it will be blocked.

Please generate a summary that:
1. Explains what types of YouTube videos will be blocked based on OGP metadata analysis (2-3 sentences)
2. Includes 5-10 specific example video types or categories that would be blocked based on the user's description (e.g., "gaming walkthroughs", "entertainment vlogs", "distracting content", etc.)
3. Mentions that the system analyzes YouTube video metadata (title, description) using Open Graph Protocol to determine if a video matches the blocking criteria

Return your response as a JSON object with this exact structure:
{{
  "summary": "Brief explanation of what YouTube videos will be blocked, followed by a list of 5-10 example video types/categories that would be blocked (e.g., 'Examples include: gaming walkthroughs, entertainment vlogs, reaction videos, etc.')"
}}"""


def _create_anthropic_client(api_key: str) -> Anthropic:
    """
    Create and return an Anthropic client
    
    Args:
        api_key: Anthropic API key
        
    Returns:
        Anthropic client instance
    """
    return Anthropic(api_key=api_key)


def _call_anthropic_api(api_key: str, prompt: str) -> Callable:
    """
    Create a callable function for Anthropic API
    
    Args:
        api_key: Anthropic API key
        prompt: Prompt to send to the API
        
    Returns:
        Callable function that returns API response
    """
    def _call():
        client = _create_anthropic_client(api_key)
        return client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=MAX_TOKENS_GENERATION,
            messages=[{"role": "user", "content": prompt}]
        )
    return _call


async def generate_block_rules(description: str) -> GenerateRulesResponse:
    """
    Generate blocking rules using Anthropic Claude API
    
    Args:
        description: User's natural language description of YouTube videos to block
        
    Returns:
        GenerateRulesResponse with summary including explanation and example video types
        
    Raises:
        ValueError: If API key is not set or generation fails
    """
    api_key = require_anthropic_api_key()
    prompt = _build_generation_prompt(description)

    try:
        description_preview = description[:100] + "..." if len(description) > 100 else description
        logger.info(f"[LLM] Generating rules for description: {description_preview}")
        
        api_call = _call_anthropic_api(api_key, prompt)
        message = await asyncio.to_thread(api_call)

        # Extract text content from the response
        content = _extract_text_from_response(message)
        
        logger.info(f"[LLM] Raw response content:\n{content}")

        # Parse JSON using utility function
        parsed = extract_json_from_response(content)

        # Validate and convert to response model
        summary = parsed.get("summary", "").strip()
        
        if not summary:
            raise ValueError("Summary is required and cannot be empty")
        
        logger.info(f"[LLM] Final summary: {summary}")
        return GenerateRulesResponse(summary=summary)

    except ValueError:
        raise
    except Exception as e:
        logger.error(f"[LLM] Error calling Anthropic API: {e}", exc_info=True)
        raise ValueError(f"{ERROR_GENERATION_FAILED}: {str(e)}") from e


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

