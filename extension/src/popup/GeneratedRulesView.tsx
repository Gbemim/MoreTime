import React from 'react';
import { GenerateRulesResponse, Schedule } from '../types';
import { DAY_NAMES } from '../constants';
import { styles } from './styles';

interface GeneratedRulesViewProps {
  rules: GenerateRulesResponse;
  schedule: Schedule | null;
  onSave: () => void;
}

/**
 * Format schedule for display
 */
function formatSchedule(schedule: Schedule | null): string {
  if (!schedule) return 'No schedule';
  
  if (schedule.type === 'duration') {
    const hours = Math.floor(schedule.durationMinutes / 60);
    const minutes = schedule.durationMinutes % 60;
    return `Block for ${hours}h ${minutes}m starting now`;
  }
  
  const days = schedule.daysOfWeek.map((d) => DAY_NAMES[d]).join(', ');
  return `${days} from ${schedule.startTime} to ${schedule.endTime}`;
}

export const GeneratedRulesView: React.FC<GeneratedRulesViewProps> = ({ 
  rules, 
  schedule, 
  onSave 
}) => {
  return (
    <div style={styles.card}>
      <h3 style={styles.heading3}>Generated Block Rules</h3>

      <div style={{ marginBottom: '12px' }}>
        <strong>Summary:</strong>
        <p style={styles.textMultiline}>{rules.summary}</p>
      </div>

      <div style={{ marginBottom: '12px' }}>
        <strong>Schedule:</strong>
        <p style={styles.text}>{formatSchedule(schedule)}</p>
      </div>

      <button onClick={onSave} style={styles.buttonSecondary}>
        Save Rule
      </button>
    </div>
  );
};



