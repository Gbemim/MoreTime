import React from 'react';
import { styles } from './styles';

interface DescriptionInputProps {
  value: string;
  onChange: (value: string) => void;
}

export const DescriptionInput: React.FC<DescriptionInputProps> = ({ value, onChange }) => {
  return (
    <div style={{ marginBottom: '16px' }}>
      <label htmlFor="description" style={styles.label}>
        Describe YouTube videos to block:
      </label>
      <textarea
        id="description"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder="e.g., 'Gaming videos and walkthroughs' or 'Productivity distraction videos like entertainment and vlogs'"
        style={styles.textarea}
      />
    </div>
  );
};



