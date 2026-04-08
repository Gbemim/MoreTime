/**
 * Content script that checks if YouTube video matches blocking rules
 * Only runs on YouTube video pages (youtube.com/watch*)
 * Resolves title/channel via YouTube oEmbed first (instant), then page OGP if needed
 */

import { extractPageMetadata, YouTubeVideoMetadata } from './metadata-extractor';
import { BlockRule } from '../types';
import { buildBlockedUrl } from '../utils/url-builder';
import {
  METADATA_CACHE_TTL,
  CONFIDENCE_THRESHOLD,
  EXTENSION_VERBOSE_LOGS,
  MESSAGE_TYPES,
  YOUTUBE_HOSTNAME,
  YOUTUBE_WATCH_PATH,
  NAVIGATION_CHECK_DELAY,
} from '../constants';

/**
 * Logging stays in this file (not ../utils/logger): the content script is rewritten into a
 * Chrome IIFE by vite.config.ts, which inlines only some chunks and strips imports—importing
 * the shared logger would drop the function definitions and leave bare debug() calls.
 */
const isVerbose = import.meta.env.DEV || EXTENSION_VERBOSE_LOGS;
function debug(...args: unknown[]): void {
  if (!isVerbose) return;
  console.log('[MoreTime]', ...args);
}
function logError(...args: unknown[]): void {
  console.error('[MoreTime]', ...args);
}

// Cache to avoid checking same YouTube video multiple times
const metadataCache = new Map<string, { metadata: YouTubeVideoMetadata; timestamp: number }>();

/** One debounced check after navigation signals; delay lets OGP tags catch up. */
let checkTimer: ReturnType<typeof setTimeout> | null = null;

/** Last watch ?v= we scheduled for — yt-navigate-finish fires often for the same video; ignore duplicates. */
let lastScheduledVideoId: string | null = null;

function scheduleCheck(): void {
  if (checkTimer !== null) {
    clearTimeout(checkTimer);
  }
  checkTimer = setTimeout(() => {
    checkTimer = null;
    void checkPageAgainstRules();
  }, NAVIGATION_CHECK_DELAY);
}

/**
 * Only re-debounce when the watch URL's video id changes (or we left /watch).
 * Otherwise yt-navigate-finish would reset the timer forever and starve checks.
 */
function scheduleCheckOnWatchVideoChange(): void {
  if (!isYouTubeVideoPage()) {
    lastScheduledVideoId = null;
    return;
  }
  const vid = new URLSearchParams(window.location.search).get('v');
  if (vid !== null && vid === lastScheduledVideoId) {
    return;
  }
  lastScheduledVideoId = vid;
  scheduleCheck();
}

/**
 * YouTube watch: `yt-navigate-finish` after real navigations; `popstate` for back/forward.
 */
function installWatchNavListeners(): void {
  window.addEventListener('popstate', scheduleCheckOnWatchVideoChange);
  document.addEventListener('yt-navigate-finish', scheduleCheckOnWatchVideoChange);
}

/**
 * Returns true if the extension context is still valid (extension not reloaded/disabled).
 * After reload, content scripts keep running but chrome.runtime is invalidated.
 */
function isExtensionContextValid(): boolean {
  try {
    return typeof chrome !== 'undefined' && !!chrome.runtime?.id;
  } catch {
    return false;
  }
}

/**
 * Check if an error is due to extension context being invalidated (e.g. after reload).
 */
function isContextInvalidatedError(error: unknown): boolean {
  const msg = error instanceof Error ? error.message : String(error);
  return msg.includes('Extension context invalidated');
}

/**
 * Check if current page is a YouTube video page
 * 
 * @returns True if the current page is a YouTube video page
 */
function isYouTubeVideoPage(): boolean {
  const hostname = window.location.hostname;
  return hostname === YOUTUBE_HOSTNAME && window.location.pathname.includes(YOUTUBE_WATCH_PATH);
}

// /**
//  * Check if current URL is an extension or system page
//  * 
//  * @returns True if the URL should be ignored
//  */
// function isExtensionOrSystemPage(): boolean {
//   const currentUrl = window.location.href;
//   return (
//     window.location.protocol === 'chrome-extension:' ||
//     currentUrl.includes('blocked.html') ||
//     currentUrl.includes('chrome://') ||
//     currentUrl.includes('chrome-extension://')
//   );
// }

async function fetchOembedFromBackground(watchUrl: string): Promise<YouTubeVideoMetadata | null> {
  if (!isExtensionContextValid()) return null;
  try {
    const response = (await chrome.runtime.sendMessage({
      type: MESSAGE_TYPES.GET_YOUTUBE_OEMBED_METADATA,
      watchUrl,
    })) as { success?: boolean; metadata?: YouTubeVideoMetadata };
    if (!response?.success || !response.metadata) return null;
    return response.metadata;
  } catch {
    return null;
  }
}

/**
 * Resolve metadata: oEmbed via background (not blocked by page CSP), then DOM OGP fallback.
 */
