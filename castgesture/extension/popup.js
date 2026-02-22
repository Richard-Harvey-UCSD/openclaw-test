/**
 * CastGesture — Popup script for extension settings.
 */

const GESTURES = {
  open_hand: { icon: '🖐️', label: 'Open Hand' },
  fist: { icon: '✊', label: 'Fist' },
  peace: { icon: '✌️', label: 'Peace' },
  thumbs_up: { icon: '👍', label: 'Thumbs Up' },
  pointing: { icon: '👆', label: 'Pointing' },
  rock_on: { icon: '🤟', label: 'Rock On' },
  ok_sign: { icon: '👌', label: 'OK Sign' },
};

const EFFECTS = ['confetti', 'emoji_rain', 'fire', 'screen_shake', 'flash', 'text_pop', 'spotlight', 'none'];

let currentSettings = null;

// Load settings
chrome.runtime.sendMessage({ type: 'getSettings' }, (settings) => {
  currentSettings = settings;
  document.getElementById('enabled').checked = settings.enabled;
  renderMappings(settings.gestureMappings);
});

// Toggle
document.getElementById('enabled').addEventListener('change', (e) => {
  currentSettings.enabled = e.target.checked;
  saveSettings();
});

// Test button
document.getElementById('test-btn').addEventListener('click', async () => {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (tab) {
    chrome.tabs.sendMessage(tab.id, {
      type: 'settingsUpdated',
      settings: currentSettings,
    }).catch(() => {});
    // Also inject a test effect via page script
    chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: () => {
        if (window.CastGestureEffects) {
          window.CastGestureEffects.trigger('confetti', { intensity: 1.5 });
        }
      },
    }).catch(() => {});
  }
});

function renderMappings(mappings) {
  const container = document.getElementById('mappings');
  container.innerHTML = '';
  for (const [gesture, info] of Object.entries(GESTURES)) {
    const current = mappings[gesture] || 'none';
    const row = document.createElement('div');
    row.className = 'mapping';
    row.innerHTML = `
      <span class="icon">${info.icon}</span>
      <span class="name">${info.label}</span>
      <select data-gesture="${gesture}">
        ${EFFECTS.map(e => `<option value="${e}" ${e === current ? 'selected' : ''}>${e.replace(/_/g, ' ')}</option>`).join('')}
      </select>
    `;
    row.querySelector('select').addEventListener('change', (e) => {
      currentSettings.gestureMappings[gesture] = e.target.value === 'none' ? null : e.target.value;
      saveSettings();
    });
    container.appendChild(row);
  }
}

function saveSettings() {
  chrome.runtime.sendMessage({ type: 'updateSettings', settings: currentSettings });
}

// Listen for gesture events from content script
chrome.runtime.onMessage.addListener((msg) => {
  if (msg.type === 'gestureDetected') {
    const display = document.getElementById('gesture-display');
    const info = GESTURES[msg.gesture] || { icon: '🤚', label: msg.gesture };
    display.innerHTML = `
      <span>${info.icon}</span>
      <span class="gesture-label">${info.label} → ${msg.effect}</span>
    `;
  }
});
