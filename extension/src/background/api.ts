/**
 * API client for backend communication
 */

import { GenerateRulesResponse } from '../types';
import { BACKEND_URL } from '../constants';
import { debug, error as logError } from '../utils/logger';

export interface CheckMetadataResult {
  matches: boolean;
  confidence: number;
  reasoning: string;
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
    const response = await fetch(`${BACKEND_URL}/generate-block-rules`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
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
 * Check if metadata matches a rule by calling the backend
 * This is called from content scripts via message passing to avoid CORS issues
 * 
 * @param userDescription - User's blocking rule description
 * @param metadata - Website metadata to check
 * @param url - Website URL
 * @param videoTitle - Video title (optional enricher for backend)
 * @param videoDescription - Video description (optional enricher for backend)
 * @returns Promise resolving to check result
 * @throws Error if the request fails
 */
export async function checkMetadata(
  userDescription: string,
  metadata: Record<string, unknown>,
  url: string,
  videoTitle: string,
  videoDescription: string
): Promise<CheckMetadataResult> {
  debug('check-metadata', url);

  try {
    const response = await fetch(`${BACKEND_URL}/check-metadata`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        user_description: userDescription,
        metadata,
        url,
        videoDescription,
        videoTitle
      }),
    });

    if (!response.ok) {
      const errorText = await response.text();
      logError(`Backend error (${response.status}):`, errorText);
      throw new Error(`Backend error (${response.status}): ${errorText || response.statusText}`);
    }

    const result = await response.json();
    debug('check-metadata done', {
      matches: result.matches,
      confidence: result.confidence,
    });
    return result;
  } catch (error) {
    if (error instanceof Error) {
      throw error;
    }
    throw new Error(`Failed to check metadata: ${String(error)}`);
  }
}
