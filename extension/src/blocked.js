/**
 * Script for the blocked page
 * Displays blocking information and updates time remaining
 */

function getBlockInfoFromURL() {
  const params = new URLSearchParams(window.location.search);
  const ruleName = params.get('rule') || 'Unknown Rule';
  const scheduleType = params.get('scheduleType') || 'Unknown';
  const timeRemaining = params.get('timeRemaining') || 'Unknown';
  const blockEndsAtRaw = params.get('blockEndsAt');
  const description = params.get('description') || 'This website is blocked according to your settings.';
  const blockEndsAt = blockEndsAtRaw ? Number(blockEndsAtRaw) : null;

  return {
    ruleName: decodeURIComponent(ruleName),
    scheduleType: decodeURIComponent(scheduleType),
    timeRemaining: decodeURIComponent(timeRemaining),
    blockEndsAt: Number.isFinite(blockEndsAt) ? blockEndsAt : null,
    description: decodeURIComponent(description),
  };
}

function formatTimeRemainingFromSeconds(totalSeconds) {
  if (totalSeconds <= 0) return '0m';
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;

  if (hours > 0) return `${hours}h ${minutes}m`;
  if (minutes > 0) return `${minutes}m ${seconds}s`;
  return `${seconds}s`;
}

function formatTimeRemaining(timeRemaining, blockEndsAt) {
  if (typeof blockEndsAt === 'number') {
    const remainingSeconds = Math.max(0, Math.floor((blockEndsAt - Date.now()) / 1000));
    return formatTimeRemainingFromSeconds(remainingSeconds);
  }
  if (timeRemaining === 'Unknown' || timeRemaining === 'N/A') {
    return 'Active';
  }
  return timeRemaining;
}

function updatePage() {
  const info = getBlockInfoFromURL();

  const ruleNameEl = document.getElementById('rule-name');
  const blockedBecauseEl = document.getElementById('blocked-because');
  const timeRemainingEl = document.getElementById('time-remaining');

  if (ruleNameEl) ruleNameEl.textContent = info.ruleName;
  if (blockedBecauseEl) blockedBecauseEl.textContent = info.description;
  if (timeRemainingEl) {
    timeRemainingEl.textContent = formatTimeRemaining(info.timeRemaining, info.blockEndsAt);
  }
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', updatePage);
} else {
  updatePage();
}

setInterval(function () {
  updatePage();
}, 1000);
