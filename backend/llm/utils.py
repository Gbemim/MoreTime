"""
Utility functions for LLM response parsing
"""

import json
import re
import logging
from typing import Dict, Optional

from constants import ERROR_JSON_PARSE_FAILED

logger = logging.getLogger(__name__)


def _strip_markdown_fences(content: str) -> str:
    """
    If the model wrapped JSON in a fenced block anywhere in the response, return the inner body.
    Handles preamble text before the fence (e.g. 'Here is the JSON:\\n```json ...').
    """
    content = content.strip()
    fence = re.search(r"```(?:json)?\s*\n?(.*?)```", content, re.DOTALL | re.IGNORECASE)
    if fence:
        return fence.group(1).strip()
    return content


def _first_json_object(content: str) -> Optional[Dict]:
    """
    Parse the first top-level JSON object in `content` using JSONDecoder (handles nested braces
    and quoted strings correctly; avoids greedy-regex mistakes).
    """
    decoder = json.JSONDecoder()
    for i, ch in enumerate(content):
        if ch != "{":
            continue
        try:
            obj, _ = decoder.raw_decode(content, i)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            return obj
    return None


def extract_json_from_response(content: str) -> dict:
    """
    Extract JSON from LLM response, handling markdown fences and leading prose.
    """
    if not content or not content.strip():
        logger.error("[LLM] Empty response content for JSON extraction")
        raise ValueError(ERROR_JSON_PARSE_FAILED)

    stripped = _strip_markdown_fences(content.strip())

    for candidate in (stripped, content.strip()):
        try:
            parsed = json.loads(candidate)
            if isinstance(parsed, dict):
                logger.debug("[LLM] Parsed JSON (full string)")
                return parsed
        except json.JSONDecodeError:
            pass
        found = _first_json_object(candidate)
        if found is not None:
            logger.debug("[LLM] Parsed JSON (first object in string)")
            return found

    preview = stripped[:800] + ("…" if len(stripped) > 800 else "")
    logger.error("[LLM] Could not parse JSON from response. Preview: %s", preview)
    raise ValueError(ERROR_JSON_PARSE_FAILED)

