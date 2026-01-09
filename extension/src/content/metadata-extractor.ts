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

  return {
    // Required OGP properties
    og_title: ogTitle,
    og_type: ogType,
    
    // Optional OGP properties
    og_description: ogDescription,
    og_site_name: ogSiteName,

    // Additional metadata
    url: currentUrl,
    video_id: videoId,
  };
}

