/**
 * Constants used throughout the extension
 */

// Backend Configuration (local server; env lives only in backend/.env)
export const BACKEND_URL =
  import.meta.env.VITE_BACKEND_URL || 'https://moretime-production.up.railway.app';
export const BACKEND_TENANT_ID = 'default-tenant';
export const BACKEND_API_KEY = '';

/** Set true locally to trace in production builds; `vite` dev always traces via import.meta.env.DEV. */
export const EXTENSION_VERBOSE_LOGS = true;

// Message Types
export const MESSAGE_TYPES = {
  GENERATE_RULES: 'GENERATE_RULES',
  GET_RULES: 'GET_RULES',
  GET_ACTIVE_RULES: 'GET_ACTIVE_RULES',
  SAVE_RULE: 'SAVE_RULE',
  TOGGLE_RULE: 'TOGGLE_RULE',
  DELETE_RULE: 'DELETE_RULE',
  CHECK_METADATA: 'CHECK_METADATA',
  REDIRECT_TO_BLOCKED: 'REDIRECT_TO_BLOCKED',
} as const;

// Storage Keys
export const STORAGE_KEYS = {
  RULES: 'rules',
} as const;

// YouTube Detection
export const YOUTUBE_HOSTNAME = 'www.youtube.com';
export const YOUTUBE_WATCH_PATH = '/watch';

// Day Names
export const DAY_NAMES = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'] as const;

// Navigation Delay (for SPAs)
export const NAVIGATION_CHECK_DELAY = 1000; // 1 second

