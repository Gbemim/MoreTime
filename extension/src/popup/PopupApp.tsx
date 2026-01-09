import React, { useState, useEffect } from 'react';
import { DescriptionInput } from './DescriptionInput';
import { ScheduleForm } from './ScheduleForm';
import { GeneratedRulesView } from './GeneratedRulesView';
import { SavedRulesList } from './SavedRulesList';
import { BlockRule, GenerateRulesResponse, Schedule } from '../types';
import { MESSAGE_TYPES } from '../constants';
import { styles } from './styles';

export const PopupApp: React.FC = () => {
  const [description, setDescription] = useState('');
  const [schedule, setSchedule] = useState<Schedule | null>(null);
  const [generatedRules, setGeneratedRules] = useState<GenerateRulesResponse | null>(null);
  const [savedRules, setSavedRules] = useState<BlockRule[]>([]);
  const [isGenerating, setIsGenerating] = useState(false);

  // Load saved rules on mount
  useEffect(() => {
    chrome.runtime.sendMessage({ type: MESSAGE_TYPES.GET_RULES }, (response) => {
      if (response && response.rules) {
        setSavedRules(response.rules);
      }
    });
  }, []);

  const handleGenerate = async () => {
    if (!description.trim() || !schedule) {
      alert('Please provide a description and select a schedule');
      return;
    }

    setIsGenerating(true);
    try {
      const response = await chrome.runtime.sendMessage({
        type: MESSAGE_TYPES.GENERATE_RULES,
        description,
      });

      if (response && response.success) {
        setGeneratedRules(response.data);
      } else {
        alert(`Failed to generate rules: ${response?.error || 'Unknown error'}`);
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : String(error);
      alert(`Error generating rules: ${errorMessage}`);
    } finally {
      setIsGenerating(false);
    }
  };

  const handleSaveRule = () => {
    if (!generatedRules || !schedule) {
      return;
    }

    const newRule: BlockRule = {
      id: Date.now().toString(),
      userDescription: description,
      aiSummary: generatedRules.summary,
      patterns: [], // Empty - blocking uses metadata analysis only
      schedule,
      enabled: true,
      createdAt: Date.now(),
    };

    chrome.runtime.sendMessage(
      { type: MESSAGE_TYPES.SAVE_RULE, rule: newRule },
      (response) => {
        if (response && response.success) {
          setSavedRules([...savedRules, newRule]);
          setDescription('');
          setSchedule(null);
          setGeneratedRules(null);
        } else {
          alert('Failed to save rule');
        }
      }
    );
  };

  const handleToggleRule = (ruleId: string, enabled: boolean) => {
    chrome.runtime.sendMessage(
      { type: MESSAGE_TYPES.TOGGLE_RULE, ruleId, enabled },
      (response) => {
        if (response && response.success) {
          setSavedRules((prev) =>
            prev.map((rule) => (rule.id === ruleId ? { ...rule, enabled } : rule))
          );
        }
      }
    );
  };

  const handleDeleteRule = (ruleId: string) => {
    chrome.runtime.sendMessage(
      { type: MESSAGE_TYPES.DELETE_RULE, ruleId },
      (response) => {
        if (response && response.success) {
          setSavedRules((prev) => prev.filter((rule) => rule.id !== ruleId));
        }
      }
    );
  };

  return (
    <div style={styles.container}>
      <h1 style={styles.heading}>MoreTime YouTube Blocker</h1>

      <DescriptionInput value={description} onChange={setDescription} />

      <ScheduleForm schedule={schedule} onScheduleChange={setSchedule} />

      <button
        onClick={handleGenerate}
        disabled={isGenerating || !description.trim() || !schedule}
        style={{
          ...styles.button,
          ...(isGenerating || !description.trim() || !schedule ? styles.buttonDisabled : {}),
        }}
      >
        {isGenerating ? 'Generating...' : 'Generate YouTube Block Rules'}
      </button>

      {generatedRules && (
        <GeneratedRulesView
          rules={generatedRules}
          schedule={schedule}
          onSave={handleSaveRule}
        />
      )}

      <SavedRulesList
        rules={savedRules}
        onToggle={handleToggleRule}
        onDelete={handleDeleteRule}
      />
    </div>
  );
};