async function getMetadata(cacheKey: string, watchUrl: string): Promise<YouTubeVideoMetadata> {
  const cached = metadataCache.get(cacheKey);

  if (cached && Date.now() - cached.timestamp < METADATA_CACHE_TTL) {
    debug('Using cached YouTube video metadata');
    return cached.metadata;
  }

  const fromOembed = await fetchOembedFromBackground(watchUrl);
  const metadata = fromOembed ?? extractPageMetadata();
  metadataCache.set(cacheKey, { metadata, timestamp: Date.now() });
  debug('YouTube metadata:', fromOembed ? 'oEmbed' : 'DOM OGP', metadata);
  return metadata;
}

/**
 * Get schedule type display string
 * 
 * @param scheduleType - Schedule type from rule
 * @returns Display string for schedule type
 */
function getScheduleTypeDisplay(scheduleType: 'duration' | 'daily'): string {
  return scheduleType === 'duration' ? 'Duration Block' : 'Daily Schedule';
}

/**
 * Handle blocking when a video matches a rule
 * 
 * @param rule - The rule that matched
 * @param reasoning - Reasoning from the backend
 */
async function handleBlocking(rule: BlockRule, reasoning: string): Promise<void> {
  debug('YouTube video matches rule — blocking');

  const scheduleType = getScheduleTypeDisplay(rule.schedule.type);
  const description = reasoning || 'This YouTube video matches your blocking rule.';
  
  if (!isExtensionContextValid()) return;

  // Request redirect via background script (required for chrome-extension:// URLs)
  try {
    await chrome.runtime.sendMessage({
      type: MESSAGE_TYPES.REDIRECT_TO_BLOCKED,
      rule: rule.userDescription,
      scheduleType,
      timeRemaining: 'N/A',
      description,
    });
    debug('Redirect requested via background script');
  } catch (error) {
    if (isContextInvalidatedError(error)) return;
    logError('Failed to request redirect:', error);
    // If background redirect fails, try direct redirect as last resort
    const blockedUrl = buildBlockedUrl({
      rule: rule.userDescription,
      scheduleType,
      timeRemaining: 'N/A',
      description,
    });
    window.location.replace(blockedUrl);
  }
}

/**
 * Check if a video matches a rule and handle blocking if needed
 * 
 * @param rule - Rule to check against
 * @param metadata - Video metadata
 * @param url - Video URL
 * @returns True if the video was blocked
 */
async function checkRuleMatch(
  rule: BlockRule,
  metadata: YouTubeVideoMetadata,
  url: string
): Promise<boolean> {
  if (!isExtensionContextValid()) return false;

  debug(`Checking against rule: "${rule.userDescription}"`);
  
  try {
    const response = await chrome.runtime.sendMessage({
      type: MESSAGE_TYPES.CHECK_METADATA,
      user_description: rule.userDescription,
      metadata,
      url,
    });

    if (!response || !response.success || !response.result) {
      logError('Background script error:', response?.error || 'Unknown error');
      return false;
    }

    const result = response.result;
    debug('Metadata check result:', {
      matches: result.matches,
      confidence: result.confidence,
      threshold: CONFIDENCE_THRESHOLD,
    });
    
    // Block if matches=True and confidence meets threshold
    if (result.matches && result.confidence >= CONFIDENCE_THRESHOLD) {
      await handleBlocking(rule, result.reasoning);
      return true;
    }
    
    debug(
      'YouTube video does not match',
      { matches: result.matches, confidence: result.confidence, threshold: CONFIDENCE_THRESHOLD }
    );
    return false;
  } catch (error) {
    if (isContextInvalidatedError(error)) return false;
    logError('Error checking metadata:', error);
    return false;
  }
}

/**
 * Check the current page against all active blocking rules
 */
async function checkPageAgainstRules(): Promise<void> {
  try {
    if (!isExtensionContextValid()) return;

    // Only check YouTube video pages
    if (!isYouTubeVideoPage()) {
      return;
    }
    
    // Don't check if we're on extension pages or the blocked page
    // if (isExtensionOrSystemPage()) {
    //   return;
    // }
    
    debug('Checking YouTube video against rules…');
    
    // Get active rules from background
    const response = await chrome.runtime.sendMessage({ 
      type: MESSAGE_TYPES.GET_ACTIVE_RULES 
    });
    
    if (!response || !response.success || !response.rules || response.rules.length === 0) {
      debug('No active rules found');
      return;
    }

    const activeRules: BlockRule[] = response.rules;
    const url = window.location.href;
    const domain = window.location.hostname;

    debug(`Found ${activeRules.length} active rule(s)`, url, activeRules.map((r) => r.userDescription));

    const cacheKey = `${domain}-${url}`;
    const metadata = await getMetadata(cacheKey, url);

    // Check against each active rule
    for (const rule of activeRules) {
      const wasBlocked = await checkRuleMatch(rule, metadata, url);
      if (wasBlocked) {
        return; // Stop checking if blocked
      }
    }
    
    debug('YouTube video check complete — not blocked');
  } catch (error) {
    if (isContextInvalidatedError(error)) return;
    logError('Error checking YouTube video metadata:', error);
  }
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    installWatchNavListeners();
    scheduleCheckOnWatchVideoChange();
  });
} else {
  installWatchNavListeners();
  scheduleCheckOnWatchVideoChange();
}

