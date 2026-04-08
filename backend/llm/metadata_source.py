"""
Metadata source and merge utilities for YouTube matching.
"""

import asyncio
import json
import re
from html import unescape
from typing import Any, Dict, List
from urllib.parse import quote, urlparse, parse_qs
from urllib.request import urlopen


def metadata_author_names(metadata: Dict[str, Any]) -> List[str]:
    """Channel/uploader names from metadata (list); supports legacy single author_name string."""
    raw = metadata.get("author_names")
    if isinstance(raw, list):
        return [str(x).strip() for x in raw if str(x).strip()]
    legacy = metadata.get("author_name")
    if isinstance(legacy, str) and legacy.strip():
        return [legacy.strip()]
    return []


def dedupe_author_names(names: List[str]) -> List[str]:
    seen = set()
    out: List[str] = []
    for name in names:
        t = str(name).strip()
        if not t:
            continue
        key = t.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(t)
    return out


def extract_video_id(url: str) -> str | None:
    """Extract YouTube video ID from watch/share/shorts URLs."""
    try:
        parsed = urlparse(url)
        host = (parsed.netloc or "").lower()

        # Standard watch URL: /watch?...&v=VIDEO_ID
        if "youtube.com" in host and parsed.path == "/watch":
            video_id = parse_qs(parsed.query).get("v", [None])[0]
            if video_id:
                return video_id

        # Shorts URL: /shorts/VIDEO_ID
        if "youtube.com" in host and parsed.path.startswith("/shorts/"):
            short_id = parsed.path.split("/shorts/", 1)[1].split("/", 1)[0]
            return short_id or None

        # Share URL: youtu.be/VIDEO_ID
        if "youtu.be" in host:
            path_id = parsed.path.strip("/").split("/", 1)[0]
            return path_id or None
    except Exception:
        return None

    return None


async def fetch_youtube_oembed_metadata(url: str) -> Dict[str, Any] | None:
    """
    Fetch main YouTube metadata via oEmbed.
    Returns None on fetch/parse failures or missing title.
    """
    video_id = extract_video_id(url)
    if not video_id:
        return None

    oembed_url = f"https://www.youtube.com/oembed?url={quote(url, safe='')}&format=json"

    def _fetch() -> Dict[str, Any] | None:
        try:
            with urlopen(oembed_url, timeout=8) as res:  # nosec B310
                if res.status != 200:
                    return None
                data = json.loads(res.read().decode("utf-8"))
        except Exception:
            return None

        title = str(data.get("title") or "").strip()
        if not title:
            return None
        channel = str(data.get("author_name") or "").strip()
        authors = dedupe_author_names([channel] if channel else [])
        description = f"Channels: {'; '.join(authors)}" if authors else None
        return {
            "title": title,
            "content_type": data.get("type") or "video",
            "description": description,
            "site_name": data.get("provider_name") or "YouTube",
            "author_names": authors,
            "url": url,
            "video_id": video_id,
        }

    return await asyncio.to_thread(_fetch)


def _extract_og_content(html: str, prop: str) -> str | None:
    pattern = (
        rf'<meta[^>]+property=["\']{re.escape(prop)}["\'][^>]+content=["\']([^"\']+)["\'][^>]*>'
        rf'|<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']{re.escape(prop)}["\'][^>]*>'
    )
    match = re.search(pattern, html, re.IGNORECASE)
    if not match:
        return None
    content = match.group(1) or match.group(2) or ""
    content = unescape(content).strip()
    return content or None


def _extract_meta_author(html: str) -> List[str]:
    pattern = (
        r'<meta[^>]+name=["\']author["\'][^>]+content=["\']([^"\']+)["\'][^>]*>'
        r'|<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']author["\'][^>]*>'
    )
    match = re.search(pattern, html, re.IGNORECASE)
    if not match:
        return []
    author = (match.group(1) or match.group(2) or "").strip()
    return [author] if author else []


async def fetch_youtube_page_metadata_fallback(url: str) -> Dict[str, Any] | None:
    """
    Secondary fallback: fetch page HTML and extract OGP fields.
    Returns None if fetch fails or no useful title is found.
    """
    video_id = extract_video_id(url)
    if not video_id:
        return None

    def _fetch() -> Dict[str, Any] | None:
        try:
            with urlopen(url, timeout=8) as res:  # nosec B310
                if res.status != 200:
                    return None
                html = res.read().decode("utf-8", errors="ignore")
        except Exception:
            return None

        title = _extract_og_content(html, "og:title")
        description = _extract_og_content(html, "og:description")
        content_type = _extract_og_content(html, "og:type")
        site_name = _extract_og_content(html, "og:site_name")
        author_names = dedupe_author_names(_extract_meta_author(html))

        if not title and not description and not author_names:
            return None

        return {
            "title": title,
            "content_type": content_type,
            "description": description,
            "site_name": site_name or "YouTube",
            "author_names": author_names,
            "url": url,
            "video_id": video_id,
        }

    return await asyncio.to_thread(_fetch)


async def resolve_metadata(url: str) -> Dict[str, Any]:
    """
    Resolve metadata source in order:
    1) YouTube oEmbed
    2) Backend OGP page fetch fallback
    """
    metadata = await fetch_youtube_oembed_metadata(url)
    if metadata is None:
        metadata = await fetch_youtube_page_metadata_fallback(url)
    if metadata is None:
        video_id = extract_video_id(url)
        return {
            "title": None,
            "content_type": None,
            "description": None,
            "site_name": "YouTube",
            "author_names": [],
            "url": url,
            "video_id": video_id,
        }
    return metadata

