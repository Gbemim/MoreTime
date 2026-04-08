/**
 * Extract Open Graph Protocol metadata from YouTube video pages
 * Focuses specifically on YouTube videos using OGP metadata
 * Runs in page context, so it can access the DOM directly
 */

export interface YouTubeVideoMetadata {
  // Basic OGP properties (required)
  og_title: string;
  og_type: string | null;
  og_description: string | null;
  og_site_name: string | null;

  /** Channel / uploader display names (YouTube supports multiple per video). */
  author_names: string[];

  // Additional YouTube-specific metadata
  url: string;
  video_id: string | null; // Extracted from URL
}

/**
 * Extract Open Graph Protocol metadata from meta tags
 */
function getOgContent(property: string): string | null {
  const meta = document.querySelector(`meta[property="${property}"]`);
  return meta ? (meta.getAttribute('content') || null) : null;
}

/**
 * Extract video ID from YouTube URL
 */
function extractVideoId(url: string): string | null {
  const match = url.match(/(?:youtube\.com\/watch\?v=|youtu\.be\/)([^&\n?#]+)/);
  return match ? match[1] : null;
}

/** Trim, drop empties, dedupe case-insensitively, preserve first-seen casing. */
export function dedupeAuthorNames(names: string[]): string[] {
  const seen = new Set<string>();
  const out: string[] = [];
  for (const raw of names) {
    const t = raw.trim();
    if (!t) continue;
    const key = t.toLowerCase();
    if (seen.has(key)) continue;
    seen.add(key);
    out.push(t);
  }
  return out;
}

function collectAuthorFromJsonLdValue(value: unknown, acc: string[]): void {
  if (value === null || value === undefined) return;
  if (typeof value === 'string') {
    const t = value.trim();
    if (t) acc.push(t);
    return;
  }
  if (Array.isArray(value)) {
    for (const item of value) collectAuthorFromJsonLdValue(item, acc);
    return;
  }
  if (typeof value !== 'object') return;
  const o = value as Record<string, unknown>;
  if (typeof o.name === 'string' && o.name.trim()) {
    acc.push(o.name.trim());
  }
  for (const nestedKey of ['author', 'creator']) {
    if (o[nestedKey] !== undefined) {
      collectAuthorFromJsonLdValue(o[nestedKey], acc);
    }
  }
}

function collectAuthorNamesFromJsonLdNode(node: unknown, acc: string[]): void {
  if (node === null || node === undefined) return;
  if (Array.isArray(node)) {
    for (const item of node) collectAuthorNamesFromJsonLdNode(item, acc);
    return;
  }
  if (typeof node !== 'object') return;
  const o = node as Record<string, unknown>;
  for (const key of ['author', 'creator']) {
    if (o[key] !== undefined) collectAuthorFromJsonLdValue(o[key], acc);
  }
  if (o['@graph'] !== undefined) {
    collectAuthorNamesFromJsonLdNode(o['@graph'], acc);
  }
}

/**
 * Best-effort channel names from JSON-LD (multi-author collabs) and meta author.
 */
function extractAuthorNamesFromDom(): string[] {
  const acc: string[] = [];

  document.querySelectorAll('script[type="application/ld+json"]').forEach((el) => {
    const text = el.textContent?.trim();
    if (!text) return;
    try {
      const data = JSON.parse(text) as unknown;
      collectAuthorNamesFromJsonLdNode(data, acc);
    } catch {
      /* ignore broken JSON */
    }
  });

  const metaAuthor = document.querySelector('meta[name="author"]')?.getAttribute('content');
  if (metaAuthor?.trim()) acc.push(metaAuthor.trim());

  return dedupeAuthorNames(acc);
}

/**
 * Extract YouTube video metadata using Open Graph Protocol
 * Based on https://ogp.me/ specification
 */
export function extractPageMetadata(): YouTubeVideoMetadata {
  // Extract all OGP properties
  const ogTitle = getOgContent('og:title') || document.title || '';
  const ogType = getOgContent('og:type');
  const ogDescription = getOgContent('og:description');
  const ogSiteName = getOgContent('og:site_name');
  const currentUrl = window.location.href;
  const videoId = extractVideoId(currentUrl);
  const author_names = extractAuthorNamesFromDom();

  return {
    // Required OGP properties
    og_title: ogTitle,
    og_type: ogType,

    // Optional OGP properties
    og_description: ogDescription,
    og_site_name: ogSiteName,

    author_names,

    // Additional metadata
    url: currentUrl,
    video_id: videoId,
  };
}

