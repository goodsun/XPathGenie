const xpathInput = document.getElementById('xpathInput');
const resultBox = document.getElementById('resultBox');
const copyBtn = document.getElementById('copyBtn');
const analyzeBtn = document.getElementById('analyzeBtn');
const toggleBtn = document.getElementById('toggleBtn');
const status = document.getElementById('status');

let currentTabId = null;

async function init() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  currentTabId = tab.id;

  // Check if already active
  chrome.runtime.sendMessage({ type: 'get_status', tabId: currentTabId }, (resp) => {
    if (resp?.injected) {
      toggleBtn.textContent = 'ON';
      toggleBtn.classList.add('active');
    }
  });

  // Load last result
  chrome.storage.session.get('lastXPathResult', (data) => {
    if (data.lastXPathResult) {
      showResult(data.lastXPathResult);
    }
  });
}

function showResult(data) {
  xpathInput.value = data.xpath || '';
  let text = data.text || '(empty)';
  if (text.length > 500) text = text.substring(0, 500) + '…';
  resultBox.textContent = `<${data.tag}> ${Object.entries(data.attrs || {}).map(([k,v]) => `${k}="${v}"`).join(' ')}\n\n${text}`;
}

// Poll for new results while popup is open
const poller = setInterval(() => {
  chrome.storage.session.get('lastXPathResult', (data) => {
    if (data.lastXPathResult && data.lastXPathResult.xpath !== xpathInput.value) {
      showResult(data.lastXPathResult);
    }
  });
}, 500);

window.addEventListener('unload', () => clearInterval(poller));

// Toggle
toggleBtn.addEventListener('click', () => {
  chrome.runtime.sendMessage({ type: 'inject', tabId: currentTabId }, (resp) => {
    if (resp?.active) {
      toggleBtn.textContent = 'ON';
      toggleBtn.classList.add('active');
      status.textContent = 'Click any element on the page';
    } else {
      toggleBtn.textContent = 'OFF';
      toggleBtn.classList.remove('active');
      status.textContent = 'Inspection disabled';
    }
  });
});

// Copy
copyBtn.addEventListener('click', async () => {
  const text = xpathInput.value;
  if (!text) return;
  await navigator.clipboard.writeText(text);
  copyBtn.textContent = '✅ Copied';
  setTimeout(() => copyBtn.textContent = '📋 Copy', 1500);
});

// Analyze
analyzeBtn.addEventListener('click', async () => {
  const xpath = xpathInput.value;
  if (!xpath) return;
  analyzeBtn.disabled = true;
  status.textContent = 'Analyzing...';

  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    // Get page HTML (trimmed)
    const [{ result: html }] = await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: () => document.documentElement.outerHTML.substring(0, 50000)
    });

    const resp = await chrome.runtime.sendMessage({
      type: 'analyze',
      xpath,
      url: tab.url,
      html
    });

    if (resp.error) {
      status.textContent = `Error: ${resp.error}`;
    } else {
      if (resp.optimized_xpath) {
        xpathInput.value = resp.optimized_xpath;
      }
      resultBox.textContent = JSON.stringify(resp, null, 2);
      status.textContent = 'Analysis complete';
    }
  } catch (e) {
    status.textContent = `Error: ${e.message}`;
  }
  analyzeBtn.disabled = false;
});

init();
