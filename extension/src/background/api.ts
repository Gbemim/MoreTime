/**
 * API client for backend communication
 */

import { GenerateRulesResponse } from '../types';
import { BACKEND_URL } from '../constants';

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
 * @returns Promise resolving to check result
 * @throws Error if the request fails
 */
export async function checkMetadata(
  userDescription: string,
  metadata: Record<string, unknown>,
  url: string
): Promise<CheckMetadataResult> {
  console.log(`[Background] Checking metadata for URL: ${url}`);
  console.log(`[Background] User description: ${userDescription}`);
  
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
      }),
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error(`[Background] Backend error (${response.status}):`, errorText);
      throw new Error(`Backend error (${response.status}): ${errorText || response.statusText}`);
    }

    const result = await response.json();
    console.log(`[Background] Backend response:`, result);
    return result;
  } catch (error) {
    if (error instanceof Error) {
      throw error;
    }
    throw new Error(`Failed to check metadata: ${String(error)}`);
  }
}

