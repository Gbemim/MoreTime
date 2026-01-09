"""
Utility functions for LLM response parsing
"""

import json
import re
import logging

from constants import ERROR_JSON_PARSE_FAILED

logger = logging.getLogger(__name__)


def _remove_markdown_code_blocks(content: str) -> str:
    """
    Remove markdown code blocks from content
    
    Args:
        content: Content that may contain markdown code blocks
        
    Returns:
        Content with code blocks removed
    """
    if not content.startswith("```"):
        return content
    
    lines = content.split("\n")
    json_start = None
    json_end = None
    
    for i, line in enumerate(lines):
        if line.strip().startswith("```"):
            if json_start is None:
                json_start = i + 1
            else:
                json_end = i
                break
    
    if json_start and json_end:
        return "\n".join(lines[json_start:json_end])
    elif json_start:
        return "\n".join(lines[json_start:])
    
    return content


def _extract_json_with_regex(content: str) -> dict:
    """
    Attempt to extract JSON using regex pattern matching
    
    Args:
        content: Content to extract JSON from
        
    Returns:
        Parsed JSON dictionary
        
    Raises:
        ValueError: If JSON cannot be extracted
    """
    json_match = re.search(r'\{.*\}', content, re.DOTALL)
    if json_match:
        parsed = json.loads(json_match.group())
        logger.info(f"[LLM] Extracted and parsed JSON: {json.dumps(parsed, indent=2)}")
        return parsed
    raise ValueError(ERROR_JSON_PARSE_FAILED)


def extract_json_from_response(content: str) -> dict:
    """
    Extract JSON from LLM response, handling markdown code blocks
    
    Args:
        content: Raw response content from LLM
        
    Returns:
        Parsed JSON dictionary
        
    Raises:
        ValueError: If JSON cannot be parsed
    """
    cleaned_content = _remove_markdown_code_blocks(content.strip())
    
    # Try to parse JSON directly
    try:
        parsed = json.loads(cleaned_content)
        logger.info(f"[LLM] Parsed JSON: {json.dumps(parsed, indent=2)}")
        return parsed
    except json.JSONDecodeError:
        # Try to extract JSON object using regex
        try:
            return _extract_json_with_regex(cleaned_content)
        except (ValueError, json.JSONDecodeError):
            logger.error(
                f"[LLM] Could not parse JSON from response. Content: {cleaned_content}"
            )
            raise ValueError(ERROR_JSON_PARSE_FAILED)

