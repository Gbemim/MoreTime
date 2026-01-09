/**
 * Storage utilities for managing rules
 */

import { BlockRule } from '../types';
import { STORAGE_KEYS } from '../constants';

/**
 * Get all saved rules from storage
 * 
 * @returns Promise resolving to array of saved rules
 */
export async function getRules(): Promise<BlockRule[]> {
  const result = await chrome.storage.local.get([STORAGE_KEYS.RULES]);
  return result[STORAGE_KEYS.RULES] || [];
}

/**
 * Save rules to storage
 * 
 * @param rules - Array of rules to save
 */
export async function saveRules(rules: BlockRule[]): Promise<void> {
  await chrome.storage.local.set({ [STORAGE_KEYS.RULES]: rules });
}

