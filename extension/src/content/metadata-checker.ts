/**
 * Content script that checks if YouTube video matches blocking rules
 * Only runs on YouTube video pages (youtube.com/watch*)
 * Uses Open Graph Protocol metadata to determine if video should be blocked
 */

import { extractPageMetadata, YouTubeVideoMetadata } from './metadata-extractor';
import { BlockRule } from '../types';
import { buildBlockedUrl } from '../utils/url-builder';
import {
  METADATA_CACHE_TTL,
  CONFIDENCE_THRESHOLD,
  MESSAGE_TYPES,
  YOUTUBE_HOSTNAME,
  YOUTUBE_WATCH_PATH,
  NAVIGATION_CHECK_DELAY,
} from '../constants';

// Cache to avoid checking same YouTube video multiple times
const metadataCache = new Map<string, { metadata: YouTubeVideoMetadata; timestamp: number }>();

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

/**
 * Get metadata from cache or extract it
 * 
 * @param cacheKey - Cache key for the metadata
 * @returns YouTube video metadata
 */
function getMetadata(cacheKey: string): YouTubeVideoMetadata {
  const cached = metadataCache.get(cacheKey);
  
  if (cached && Date.now() - cached.timestamp < METADATA_CACHE_TTL) {
    console.log('[MoreTime] Using cached YouTube video metadata');
    return cached.metadata;
  }
  
  // Extract OGP metadata from YouTube video page
  const metadata = extractPageMetadata();
  metadataCache.set(cacheKey, { metadata, timestamp: Date.now() });
  console.log('[MoreTime] Extracted YouTube video OGP metadata:', metadata);
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
  console.log(`[MoreTime] YouTube video matches rule - BLOCKING`);
  
  // Stop any ongoing page loads
  window.stop();
  
  const scheduleType = getScheduleTypeDisplay(rule.schedule.type);
  const description = reasoning || 'This YouTube video matches your blocking rule.';
  
  // Request redirect via background script (required for chrome-extension:// URLs)
  try {
    await chrome.runtime.sendMessage({
      type: MESSAGE_TYPES.REDIRECT_TO_BLOCKED,
      rule: rule.userDescription,
      scheduleType,
      timeRemaining: 'N/A',
      description,
    });
    console.log('[MoreTime] Redirect requested via background script');
  } catch (error) {
    console.error('[MoreTime] Failed to request redirect:', error);
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
  console.log(`[MoreTime] Checking against rule: "${rule.userDescription}"`);
  
  try {
    const response = await chrome.runtime.sendMessage({
      type: MESSAGE_TYPES.CHECK_METADATA,
      user_description: rule.userDescription,
      metadata,
      url,
    });

    if (!response || !response.success || !response.result) {
      console.error(`[MoreTime] Background script error:`, response?.error || 'Unknown error');
      return false;
    }

    const result = response.result;
    console.log('[MoreTime] Backend response:', result);
    console.log(
      `[MoreTime] matches: ${result.matches}, ` +
      `confidence: ${result.confidence}, threshold: ${CONFIDENCE_THRESHOLD}`
    );
    
    // Block if matches=True and confidence meets threshold
    if (result.matches && result.confidence >= CONFIDENCE_THRESHOLD) {
      await handleBlocking(rule, result.reasoning);
      return true;
    }
    
    console.log(
      `[MoreTime] YouTube video does not match ` +
      `(matches: ${result.matches}, confidence: ${result.confidence} < ${CONFIDENCE_THRESHOLD})`
    );
    return false;
  } catch (error) {
    console.error('[MoreTime] Error checking metadata:', error);
    return false;
  }
}

/**
 * Check the current page against all active blocking rules
 */
async function checkPageAgainstRules(): Promise<void> {
  try {
    // Only check YouTube video pages
    if (!isYouTubeVideoPage()) {
      return;
    }
    
    // Don't check if we're on extension pages or the blocked page
    // if (isExtensionOrSystemPage()) {
    //   return;
    // }
    
    console.log('[MoreTime] Checking YouTube video against rules...');
    
    // Get active rules from background
    const response = await chrome.runtime.sendMessage({ 
      type: MESSAGE_TYPES.GET_ACTIVE_RULES 
    });
    
    if (!response || !response.success || !response.rules || response.rules.length === 0) {
      console.log('[MoreTime] No active rules found');
      return;
    }

    const activeRules: BlockRule[] = response.rules;
    const url = window.location.href;
    const domain = window.location.hostname;

    console.log(`[MoreTime] Found ${activeRules.length} active rule(s) for URL: ${url}`);
    console.log('[MoreTime] Active rules:', activeRules.map(r => r.userDescription));

    // Get metadata (from cache or extract)
    const cacheKey = `${domain}-${url}`;
    const metadata = getMetadata(cacheKey);

    // Check against each active rule
    for (const rule of activeRules) {
      const wasBlocked = await checkRuleMatch(rule, metadata, url);
      if (wasBlocked) {
        return; // Stop checking if blocked
      }
    }
    
    console.log('[MoreTime] YouTube video check complete - not blocked');
  } catch (error) {
    console.error('[MoreTime] Error checking YouTube video metadata:', error);
  }
}

// Run check when page is loaded
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', checkPageAgainstRules);
} else {
  checkPageAgainstRules();
}

// Also check on navigation (for SPAs)
let lastUrl = location.href;
new MutationObserver(() => {
  const url = location.href;
  if (url !== lastUrl) {
    lastUrl = url;
    setTimeout(checkPageAgainstRules, NAVIGATION_CHECK_DELAY);
  }
}).observe(document, { subtree: true, childList: true });

