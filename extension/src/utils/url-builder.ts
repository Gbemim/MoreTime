/**
 * Utility functions for building URLs
 */

/**
 * Build the blocked page URL with query parameters
 */
export function buildBlockedUrl(params: {
  rule: string;
  scheduleType: string;
  timeRemaining?: string;
  description?: string;
}): string {
  const blockedUrl = chrome.runtime.getURL('blocked.html');
  const queryParams = new URLSearchParams({
    rule: params.rule,
    scheduleType: params.scheduleType,
    timeRemaining: params.timeRemaining || 'N/A',
    description: params.description || 'This website matches your blocking rule.',
  });
  
  return `${blockedUrl}?${queryParams.toString()}`;
}

