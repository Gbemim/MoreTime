"""
Shared copy for metadata-vs-rule evaluation (single-shot JSON and ReAct agent).
"""

from typing import Any, Dict

from .metadata_source import metadata_author_names


def _format_authors_for_prompt(metadata: Dict[str, Any]) -> str:
    names = metadata_author_names(metadata)
    if not names:
        return "N/A"
    return "; ".join(names)


def format_metadata_block(metadata: Dict[str, Any], url: str) -> str:
    """Readable metadata block for prompts and tools."""
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


MATCHING_POLICY_RULES = """IMPORTANT:
- This is specifically for YouTube videos - focus on video content, not general websites
- Be strict - only return matches: true if the video clearly falls under the user's blocking rule
- If matches: true, your confidence should be at least 0.5 (you should be confident when blocking)
- If matches: false, confidence can be lower (it's okay to be uncertain about non-matches)
- Confidence represents how sure you are that your matches decision is correct
- Metadata fields may be populated from YouTube oEmbed first, with OGP as fallback; treat provided title/description fields as the primary evidence
- If title is only the generic word "YouTube" (or empty) and description is missing or generic, you MUST decide not to match — do not infer video topic from the platform name
- Do not treat marketing boilerplate in the description (e.g. "Enjoy the videos and music you love") as evidence the video matches the rule"""


def build_single_shot_matching_prompt(user_description: str, metadata_str: str) -> str:
    """Full user message for legacy single-shot JSON response (fallback)."""
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

{MATCHING_POLICY_RULES}"""


def build_react_system_prompt() -> str:
    """System prompt for the ReAct metadata agent."""
    return f"""You are a specialist agent that decides whether a YouTube video's metadata matches a user's blocking rule.

You have two tools:
- get_match_context: returns the user rule, formatted video metadata, URL, and precomputed embedding similarity between the rule and metadata (read-only signal).
- submit_match_decision: REQUIRED when you are done — pass matches (boolean), confidence (0.0–1.0), and a short reasoning string.

Procedure:
1. Call get_match_context first to load all evidence.
2. Reason about whether the video clearly falls under the rule.
3. Call submit_match_decision exactly once with your final structured decision.

{MATCHING_POLICY_RULES}"""
