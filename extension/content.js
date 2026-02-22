(() => {
  // Toggle: if already active, remove panel and cleanup
  if (window.__xpathAbuActive) {
    if (window.__xpathAbuCleanup) window.__xpathAbuCleanup();
    return;
  }
  window.__xpathAbuActive = true;

  let inspecting = true;
  let hoveredEl = null;
  let lastResult = null;

  // --- XPath Generator ---
  function getXPath(el) {
    if (el.id) return `//*[@id="${el.id}"]`;
    if (el === document.body) return '/html/body';
    if (el === document.documentElement) return '/html';

    // Try class-based if unique
    if (el.className && typeof el.className === 'string') {
      const classes = el.className.trim().split(/\s+/);
      if (classes.length && classes[0]) {
        const cls = classes.map(c => `contains(@class,"${c}")`).join(' and ');
        const classXPath = `//${el.tagName.toLowerCase()}[${cls}]`;
        try {
          const result = document.evaluate(classXPath, document, null, XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null);
          if (result.snapshotLength === 1) return classXPath;
        } catch (e) {}
      }
    }

    const parts = [];
    let current = el;
    while (current && current !== document) {
      let tag = current.tagName.toLowerCase();
      const parent = current.parentElement;
      if (parent) {
        const siblings = Array.from(parent.children).filter(c => c.tagName === current.tagName);
        if (siblings.length > 1) tag += `[${siblings.indexOf(current) + 1}]`;
      }
      parts.unshift(tag);
      current = parent;
    }
    return '/' + parts.join('/');
  }

  // --- Create Shadow DOM Panel ---
  const host = document.createElement('div');
  host.id = 'xpathabu-host';
  host.style.cssText = 'all:initial; position:fixed; z-index:2147483647; bottom:16px; right:16px;';
  const shadow = host.attachShadow({ mode: 'closed' });

  shadow.innerHTML = `
    <style>
      :host { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }
      * { box-sizing: border-box; margin: 0; padding: 0; }
      #panel {
        width: 380px;
        background: #1a1a2e;
        border: 1px solid #7c5cfc55;
        border-radius: 10px;
        color: #e0e0e0;
        font-size: 13px;
        box-shadow: 0 8px 32px rgba(0,0,0,0.5);
        overflow: hidden;
        user-select: none;
      }
      #header {
        display: flex; align-items: center; justify-content: space-between;
        padding: 8px 12px;
        background: #16162a;
        cursor: grab;
        border-bottom: 1px solid #7c5cfc44;
      }
      #header:active { cursor: grabbing; }
      #title { font-weight: 700; font-size: 14px; color: #7c5cfc; }
      .header-btns { display: flex; gap: 4px; }
      .btn {
        background: #2a2a4a; border: 1px solid #7c5cfc44; color: #ccc;
        border-radius: 5px; padding: 4px 10px; cursor: pointer; font-size: 12px;
        transition: background 0.15s;
      }
      .btn:hover { background: #7c5cfc; color: #fff; }
      .btn.active { background: #7c5cfc; color: #fff; }
      .btn.close { background: #4a2a2a; border-color: #fc5c5c44; }
      .btn.close:hover { background: #fc5c5c; }
      #body { padding: 10px 12px; display: flex; flex-direction: column; gap: 8px; }
      label { font-size: 11px; color: #888; text-transform: uppercase; letter-spacing: 0.5px; }
      #xpath-display {
        background: #0d0d1a; border: 1px solid #333; border-radius: 6px;
        padding: 8px; font-family: 'SF Mono', Monaco, monospace; font-size: 12px;
        color: #a8ff60; word-break: break-all; min-height: 36px;
        max-height: 80px; overflow-y: auto; user-select: text; cursor: text;
      }
      #tag-info { color: #7c5cfc; font-size: 12px; font-weight: 600; }
      #text-preview {
        background: #0d0d1a; border: 1px solid #333; border-radius: 6px;
        padding: 8px; font-size: 12px; color: #ccc;
        max-height: 60px; overflow-y: auto; user-select: text; cursor: text;
      }
      #attrs-display {
        background: #0d0d1a; border: 1px solid #333; border-radius: 6px;
        padding: 8px; font-size: 11px; color: #999;
        max-height: 60px; overflow-y: auto; user-select: text; cursor: text;
      }
      #footer { display: flex; gap: 6px; padding: 0 12px 10px; }
      #footer .btn { flex: 1; text-align: center; padding: 6px; }
      #status { text-align: center; font-size: 11px; color: #666; padding: 0 12px 8px; }
      .highlight-overlay {
        position: fixed; pointer-events: none; z-index: 2147483646;
        border: 2px solid #7c5cfc; background: rgba(124,92,252,0.1);
        border-radius: 2px; transition: all 0.05s;
      }
    </style>
    <div id="panel">
      <div id="header">
        <span id="title">🐒 XPathAbu</span>
        <div class="header-btns">
          <button class="btn active" id="btn-toggle">ON</button>
          <button class="btn close" id="btn-close">✕</button>
        </div>
      </div>
      <div id="body">
        <div>
          <label>XPath</label>
          <div id="xpath-display">クリックで要素を選択...</div>
        </div>
        <div id="tag-info"></div>
        <div>
          <label>Text</label>
          <div id="text-preview">—</div>
        </div>
        <div>
          <label>Attributes</label>
          <div id="attrs-display">—</div>
        </div>
      </div>
      <div id="footer">
        <button class="btn" id="btn-copy">📋 Copy XPath</button>
        <button class="btn" id="btn-analyze">🔍 Analyze</button>
      </div>
      <div id="status">inspect mode: ON</div>
    </div>
  `;

  document.body.appendChild(host);

  // Create highlight overlay (outside shadow DOM so it covers the page)
  const highlightOverlay = document.createElement('div');
  highlightOverlay.style.cssText = 'position:fixed;pointer-events:none;z-index:2147483646;border:2px solid #7c5cfc;background:rgba(124,92,252,0.1);border-radius:2px;display:none;transition:all 0.05s;';
  document.body.appendChild(highlightOverlay);

  // --- DOM refs ---
  const panel = shadow.getElementById('panel');
  const xpathDisplay = shadow.getElementById('xpath-display');
  const tagInfo = shadow.getElementById('tag-info');
  const textPreview = shadow.getElementById('text-preview');
  const attrsDisplay = shadow.getElementById('attrs-display');
  const btnToggle = shadow.getElementById('btn-toggle');
  const btnClose = shadow.getElementById('btn-close');
  const btnCopy = shadow.getElementById('btn-copy');
  const btnAnalyze = shadow.getElementById('btn-analyze');
  const statusEl = shadow.getElementById('status');

  // --- Stop events from reaching page ---
  host.addEventListener('mousedown', e => e.stopPropagation(), true);
  host.addEventListener('mouseup', e => e.stopPropagation(), true);
  host.addEventListener('click', e => e.stopPropagation(), true);
  host.addEventListener('mouseover', e => e.stopPropagation(), true);
  host.addEventListener('mouseout', e => e.stopPropagation(), true);
  host.addEventListener('pointerdown', e => e.stopPropagation(), true);
  host.addEventListener('pointerup', e => e.stopPropagation(), true);

  // --- Drag to move ---
  const header = shadow.getElementById('header');
  let dragging = false, dx = 0, dy = 0;

  header.addEventListener('mousedown', e => {
    dragging = true;
    const rect = host.getBoundingClientRect();
    dx = e.clientX - rect.left;
    dy = e.clientY - rect.top;
    e.preventDefault();
  });

  document.addEventListener('mousemove', e => {
    if (!dragging) return;
    host.style.left = (e.clientX - dx) + 'px';
    host.style.top = (e.clientY - dy) + 'px';
    host.style.right = 'auto';
    host.style.bottom = 'auto';
  }, true);

  document.addEventListener('mouseup', () => { dragging = false; }, true);

  // --- Inspect handlers ---
  function onMouseOver(e) {
    if (!inspecting || e.target === host || host.contains(e.target)) return;
    hoveredEl = e.target;
    const rect = hoveredEl.getBoundingClientRect();
    highlightOverlay.style.display = 'block';
    highlightOverlay.style.left = rect.left + 'px';
    highlightOverlay.style.top = rect.top + 'px';
    highlightOverlay.style.width = rect.width + 'px';
    highlightOverlay.style.height = rect.height + 'px';
  }

  function onMouseOut(e) {
    if (!inspecting) return;
    highlightOverlay.style.display = 'none';
    hoveredEl = null;
  }

  function onClick(e) {
    if (!inspecting) return;
    if (e.target === host || host.contains(e.target)) return;
    e.preventDefault();
    e.stopPropagation();

    const el = e.target;
    highlightOverlay.style.display = 'none';

    const xpath = getXPath(el);
    const text = (el.innerText || el.textContent || '').trim().substring(0, 2000);
    const tag = el.tagName.toLowerCase();
    const attrs = {};
    for (const attr of el.attributes) attrs[attr.name] = attr.value;

    lastResult = { xpath, text, tag, attrs };

    xpathDisplay.textContent = xpath;
    tagInfo.textContent = `<${tag}>${el.id ? ' #' + el.id : ''}${el.className && typeof el.className === 'string' ? ' .' + el.className.trim().split(/\s+/).join('.') : ''}`;
    textPreview.textContent = text.substring(0, 300) || '(empty)';
    attrsDisplay.textContent = Object.entries(attrs).map(([k, v]) => `${k}="${v}"`).join('\n') || '(none)';
  }

  document.addEventListener('mouseover', onMouseOver, true);
  document.addEventListener('mouseout', onMouseOut, true);
  document.addEventListener('click', onClick, true);

  // --- Button handlers ---
  btnToggle.addEventListener('click', () => {
    inspecting = !inspecting;
    btnToggle.textContent = inspecting ? 'ON' : 'OFF';
    btnToggle.classList.toggle('active', inspecting);
    statusEl.textContent = `inspect mode: ${inspecting ? 'ON' : 'OFF'}`;
    if (!inspecting) {
      highlightOverlay.style.display = 'none';
      hoveredEl = null;
    }
  });

  btnClose.addEventListener('click', cleanup);

  btnCopy.addEventListener('click', () => {
    if (!lastResult) return;
    navigator.clipboard.writeText(lastResult.xpath).then(() => {
      btnCopy.textContent = '✅ Copied!';
      setTimeout(() => { btnCopy.textContent = '📋 Copy XPath'; }, 1500);
    });
  });

  btnAnalyze.addEventListener('click', () => {
    if (!lastResult) return;
    btnAnalyze.textContent = '⏳...';
    chrome.runtime.sendMessage({
      type: 'analyze',
      xpath: lastResult.xpath,
      url: location.href,
      html: lastResult.tag
    }, (resp) => {
      btnAnalyze.textContent = '🔍 Analyze';
      if (resp && !resp.error) {
        textPreview.textContent = JSON.stringify(resp, null, 2).substring(0, 500);
      } else {
        textPreview.textContent = 'Error: ' + (resp?.error || 'no response');
      }
    });
  });

  // --- Cleanup ---
  function cleanup() {
    document.removeEventListener('mouseover', onMouseOver, true);
    document.removeEventListener('mouseout', onMouseOut, true);
    document.removeEventListener('click', onClick, true);
    highlightOverlay.remove();
    host.remove();
    window.__xpathAbuActive = false;
    window.__xpathAbuCleanup = null;
  }

  window.__xpathAbuCleanup = cleanup;
})();
