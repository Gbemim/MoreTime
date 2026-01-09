/**
 * Type definitions for the extension
 */

export type ScheduleType = 'duration' | 'daily';

export interface DurationSchedule {
  type: 'duration';
  durationMinutes: number;
  startTime: number; // Unix timestamp when blocking started
}

export interface DailySchedule {
  type: 'daily';
  daysOfWeek: number[]; // 0 = Sunday, 1 = Monday, ..., 6 = Saturday
  startTime: string; // "HH:MM" format
  endTime: string; // "HH:MM" format
}

export type Schedule = DurationSchedule | DailySchedule;

export interface BlockRule {
  id: string;
  userDescription: string;
  aiSummary: string;
  patterns: Array<{
    pattern: string;
    reason: string;
  }>;
  schedule: Schedule;
  enabled: boolean;
  createdAt: number; // Unix timestamp
}

export interface GenerateRulesRequest {
  description: string;
}

export interface GenerateRulesResponse {
  summary: string;
}