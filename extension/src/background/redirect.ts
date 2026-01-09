/**
 * Redirect utilities for blocked pages
 */

import { buildBlockedUrl } from '../utils/url-builder';

export interface RedirectParams {
  rule: string;
  scheduleType: string;
  timeRemaining?: string;
  description?: string;
}

/**
 * Redirect a tab to the blocked page
 * 
 * @param tabId - ID of the tab to redirect
 * @param params - Parameters for the blocked page
 */
export async function redirectToBlocked(
  tabId: number,
  params: RedirectParams
): Promise<void> {
  const blockedUrl = buildBlockedUrl(params);
  console.log(`[MoreTime] Redirecting tab ${tabId} to: ${blockedUrl}`);
  await chrome.tabs.update(tabId, { url: blockedUrl });
}

