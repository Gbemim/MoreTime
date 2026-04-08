/**
 * API client for backend communication
 */

import { GenerateRulesResponse } from '../types';
import { BACKEND_API_KEY, BACKEND_FALLBACK_URL, BACKEND_TENANT_ID, BACKEND_URL } from '../constants';
import { debug, error as logError } from '../utils/logger';

export interface CheckMetadataResult {
  matches: boolean;
  block: boolean;
  confidence: number;
  reasoning: string;
  reason_code: string;
  decision_id: string;
  matched_rule_id: string | null;
  model_name: string;
  evaluated_at: number;
}

const LEGACY_CONFIDENCE_THRESHOLD = 0.5;

function buildHeaders(): Record<string, string> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    'X-Tenant-Id': BACKEND_TENANT_ID,
  };
  if (BACKEND_API_KEY.trim()) {
    headers['X-API-Key'] = BACKEND_API_KEY.trim();
  }
  return headers;
}

async function fetchBackend(path: string, init: RequestInit): Promise<Response> {
  try {
    return await fetch(`${BACKEND_URL}${path}`, init);
  } catch (error) {
    if (!BACKEND_FALLBACK_URL) {
      throw error;
    }
    debug(`Primary backend failed, falling back: ${BACKEND_URL} -> ${BACKEND_FALLBACK_URL}`);
    return fetch(`${BACKEND_FALLBACK_URL}${path}`, init);
  }
}

/**
 * Call the backend API to generate block rules
 * 
 * @param description - User's description of videos to block
 * @returns Promise resolving to generated rules response
 * @throws Error if the request fails
 */
export async function generateRules(description: string): Promise<GenerateRulesResponse> {
  try {
    const response = await fetchBackend('/generate-block-rules', {
      method: 'POST',
      headers: buildHeaders(),
      body: JSON.stringify({ description }),
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Backend error (${response.status}): ${errorText || response.statusText}`);
    }

    return response.json();
  } catch (error) {
    if (error instanceof Error) {
      throw error;
    }
    throw new Error(`Failed to generate rules: ${String(error)}`);
  }
}

/**
 * Check if URL matches a rule by calling the backend
 * This is called from content scripts via message passing to avoid CORS issues
 * 
 * @param userDescription - User's blocking rule description
 * @param url - Website URL
 * @returns Promise resolving to check result
 * @throws Error if the request fails
 */
export async function checkMetadata(
  ruleId: string,
  userDescription: string,
  url: string
): Promise<CheckMetadataResult> {
  debug('check-metadata', url);

  try {
    const response = await fetchBackend('/check-metadata', {
      method: 'POST',
      headers: buildHeaders(),
      body: JSON.stringify({
        rule_id: ruleId,
        user_description: userDescription,
        url,
      }),
    });

    if (!response.ok) {
      const errorText = await response.text();
      logError(`Backend error (${response.status}):`, errorText);
      throw new Error(`Backend error (${response.status}): ${errorText || response.statusText}`);
    }

    const result = await response.json();
    const matches = Boolean(result.matches);
    const confidence = Number(result.confidence ?? 0);
    const block =
      typeof result.block === 'boolean'
        ? result.block
        : matches && confidence >= LEGACY_CONFIDENCE_THRESHOLD;

    const normalized: CheckMetadataResult = {
      matches,
      block,
      confidence,
      reasoning: String(result.reasoning ?? ''),
      reason_code: String(result.reason_code ?? 'legacy_backend_response'),
      decision_id: String(result.decision_id ?? ''),
      matched_rule_id: result.matched_rule_id ?? null,
      model_name: String(result.model_name ?? ''),
      evaluated_at: Number(result.evaluated_at ?? Date.now()),
    };
    debug('check-metadata done', {
      matches: normalized.matches,
      block: normalized.block,
      confidence: normalized.confidence,
    });
    return normalized;
  } catch (error) {
    if (error instanceof Error) {
      throw error;
    }
    throw new Error(`Failed to check metadata: ${String(error)}`);
  }
}


export async function getRules(activeOnly = false): Promise<{ rules: unknown[] }> {
  const response = await fetchBackend(`/rules?active_only=${activeOnly ? 'true' : 'false'}`, {
    method: 'GET',
    headers: buildHeaders(),
  });
  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Backend error (${response.status}): ${errorText || response.statusText}`);
  }
  return response.json();
}

export async function saveRule(rule: {
  userDescription: string;
  aiSummary: string;
  schedule: unknown;
}): Promise<unknown> {
  const response = await fetchBackend('/rules', {
    method: 'POST',
    headers: buildHeaders(),
    body: JSON.stringify(rule),
  });
  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Backend error (${response.status}): ${errorText || response.statusText}`);
  }
  return response.json();
}

export async function toggleRule(ruleId: string, enabled: boolean): Promise<unknown> {
  const response = await fetchBackend(`/rules/${ruleId}`, {
    method: 'PATCH',
    headers: buildHeaders(),
    body: JSON.stringify({ enabled }),
  });
  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Backend error (${response.status}): ${errorText || response.statusText}`);
  }
  return response.json();
}

export async function deleteRule(ruleId: string): Promise<void> {
  const response = await fetchBackend(`/rules/${ruleId}`, {
    method: 'DELETE',
    headers: buildHeaders(),
  });
  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Backend error (${response.status}): ${errorText || response.statusText}`);
  }
}
