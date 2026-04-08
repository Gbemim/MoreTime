/**
 * YouTube oEmbed fetch — must run in the extension service worker, not a tab content script:
 * fetches from content scripts can be blocked by the *page* CSP (connect-src), even for youtube.com URLs.
 */
import { dedupeAuthorNames, type YouTubeVideoMetadata } from './content/metadata-extractor';

function extractVideoId(url: string): string | null {
  const match = url.match(/(?:youtube\.com\/watch\?v=|youtu\.be\/)([^&\n?#]+)/);
  return match ? match[1] : null;
}

export async function fetchYoutubeOEmbedMetadata(watchUrl: string): Promise<YouTubeVideoMetadata | null> {
  const videoId = extractVideoId(watchUrl);
  if (!videoId) return null;

  const oembedUrl = `https://www.youtube.com/oembed?url=${encodeURIComponent(watchUrl)}&format=json`;
  try {
    const res = await fetch(oembedUrl);
    if (!res.ok) return null;
    const data = (await res.json()) as {
      title?: string;
      author_name?: string;
      provider_name?: string;
      type?: string;
    };
    const title = (data.title ?? '').trim();
    if (!title) return null;

    const channel = (data.author_name ?? '').trim();
    const author_names = dedupeAuthorNames(channel ? [channel] : []);
    const og_description =
      author_names.length > 0 ? `Channels: ${author_names.join('; ')}` : null;
    return {
      og_title: title,
      og_type: data.type ?? 'video',
      og_description,
      og_site_name: data.provider_name ?? 'YouTube',
      author_names,
      url: watchUrl,
      video_id: videoId,
    };
  } catch {
    return null;
  }
}
