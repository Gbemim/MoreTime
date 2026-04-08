/**
 * Background service worker for the MoreTime extension
 * Handles messaging and backend API orchestration for rule management
 * Blocking is performed via metadata analysis in content scripts
 */

import { BlockRule } from '../types';
import { MESSAGE_TYPES } from '../constants';
import { debug, error as logError } from '../utils/logger';
import { checkMetadata, deleteRule, generateRules, getRules, saveRule, toggleRule } from './api';
import { redirectToBlocked } from './redirect';

type CreateRuleInput = {
  userDescription: string;
  aiSummary: string;
  schedule: BlockRule['schedule'];
};

/**
 * Get active rules based on schedules
 */
async function getActiveRules(): Promise<BlockRule[]> {
  const response = await getRules(true);
  return response.rules as BlockRule[];
}

/**
 * Apply blocking rules - metadata-based blocking is handled by content scripts
 * This function cleans up any legacy URL-based rules when declarativeNetRequest is available
 */
async function applyBlockingRules(activeRules: BlockRule[]): Promise<void> {
  try {
    // Clean up legacy URL-based rules only if declarativeNetRequest permission is present
    if (chrome.declarativeNetRequest) {
      const existingRules = await chrome.declarativeNetRequest.getDynamicRules();
      const existingRuleIds = existingRules.map(rule => rule.id);
      if (existingRuleIds.length > 0) {
        await chrome.declarativeNetRequest.updateDynamicRules({
          removeRuleIds: existingRuleIds,
        });
        debug(`Removed ${existingRuleIds.length} legacy URL-based rule(s)`);
      }
    }

    // Metadata-based blocking is handled by content scripts
    if (activeRules.length > 0) {
      debug(`${activeRules.length} active rule(s) — blocking via metadata analysis`);
    } else {
      debug('No active blocking rules');
    }
  } catch (error) {
    logError('Error applying blocking rules:', error);
  }
}

/**
 * Evaluate schedules and update blocking rules
 * Called on extension lifecycle events
 */
async function evaluateAndUpdateRules(): Promise<void> {
  const activeRules = await getActiveRules();
  await applyBlockingRules(activeRules);
}

/** Inject metadata checker into one tab. */
async function ensureMetadataCheckerInjected(tabId: number): Promise<void> {
  try {
    await chrome.scripting.executeScript({
      target: { tabId },
      files: ['content/metadata-checker.js'],
    });
    debug(`Injected metadata checker into tab ${tabId}`);
  } catch (error) {
    // Ignore tabs where injection is not allowed (e.g., special pages/races).
    debug(`Skipping injection for tab ${tabId}:`, error);
  }
}

/** Inject into YouTube tabs that were already open. */
async function injectIntoExistingYouTubeTabs(): Promise<void> {
  try {
    const tabs = await chrome.tabs.query({ url: ['https://www.youtube.com/*'] });
    await Promise.all(
      tabs
        .map((tab) => tab.id)
        .filter((id): id is number => typeof id === 'number')
        .map((id) => ensureMetadataCheckerInjected(id))
    );
  } catch (error) {
    logError('Failed to inject into existing YouTube tabs:', error);
  }
}

/**
 * Handle message from popup or content scripts
 */
async function handleMessage(
  message: { type: string; [key: string]: unknown },
  sender: chrome.runtime.MessageSender
): Promise<{ success: boolean; [key: string]: unknown }> {
  switch (message.type) {
    case MESSAGE_TYPES.GENERATE_RULES: {
      const rules = await generateRules(message.description as string);
      return { success: true, data: rules };
    }

    case MESSAGE_TYPES.GET_RULES: {
      const response = await getRules(false);
      const allRules = response.rules as BlockRule[];
      return { success: true, rules: allRules };
    }

    case MESSAGE_TYPES.GET_ACTIVE_RULES: {
      const activeRules = await getActiveRules();
      return { success: true, rules: activeRules };
    }

    case MESSAGE_TYPES.SAVE_RULE: {
      const inputRule = message.rule as CreateRuleInput;
      const createdRule = (await saveRule({
        userDescription: inputRule.userDescription,
        aiSummary: inputRule.aiSummary,
        schedule: inputRule.schedule,
      })) as BlockRule;
      await evaluateAndUpdateRules(); // Update blocking immediately
      return { success: true, rule: createdRule };
    }

    case MESSAGE_TYPES.TOGGLE_RULE: {
      const updated = (await toggleRule(message.ruleId as string, message.enabled as boolean)) as BlockRule;
      await evaluateAndUpdateRules();
      return { success: true, rule: updated };
    }

    case MESSAGE_TYPES.DELETE_RULE: {
      await deleteRule(message.ruleId as string);
      await evaluateAndUpdateRules();
      return { success: true };
    }

    case MESSAGE_TYPES.CHECK_METADATA: {
      const checkResult = await checkMetadata(
        message.rule_id as string,
        message.user_description as string,
        message.url as string,
        message.metadata as Record<string, unknown> | undefined
      );
      return { success: true, result: checkResult };
    }

    case MESSAGE_TYPES.REDIRECT_TO_BLOCKED: {
      const tabId = sender.tab?.id;
      if (!tabId) {
        return { success: false, error: 'No tab ID available' };
      }

      try {
        await redirectToBlocked(tabId, {
          rule: message.rule as string,
          scheduleType: message.scheduleType as string,
          timeRemaining: message.timeRemaining as string | undefined,
          blockEndsAt: message.blockEndsAt as number | undefined,
          description: message.description as string | undefined,
        });
        return { success: true };
      } catch (error) {
        logError('Error redirecting:', error);
        return { success: false, error: (error as Error).message };
      }
    }

    default:
      return { success: false, error: 'Unknown message type' };
  }
}

/**
 * Message handler for communication with popup and content scripts
 */
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  (async () => {
    try {
      const response = await handleMessage(message, sender);
      sendResponse(response);
    } catch (error) {
      logError('Message handler error:', error);
      sendResponse({ 
        success: false, 
        error: error instanceof Error ? error.message : String(error) 
      });
    }
  })();

  return true; // Indicates we will send a response asynchronously
});

/**
 * Evaluate rules on startup
 */
chrome.runtime.onStartup.addListener(() => {
  evaluateAndUpdateRules();
  injectIntoExistingYouTubeTabs();
});

chrome.runtime.onInstalled.addListener(() => {
  evaluateAndUpdateRules();
  injectIntoExistingYouTubeTabs();
});

// Initial evaluation
evaluateAndUpdateRules();
injectIntoExistingYouTubeTabs();