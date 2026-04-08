/**
 * Constants used throughout the extension
 */

// Backend Configuration (local server; env lives only in backend/.env)
export const BACKEND_URL = 'http://localhost:8000';

/** Set true locally to trace in production builds; `vite` dev always traces via import.meta.env.DEV. */
export const EXTENSION_VERBOSE_LOGS = false;

// Cache Configuration
export const METADATA_CACHE_TTL = 5 * 60 * 1000; // 5 minutes

// Similarity Thresholds
export const CONFIDENCE_THRESHOLD = 0.5;

// Message Types
export const MESSAGE_TYPES = {
  GENERATE_RULES: 'GENERATE_RULES',
  GET_RULES: 'GET_RULES',
  GET_ACTIVE_RULES: 'GET_ACTIVE_RULES',
  SAVE_RULE: 'SAVE_RULE',
  TOGGLE_RULE: 'TOGGLE_RULE',
  DELETE_RULE: 'DELETE_RULE',
  CHECK_METADATA: 'CHECK_METADATA',
  /** oEmbed must be fetched from the service worker (page CSP blocks many content-script fetches). */
  GET_YOUTUBE_OEMBED_METADATA: 'GET_YOUTUBE_OEMBED_METADATA',
  REDIRECT_TO_BLOCKED: 'REDIRECT_TO_BLOCKED',
} as const;

// Alarm Names
export const ALARM_NAMES = {
  EVALUATE_RULES: 'evaluateRules',
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

