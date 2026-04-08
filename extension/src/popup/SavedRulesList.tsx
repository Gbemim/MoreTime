import React from 'react';
import { BlockRule } from '../types';
import { DAY_NAMES } from '../constants';
import { styles } from './styles';

interface SavedRulesListProps {
  rules: BlockRule[];
  onToggle: (ruleId: string, enabled: boolean) => void;
  onDelete: (ruleId: string) => void;
}

/**
 * Format schedule for display
 */
function formatSchedule(schedule: BlockRule['schedule']): string {
  if (schedule.type === 'duration') {
    const hours = Math.floor(schedule.durationMinutes / 60);
    const minutes = schedule.durationMinutes % 60;
    const endDate = new Date(schedule.startTime + schedule.durationMinutes * 60 * 1000);
    
    if (endDate.getTime() < Date.now()) {
      return `Expired (was ${hours}h ${minutes}m)`;
    }
    
    return `Block for ${hours}h ${minutes}m (until ${endDate.toLocaleTimeString()})`;
  }
  
  const days = schedule.daysOfWeek.map((d) => DAY_NAMES[d]).join(', ');
  return `${days} from ${schedule.startTime} to ${schedule.endTime}`;
}

export const SavedRulesList: React.FC<SavedRulesListProps> = ({ 
  rules, 
  onToggle, 
  onDelete 
}) => {
  if (rules.length === 0) {
    return (
      <div style={styles.emptyState}>
        No saved rules yet. Generate and save a rule to get started.
      </div>
    );
  }

  return (
    <div style={{ marginTop: '24px' }}>
      <h2 style={styles.heading2}>Saved Rules</h2>
      {rules.map((rule) => (
        <div
          key={rule.id}
          style={{
            ...styles.ruleCard,
            ...(rule.enabled ? styles.ruleCardActive : styles.ruleCardInactive),
          }}
        >
          <div style={styles.flexBetween}>
            <div style={{ flex: 1 }}>
              <div style={{ fontWeight: 'bold', marginBottom: '4px', fontSize: '14px' }}>
                {rule.userDescription}
              </div>
              <div style={styles.textSmallMultiline}>{rule.aiSummary}</div>
              <div style={styles.textMuted}>Schedule: {formatSchedule(rule.schedule)}</div>
              <div style={styles.textTiny}>Metadata-based blocking</div>
            </div>
            <div style={styles.flexColumn}>
              <label style={styles.checkboxLabel}>
                <input
                  type="checkbox"
                  checked={rule.enabled}
                  onChange={(e) => onToggle(rule.id, e.target.checked)}
                  style={styles.checkbox}
                />
                Active
              </label>
              <button onClick={() => onDelete(rule.id)} style={styles.buttonDelete}>
                Delete
              </button>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
};