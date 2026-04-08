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
        description: Description of videos to block
        
    Returns:
        Formatted prompt string
    """
    return f"""You are helping a user create YouTube video blocking rules for productivity.

I will be blocking YouTube videos based on this description:
"{description}"

Produce:
1. `summary` — 1-2 **short sentences** only (no lists, no line breaks inside the string — use a single paragraph).
2. `examples` — 5-10 short strings, each one example category or video type that would be blocked.

Valid JSON requires every string on **one line** with escaped newlines if needed; **never** put raw newlines or markdown bullets inside a JSON string.

Return **only** one JSON object (no markdown fences, no other text), exactly:
{{
  "summary": "One or two sentences explaining what will be blocked.",
  "examples": ["Example category 1", "Example category 2", "Example category 3"]
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

        # Validate and convert to response model (examples may be omitted by older-shaped responses)
        summary = (parsed.get("summary") or "").strip()
        examples = parsed.get("examples")
        if isinstance(examples, list) and examples:
            bullets = "\n".join(
                f"- {str(x).strip()}" for x in examples if str(x).strip()
            )
            if bullets:
                summary = f"{summary}\n\n{bullets}".strip() if summary else bullets

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

