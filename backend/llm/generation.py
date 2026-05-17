"""
LLM integration for generating blocking rules
"""

import logging
from typing import Any, Dict

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage
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


def _create_chat_model(api_key: str) -> ChatAnthropic:
    """Create and return a LangChain Anthropic chat model."""
    return ChatAnthropic(
        model_name=ANTHROPIC_MODEL,
        api_key=api_key,
        max_tokens=MAX_TOKENS_GENERATION,  # type: ignore[call-arg]
        timeout=None,
        stop=None,
        base_url=None,
    )


async def generation_node_build_prompt(state: Dict[str, Any]) -> Dict[str, Any]:
    return {"prompt": _build_generation_prompt(state["description"])}


async def generation_node_invoke_model(state: Dict[str, Any]) -> Dict[str, Any]:
    api_key = require_anthropic_api_key()
    model = _create_chat_model(api_key)
    response = await model.ainvoke([HumanMessage(content=state["prompt"])])
    content = response.content
    if isinstance(content, list):
        content = "".join(
            str(getattr(block, "text", block)) for block in content
        )
    return {"raw_content": str(content)}


async def generation_node_parse_output(state: Dict[str, Any]) -> Dict[str, Any]:
    parsed = extract_json_from_response(state["raw_content"])
    return {"parsed": parsed}


async def generation_node_normalize_summary(state: Dict[str, Any]) -> Dict[str, Any]:
    parsed = state.get("parsed", {})
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
    return {"summary": summary}


async def generate_block_rules(description: str) -> GenerateRulesResponse:
    """Generate blocking rules via LangGraph + LangChain Anthropic."""
    from .graphs.orchestrator_graph import get_orchestrator_graph

    description_preview = description[:100] + "..." if len(description) > 100 else description
    logger.info(f"[LLM] Generating rules for description: {description_preview}")
    try:
        graph = get_orchestrator_graph()
        result = await graph.ainvoke(
            {"task": "generate_rules", "description": description}
        )
        summary = str(result.get("summary") or "").strip()
        if not summary:
            raise ValueError("Summary is required and cannot be empty")
        logger.info(f"[LLM] Final summary: {summary}")
        return GenerateRulesResponse(summary=summary)
    except ValueError:
        raise
    except Exception as e:
        logger.error(f"[LLM] Error generating rules: {e}", exc_info=True)
        raise ValueError(f"{ERROR_GENERATION_FAILED}: {str(e)}") from e

