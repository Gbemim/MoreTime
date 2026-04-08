/**
 * Extension logging: production builds stay quiet; dev builds and EXTENSION_VERBOSE_LOGS enable traces.
 * Prefer errors in the service worker; content scripts stay nearly silent in production.
 */

import { EXTENSION_VERBOSE_LOGS } from '../constants';

const isVerbose = import.meta.env.DEV || EXTENSION_VERBOSE_LOGS;

export function debug(...args: unknown[]): void {
  if (!isVerbose) return;
  console.log('[MoreTime]', ...args);
}

export function error(...args: unknown[]): void {
  console.error('[MoreTime]', ...args);
}
