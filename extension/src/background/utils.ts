/**
 * Utility functions for schedule evaluation and rule management
 */

import { BlockRule, DurationSchedule, DailySchedule } from '../types';

/**
 * Check if a duration-based schedule is currently active
 * 
 * @param schedule - Duration schedule to check
 * @returns True if the schedule is currently active
 */
export function isDurationActive(schedule: DurationSchedule): boolean {
  const now = Date.now();
  const endTime = schedule.startTime + schedule.durationMinutes * 60 * 1000;
  return now >= schedule.startTime && now < endTime;
}

/**
 * Parse time string (HH:MM) to minutes since midnight
 * 
 * @param timeStr - Time string in HH:MM format
 * @returns Minutes since midnight
 */
function parseTimeToMinutes(timeStr: string): number {
  const [hour, minute] = timeStr.split(':').map(Number);
  return hour * 60 + minute;
}

/**
 * Check if a daily schedule is currently active
 * 
 * @param schedule - Daily schedule to check
 * @returns True if the schedule is currently active
 */
export function isDailyActive(schedule: DailySchedule): boolean {
  const now = new Date();
  const currentDay = now.getDay(); // 0 = Sunday, 6 = Saturday
  const currentTime = now.getHours() * 60 + now.getMinutes(); // minutes since midnight

  // Check if today is in the schedule
  if (!schedule.daysOfWeek.includes(currentDay)) {
    return false;
  }

  // Parse start and end times
  const startMinutes = parseTimeToMinutes(schedule.startTime);
  const endMinutes = parseTimeToMinutes(schedule.endTime);

  // Handle schedules that span midnight
  if (endMinutes < startMinutes) {
    return currentTime >= startMinutes || currentTime < endMinutes;
  }
  
  return currentTime >= startMinutes && currentTime < endMinutes;
}

/**
 * Determine which rules are currently active based on their schedules
 * 
 * @param rules - Array of rules to filter
 * @returns Array of currently active rules
 */
export function filterActiveRules(rules: BlockRule[]): BlockRule[] {
  return rules.filter((rule) => {
    if (!rule.enabled) {
      return false;
    }

    if (rule.schedule.type === 'duration') {
      return isDurationActive(rule.schedule);
    }
    
    return isDailyActive(rule.schedule);
  });
}

