import React, { useState, useEffect } from 'react';
import { Schedule, DurationSchedule, DailySchedule } from '../types';
import { DAY_NAMES } from '../constants';
import { styles } from './styles';

interface ScheduleFormProps {
  schedule: Schedule | null;
  onScheduleChange: (schedule: Schedule | null) => void;
}

const DAYS_OF_WEEK = DAY_NAMES.map((label, value) => ({ value, label }));

export const ScheduleForm: React.FC<ScheduleFormProps> = ({ 
  schedule: _schedule, 
  onScheduleChange 
}) => {
  const [scheduleType, setScheduleType] = useState<'duration' | 'daily'>('duration');
  const [durationHours, setDurationHours] = useState(1);
  const [durationMinutes, setDurationMinutes] = useState(0);
  const [selectedDays, setSelectedDays] = useState<number[]>([]);
  const [startTime, setStartTime] = useState('09:00');
  const [endTime, setEndTime] = useState('17:00');

  const handleScheduleTypeChange = (type: 'duration' | 'daily') => {
    setScheduleType(type);
    onScheduleChange(null);
  };

  const createDurationSchedule = (): DurationSchedule | null => {
    const totalMinutes = durationHours * 60 + durationMinutes;
    if (totalMinutes > 0) {
      return {
        type: 'duration',
        durationMinutes: totalMinutes,
        startTime: Date.now(),
      };
    }
    return null;
  };

  const createDailySchedule = (): DailySchedule | null => {
    if (selectedDays.length > 0 && startTime && endTime) {
      return {
        type: 'daily',
        daysOfWeek: selectedDays,
        startTime,
        endTime,
      };
    }
    return null;
  };

  const toggleDay = (day: number) => {
    const newDays = selectedDays.includes(day)
      ? selectedDays.filter((d) => d !== day)
      : [...selectedDays, day].sort();
    setSelectedDays(newDays);
  };

  useEffect(() => {
    if (scheduleType === 'duration') {
      const schedule = createDurationSchedule();
      onScheduleChange(schedule);
    } else {
      const schedule = createDailySchedule();
      onScheduleChange(schedule);
    }
  }, [durationHours, durationMinutes, selectedDays, startTime, endTime, scheduleType]);

  const inputStyle = {
    width: '60px',
    padding: '4px',
    border: '1px solid #ccc',
    borderRadius: '4px',
  } as const;

  const timeInputStyle = {
    marginLeft: '4px',
    padding: '4px',
    border: '1px solid #ccc',
    borderRadius: '4px',
  } as const;

  return (
    <div style={{ marginBottom: '16px' }}>
      <label style={styles.label}>Schedule:</label>

      <div style={{ marginBottom: '12px' }}>
        <label style={{ marginRight: '16px', cursor: 'pointer' }}>
          <input
            type="radio"
            checked={scheduleType === 'duration'}
            onChange={() => handleScheduleTypeChange('duration')}
            style={{ marginRight: '4px' }}
          />
          Duration
        </label>
        <label style={{ cursor: 'pointer' }}>
          <input
            type="radio"
            checked={scheduleType === 'daily'}
            onChange={() => handleScheduleTypeChange('daily')}
            style={{ marginRight: '4px' }}
          />
          Daily Schedule
        </label>
      </div>

      {scheduleType === 'duration' ? (
        <div style={styles.flexRow}>
          <input
            type="number"
            min="0"
            max="23"
            value={durationHours}
            onChange={(e) => setDurationHours(parseInt(e.target.value) || 0)}
            style={inputStyle}
          />
          <span>hours</span>
          <input
            type="number"
            min="0"
            max="59"
            value={durationMinutes}
            onChange={(e) => setDurationMinutes(parseInt(e.target.value) || 0)}
            style={inputStyle}
          />
          <span>minutes</span>
        </div>
      ) : (
        <div>
          <div style={{ marginBottom: '8px' }}>
            <label style={{ display: 'block', marginBottom: '4px', fontSize: '12px' }}>
              Days of week:
            </label>
            <div style={{ display: 'flex', gap: '4px' }}>
              {DAYS_OF_WEEK.map((day) => (
                <button
                  key={day.value}
                  onClick={() => toggleDay(day.value)}
                  style={{
                    padding: '6px 10px',
                    border: '1px solid #ccc',
                    borderRadius: '4px',
                    backgroundColor: selectedDays.includes(day.value) ? '#4CAF50' : 'white',
                    color: selectedDays.includes(day.value) ? 'white' : 'black',
                    cursor: 'pointer',
                    fontSize: '12px',
                  }}
                >
                  {day.label}
                </button>
              ))}
            </div>
          </div>
          <div style={styles.flexRow}>
            <label style={{ fontSize: '12px' }}>
              Start:
              <input
                type="time"
                value={startTime}
                onChange={(e) => setStartTime(e.target.value)}
                style={timeInputStyle}
              />
            </label>
            <label style={{ fontSize: '12px' }}>
              End:
              <input
                type="time"
                value={endTime}
                onChange={(e) => setEndTime(e.target.value)}
                style={timeInputStyle}
              />
            </label>
          </div>
        </div>
      )}
    </div>
  );
};



