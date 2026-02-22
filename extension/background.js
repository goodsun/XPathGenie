const GENIE_API = 'http://localhost:8789';

// Toggle panel on icon click
chrome.action.onClicked.addListener(async (tab) => {
  try {
    await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      files: ['content.js']
    });
  } catch (e) {
    console.error('XPathAbu inject failed:', e);
  }
});

// Handle analyze requests from content script
chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg.type === 'analyze') {
    analyzeXPath(msg).then(sendResponse).catch(e => sendResponse({ error: e.message }));
    return true;
  }
});

async function analyzeXPath({ xpath, url, html }) {
  const resp = await fetch(`${GENIE_API}/api/analyze`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ xpath, url, html })
  });
  return await resp.json();
}
