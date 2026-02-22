const GENIE_API = 'http://localhost:8789';

// Track which tabs have content script injected
const injectedTabs = new Set();

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg.type === 'inject') {
    injectContentScript(msg.tabId).then(sendResponse);
    return true;
  }
  if (msg.type === 'analyze') {
    analyzeXPath(msg).then(sendResponse).catch(e => sendResponse({ error: e.message }));
    return true;
  }
  if (msg.type === 'xpath_result') {
    // Forward from content script to popup
    // Store latest result
    chrome.storage.session.set({ lastXPathResult: msg.data });
  }
  if (msg.type === 'get_status') {
    sendResponse({ injected: injectedTabs.has(msg.tabId) });
    return false;
  }
});

// Clean up on tab close
chrome.tabs.onRemoved.addListener((tabId) => injectedTabs.delete(tabId));

async function injectContentScript(tabId) {
  if (injectedTabs.has(tabId)) {
    // Toggle off
    await chrome.tabs.sendMessage(tabId, { type: 'toggle_off' });
    injectedTabs.delete(tabId);
    return { active: false };
  }
  try {
    await chrome.scripting.executeScript({ target: { tabId }, files: ['content.js'] });
    await chrome.scripting.insertCSS({ target: { tabId }, files: ['content.css'] });
    injectedTabs.add(tabId);
    return { active: true };
  } catch (e) {
    return { active: false, error: e.message };
  }
}

async function analyzeXPath({ xpath, url, html }) {
  const resp = await fetch(`${GENIE_API}/api/analyze`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ xpath, url, html })
  });
  return await resp.json();
}
