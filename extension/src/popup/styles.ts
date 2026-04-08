/**
 * Shared styles for popup components
 */

export const styles = {
  container: {
    padding: '16px',
    fontFamily: 'system-ui, sans-serif',
  } as const,

  heading: {
    marginTop: 0,
    fontSize: '20px',
  } as const,

  heading2: {
    fontSize: '18px',
    marginBottom: '12px',
  } as const,

  heading3: {
    marginTop: 0,
    fontSize: '16px',
  } as const,

  label: {
    display: 'block',
    marginBottom: '8px',
    fontWeight: '500',
    fontSize: '14px',
  } as const,

  textarea: {
    width: '100%',
    minHeight: '80px',
    padding: '8px',
    border: '1px solid #ccc',
    borderRadius: '4px',
    fontSize: '14px',
    fontFamily: 'inherit',
    resize: 'vertical',
    boxSizing: 'border-box',
  } as const,

  button: {
    width: '100%',
    padding: '10px',
    marginTop: '12px',
    backgroundColor: '#4CAF50',
    color: 'white',
    border: 'none',
    borderRadius: '4px',
    cursor: 'pointer',
    fontSize: '14px',
    fontWeight: 'bold',
  } as const,

  buttonDisabled: {
    cursor: 'not-allowed',
    opacity: 0.6,
  } as const,

  buttonSecondary: {
    width: '100%',
    padding: '8px',
    backgroundColor: '#2196F3',
    color: 'white',
    border: 'none',
    borderRadius: '4px',
    cursor: 'pointer',
    fontSize: '14px',
    fontWeight: 'bold',
  } as const,

  buttonDelete: {
    padding: '4px 8px',
    fontSize: '11px',
    backgroundColor: '#f44336',
    color: 'white',
    border: 'none',
    borderRadius: '4px',
    cursor: 'pointer',
  } as const,

  card: {
    marginTop: '16px',
    padding: '12px',
    backgroundColor: '#f5f5f5',
    borderRadius: '4px',
    border: '1px solid #ddd',
  } as const,

  ruleCard: {
    padding: '12px',
    marginBottom: '8px',
    borderRadius: '4px',
  } as const,

  ruleCardActive: {
    backgroundColor: '#fff3cd',
    border: '1px solid #ffc107',
  } as const,

  ruleCardInactive: {
    backgroundColor: '#f5f5f5',
    border: '1px solid #ddd',
  } as const,

  emptyState: {
    marginTop: '24px',
    textAlign: 'center',
    color: '#999',
    fontSize: '14px',
  } as const,

  text: {
    margin: '4px 0',
    fontSize: '14px',
    color: '#666',
  } as const,

  /** Summary / AI text with newlines and “- ” bullets from the backend */
  textMultiline: {
    margin: '4px 0 0',
    fontSize: '14px',
    color: '#666',
    whiteSpace: 'pre-wrap',
    wordBreak: 'break-word',
  } as const,

  textSmall: {
    fontSize: '12px',
    color: '#666',
  } as const,

  textSmallMultiline: {
    fontSize: '12px',
    color: '#666',
    whiteSpace: 'pre-wrap',
    wordBreak: 'break-word',
    marginTop: '4px',
  } as const,

  textTiny: {
    fontSize: '11px',
    color: '#999',
  } as const,

  textMuted: {
    fontSize: '12px',
    color: '#888',
  } as const,

  flexRow: {
    display: 'flex',
    gap: '8px',
    alignItems: 'center',
  } as const,

  flexColumn: {
    display: 'flex',
    flexDirection: 'column',
    gap: '4px',
    marginLeft: '8px',
  } as const,

  flexBetween: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'start',
    marginBottom: '8px',
  } as const,

  checkbox: {
    marginRight: '4px',
  } as const,

  checkboxLabel: {
    cursor: 'pointer',
    fontSize: '12px',
  } as const,
} as const;

