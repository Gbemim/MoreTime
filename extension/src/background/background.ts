/**
 * Background service worker for the MoreTime extension
 * Handles messaging, storage, schedule evaluation, and rule management
 * Blocking is performed via metadata analysis in content scripts
 */

import { BlockRule } from '../types';
import { MESSAGE_TYPES, ALARM_NAMES } from '../constants';
import { getRules, saveRules } from './storage';
import { filterActiveRules } from './utils';
import { generateRules, checkMetadata } from './api';
import { redirectToBlocked } from './redirect';


/**
 * Get active rules based on schedules
 */
async function getActiveRules(): Promise<BlockRule[]> {
  const allRules = await getRules();
  return filterActiveRules(allRules);
}

/**
 * Apply blocking rules - metadata-based blocking is handled by content scripts
 * This function now only cleans up any legacy URL-based rules
 */
async function applyBlockingRules(activeRules: BlockRule[]): Promise<void> {
  try {
    // Get existing rules to clean up (legacy URL-based rules)
    const existingRules = await chrome.declarativeNetRequest.getDynamicRules();
    const existingRuleIds = existingRules.map(rule => rule.id);

    // Remove all existing URL-based rules since we use metadata analysis only
    if (existingRuleIds.length > 0) {
      await chrome.declarativeNetRequest.updateDynamicRules({
        removeRuleIds: existingRuleIds,
      });
      console.log(`[MoreTime] Removed ${existingRuleIds.length} legacy URL-based rule(s)`);
    }

    // Metadata-based blocking is handled by content scripts
    if (activeRules.length > 0) {
      console.log(`[MoreTime] ${activeRules.length} active rule(s) - blocking via metadata analysis`);
    } else {
      console.log('[MoreTime] No active blocking rules');
    }
  } catch (error) {
    console.error('[MoreTime] Error applying blocking rules:', error);
  }
}

/**
 * Evaluate schedules and update blocking rules
 * Called periodically via chrome.alarms
 */
async function evaluateAndUpdateRules(): Promise<void> {
  const activeRules = await getActiveRules();
  await applyBlockingRules(activeRules);
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
      const allRules = await getRules();
      return { success: true, rules: allRules };
    }

    case MESSAGE_TYPES.GET_ACTIVE_RULES: {
      const activeRules = await getActiveRules();
      return { success: true, rules: activeRules };
    }

    case MESSAGE_TYPES.SAVE_RULE: {
      const currentRules = await getRules();
      currentRules.push(message.rule as BlockRule);
      await saveRules(currentRules);
      await evaluateAndUpdateRules(); // Update blocking immediately
      return { success: true };
    }

    case MESSAGE_TYPES.TOGGLE_RULE: {
      const rulesToToggle = await getRules();
      const ruleIndex = rulesToToggle.findIndex((r) => r.id === message.ruleId);
      if (ruleIndex !== -1) {
        rulesToToggle[ruleIndex].enabled = message.enabled as boolean;
        await saveRules(rulesToToggle);
        await evaluateAndUpdateRules();
        return { success: true };
      }
      return { success: false, error: 'Rule not found' };
    }

    case MESSAGE_TYPES.DELETE_RULE: {
      const rulesToDelete = await getRules();
      const filteredRules = rulesToDelete.filter((r) => r.id !== message.ruleId);
      await saveRules(filteredRules);
      await evaluateAndUpdateRules();
      return { success: true };
    }

    case MESSAGE_TYPES.CHECK_METADATA: {
      const checkResult = await checkMetadata(
        message.user_description as string,
        message.metadata as Record<string, unknown>,
        message.url as string
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
          description: message.description as string | undefined,
        });
        return { success: true };
      } catch (error) {
        console.error('[MoreTime] Error redirecting:', error);
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
      sendResponse({ 
        success: false, 
        error: error instanceof Error ? error.message : String(error) 
      });
    }
  })();

  return true; // Indicates we will send a response asynchronously
});

/**
 * Set up periodic alarm to evaluate schedules
 * This runs every minute to check if rules should be activated/deactivated
 */
chrome.alarms.create(ALARM_NAMES.EVALUATE_RULES, { periodInMinutes: 1 });

chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === ALARM_NAMES.EVALUATE_RULES) {
    evaluateAndUpdateRules();
  }
});

/**
 * Evaluate rules on startup
 */
chrome.runtime.onStartup.addListener(() => {
  evaluateAndUpdateRules();
});

chrome.runtime.onInstalled.addListener(() => {
  evaluateAndUpdateRules();
});

// Initial evaluation
evaluateAndUpdateRules();