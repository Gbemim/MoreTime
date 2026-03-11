/**
 * Script for the blocked page
 * Displays blocking information and updates time remaining
 */

function getBlockInfoFromURL() {
  const params = new URLSearchParams(window.location.search);
  const ruleName = params.get('rule') || 'Unknown Rule';
  const scheduleType = params.get('scheduleType') || 'Unknown';
  const timeRemaining = params.get('timeRemaining') || 'Unknown';
  const description = params.get('description') || 'This website is blocked according to your settings.';

  return {
    ruleName: decodeURIComponent(ruleName),
    scheduleType: decodeURIComponent(scheduleType),
    timeRemaining: decodeURIComponent(timeRemaining),
    description: decodeURIComponent(description),
  };
}

function formatTimeRemaining(timeRemaining) {
  if (timeRemaining === 'Unknown' || timeRemaining === 'N/A') {
    return 'Active';
  }
  return timeRemaining;
}

function updatePage() {
  const info = getBlockInfoFromURL();

  const ruleNameEl = document.getElementById('rule-name');
  const scheduleTypeEl = document.getElementById('schedule-type');
  const timeRemainingEl = document.getElementById('time-remaining');
  const descriptionEl = document.getElementById('description');

  if (ruleNameEl) ruleNameEl.textContent = info.ruleName;
  if (scheduleTypeEl) scheduleTypeEl.textContent = info.scheduleType;
  if (timeRemainingEl) timeRemainingEl.textContent = formatTimeRemaining(info.timeRemaining);
  if (descriptionEl) descriptionEl.textContent = info.description;

  if (info.scheduleType === 'Daily Schedule' && info.timeRemaining === 'Active') {
    const timeInfo = document.getElementById('time-info');
    if (timeInfo) {
      timeInfo.style.display = 'none';
    }
  }
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', updatePage);
} else {
  updatePage();
}

setInterval(function () {
  const info = getBlockInfoFromURL();
  if (info.scheduleType === 'Duration Block') {
    updatePage();
  }
}, 1000);
