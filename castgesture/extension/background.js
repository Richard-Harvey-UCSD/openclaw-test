/**
 * CastGesture — Background service worker.
 * Manages extension lifecycle, state sync between popup and content scripts.
 */

// Default settings
const DEFAULT_SETTINGS = {
  enabled: true,
  gestureMappings: {
    open_hand: 'confetti',
    fist: 'screen_shake',
    peace: 'emoji_rain',
    thumbs_up: 'text_pop',
    pointing: 'spotlight',
  },
  confidenceThreshold: 0.7,
  cooldownMs: 1000,
};

// Initialize settings on install
chrome.runtime.onInstalled.addListener(() => {
  chrome.storage.local.get('settings', (result) => {
    if (!result.settings) {
      chrome.storage.local.set({ settings: DEFAULT_SETTINGS });
    }
  });
});

// Relay messages between popup and content scripts
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === 'getSettings') {
    chrome.storage.local.get('settings', (result) => {
      sendResponse(result.settings || DEFAULT_SETTINGS);
    });
    return true; // async response
  }

  if (message.type === 'updateSettings') {
    chrome.storage.local.set({ settings: message.settings }, () => {
      // Notify all content scripts
      chrome.tabs.query({}, (tabs) => {
        tabs.forEach(tab => {
          chrome.tabs.sendMessage(tab.id, {
            type: 'settingsUpdated',
            settings: message.settings,
          }).catch(() => {});
        });
      });
      sendResponse({ ok: true });
    });
    return true;
  }

  if (message.type === 'gestureDetected') {
    // Forward to popup for display
    chrome.runtime.sendMessage(message).catch(() => {});
  }
});
