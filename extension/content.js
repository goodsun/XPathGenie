(() => {
  if (window.__xpathAbuActive) {
    if (window.__xpathAbuCleanup) window.__xpathAbuCleanup();
    return;
  }
  window.__xpathAbuActive = true;

  let inspecting = true;
  let hoveredEl = null;
  let lastResult = null;
  let selectedEl = null;
  let extraHighlights = [];

  // --- XPath Generator ---
  function getXPath(el) {
    if (el.id) return `//*[@id="${el.id}"]`;
    if (el === document.body) return '/html/body';
    if (el === document.documentElement) return '/html';

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
  host.style.cssText = 'all:initial; position:fixed; z-index:2147483647; bottom:16px; right:16px; width:350px; height:500px;';
  const shadow = host.attachShadow({ mode: 'closed' });

  shadow.innerHTML = `
    <style>
      :host { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }
      * { box-sizing: border-box; margin: 0; padding: 0; }
      #panel {
        width: 100%; height: 100%;
        background: #1a1a2e;
        border: 1px solid #7c5cfc55;
        border-radius: 10px;
        color: #e0e0e0;
        font-size: 13px;
        box-shadow: 0 8px 32px rgba(0,0,0,0.5);
        overflow: hidden;
        user-select: none;
        display: flex;
        flex-direction: column;
        position: relative;
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
      #body { padding: 10px 12px; display: flex; flex-direction: column; gap: 8px; flex: 1; overflow: hidden; }
      label { font-size: 11px; color: #888; text-transform: uppercase; letter-spacing: 0.5px; }
      #xpath-display {
        background: #0d0d1a; border: 1px solid #333; border-radius: 6px;
        padding: 8px; font-family: 'SF Mono', Monaco, monospace; font-size: 12px;
        color: #a8ff60; width: 100%; outline: none;
      }
      #xpath-display:focus { border-color: #7c5cfc; }
      #tag-info { color: #7c5cfc; font-size: 12px; font-weight: 600; display: flex; flex-wrap: wrap; gap: 2px; align-items: center; padding: 2px 0; }
      #tag-info .crumb { cursor: pointer; padding: 1px 4px; border-radius: 3px; transition: background 0.1s; }
      #tag-info .crumb:hover { background: #7c5cfc33; }
      #tag-info .crumb.active { background: #7c5cfc; color: #fff; }
      #tag-info .sep { color: #555; font-size: 10px; }
      #tag-info .idx { background: #4a2a2a; border: 1px solid #fc5c5c44; color: #fc5c5c; font-size: 10px; padding: 0 5px; border-radius: 8px; margin-left: 2px; display: inline-block; line-height: 16px; font-weight: 700; cursor: pointer; }
      #tag-info .idx:hover { background: #fc5c5c; color: #fff; }
      #text-preview {
        background: #0d0d1a no-repeat calc(100% + 40px) bottom/300px; border: 1px solid #333; border-radius: 6px;
        padding: 8px; font-size: 12px; color: #ccc;
        width: 100%; outline: none; resize: none; flex: 1; min-height: 60px;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
      }
      #text-preview:focus { border-color: #7c5cfc; }

      #footer { display: flex; gap: 6px; padding: 0 12px 10px; }
      #footer .btn { flex: 1; text-align: center; padding: 6px; }
      #status { text-align: center; font-size: 11px; color: #666; padding: 0 12px 8px; }
      #resize-grip {
        position: absolute; bottom: 2px; right: 2px; width: 14px; height: 14px;
        cursor: nwse-resize; opacity: 0.4; font-size: 10px; color: #7c5cfc;
        text-align: right; line-height: 14px;
      }
    </style>
    <div id="panel">
      <div id="header">
        <span id="title"><img id="title-icon" style="width:20px;height:20px;vertical-align:middle;margin-right:4px;"> XPathAbu</span>
        <div class="header-btns">
          <button class="btn active" id="btn-toggle">ON</button>
          <button class="btn close" id="btn-close">✕</button>
        </div>
      </div>
      <div id="body">
        <div>
          <label>XPath</label>
          <input type="text" id="xpath-display" value="クリックで要素を選択..." spellcheck="false">
        </div>
        <div id="tag-info"></div>
        <div style="display:flex;flex-direction:column;flex:1;min-height:0;">
          <textarea id="text-preview" rows="4" spellcheck="false" readonly style="flex:1;">—</textarea>
        </div>
      </div>
      <div id="footer">
        <button class="btn" id="btn-copy">📋 Copy XPath</button>
        <button class="btn" id="btn-analyze">🔍 Analyze</button>
      </div>
      <div id="status">inspect mode: ON</div>
      <div id="resize-grip">⋮⋱</div>
    </div>
  `;

  document.body.appendChild(host);

  const highlightOverlay = document.createElement('div');
  highlightOverlay.style.cssText = 'position:fixed;pointer-events:none;z-index:2147483646;border:2px solid #7c5cfc;background:rgba(124,92,252,0.1);border-radius:2px;display:none;transition:all 0.05s;';
  document.body.appendChild(highlightOverlay);

  const panel = shadow.getElementById('panel');
  // Set Abu watermark on textarea
  const abuUrl = chrome.runtime.getURL('abu.png');
  shadow.getElementById('text-preview').style.backgroundImage = `url(${abuUrl})`;
  shadow.getElementById('title-icon').src = chrome.runtime.getURL('icon32.png');
  const xpathDisplay = shadow.getElementById('xpath-display');
  const tagInfo = shadow.getElementById('tag-info');
  const textPreview = shadow.getElementById('text-preview');
  const btnToggle = shadow.getElementById('btn-toggle');
  const btnClose = shadow.getElementById('btn-close');
  const btnCopy = shadow.getElementById('btn-copy');
  const btnAnalyze = shadow.getElementById('btn-analyze');
  const statusEl = shadow.getElementById('status');
  const resizeGrip = shadow.getElementById('resize-grip');

  // Block page inspect handlers on panel
  ['click', 'mouseover', 'mouseout'].forEach(evt => {
    host.addEventListener(evt, e => e.stopPropagation(), true);
  });

  // --- Drag ---
  const header = shadow.getElementById('header');
  let dragging = false, dx = 0, dy = 0;

  header.addEventListener('mousedown', e => {
    if (e.target.closest('button')) return;
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
  });

  document.addEventListener('mouseup', () => { dragging = false; });

  // --- Resize ---
  let resizing = false, rw = 0, rh = 0, rx = 0, ry = 0;

  resizeGrip.addEventListener('pointerdown', e => {
    resizing = true;
    rw = host.offsetWidth;
    rh = host.offsetHeight;
    rx = e.clientX;
    ry = e.clientY;
    resizeGrip.setPointerCapture(e.pointerId);
    e.preventDefault();
    e.stopPropagation();
  });

  resizeGrip.addEventListener('pointermove', e => {
    if (!resizing) return;
    host.style.width = Math.max(280, rw + (e.clientX - rx)) + 'px';
    host.style.height = Math.max(200, rh + (e.clientY - ry)) + 'px';
    e.stopPropagation();
  });

  resizeGrip.addEventListener('pointerup', e => {
    resizing = false;
    resizeGrip.releasePointerCapture(e.pointerId);
    e.stopPropagation();
  });

  // --- Inspect handlers ---
  function onMouseOver(e) {
    if (!inspecting || dragging || resizing || e.target === host || host.contains(e.target)) return;
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
    if (!inspecting || dragging || resizing) return;
    if (e.target === host || host.contains(e.target)) return;
    e.preventDefault();
    e.stopPropagation();

    const el = e.target;
    highlightOverlay.style.display = 'none';

    let xpath = getXPath(el);
    const tag = el.tagName.toLowerCase();
    let text;
    if (tag === 'a' && el.href) {
      xpath += '/@href';
      text = el.href;
    } else {
      text = (el.innerText || el.textContent || '').trim().substring(0, 2000);
    }

    lastResult = { xpath, text, tag };
    selectedEl = el;
    xpathDisplay.value = xpath;
    buildBreadcrumbsFromXPath(xpath);
    evaluateXPath(xpath);
  }

  document.addEventListener('mouseover', onMouseOver, true);
  document.addEventListener('mouseout', onMouseOut, true);
  document.addEventListener('click', onClick, true);

  // --- Evaluate XPath ---
  function evaluateXPath(xpath) {
    extraHighlights.forEach(h => h.remove());
    extraHighlights = [];
    try {
      const result = document.evaluate(xpath, document, null, XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null);
      const count = result.snapshotLength;
      if (count === 0) {
        textPreview.value = '(no match)';
        tagInfo.innerHTML = '';
        highlightOverlay.style.display = 'none';
        return;
      }
      const lines = [];
      for (let i = 0; i < count; i++) {
        const node = result.snapshotItem(i);
        const text = (node.nodeType === Node.ATTRIBUTE_NODE ? node.value : (node.innerText || node.textContent || '')).trim();
        lines.push(`[${i + 1}] ${text.substring(0, 500)}`);
        const el = node.nodeType === Node.ATTRIBUTE_NODE ? node.ownerElement : node;
        if (el && el.getBoundingClientRect) {
          const rect = el.getBoundingClientRect();
          if (i === 0) {
            highlightOverlay.style.display = 'block';
            highlightOverlay.style.left = rect.left + 'px';
            highlightOverlay.style.top = rect.top + 'px';
            highlightOverlay.style.width = rect.width + 'px';
            highlightOverlay.style.height = rect.height + 'px';
          } else {
            const h = document.createElement('div');
            h.style.cssText = `position:fixed;pointer-events:none;z-index:2147483646;border:2px solid #fc5c5c;background:rgba(252,92,92,0.1);border-radius:2px;left:${rect.left}px;top:${rect.top}px;width:${rect.width}px;height:${rect.height}px;`;
            document.body.appendChild(h);
            extraHighlights.push(h);
          }
        }
      }
      buildBreadcrumbsFromXPath(xpath);
      textPreview.value = `(${count} match${count > 1 ? 'es' : ''})\n` + lines.join('\n');
    } catch (e) {
      textPreview.value = 'Error: ' + e.message;
      tagInfo.innerHTML = '';
      highlightOverlay.style.display = 'none';
    }
  }

  // --- Breadcrumb ---
  function parseXPathSegments(xpath) {
    let path = xpath.replace(/^\/\//, '').replace(/^\//, '');
    const segments = [];
    let current = '';
    let bracketDepth = 0;
    for (const ch of path) {
      if (ch === '[') bracketDepth++;
      if (ch === ']') bracketDepth--;
      if (ch === '/' && bracketDepth === 0) {
        if (current) segments.push(current);
        current = '';
      } else {
        current += ch;
      }
    }
    if (current) segments.push(current);
    return segments;
  }

  function buildBreadcrumbsFromXPath(xpath) {
    tagInfo.innerHTML = '';
    if (!xpath) return;
    const segments = parseXPathSegments(xpath);
    const isRelative = xpath.startsWith('//');

    segments.forEach((seg, i) => {
      if (i > 0) {
        const sep = document.createElement('span');
        sep.className = 'sep';
        sep.textContent = '\u203a';
        tagInfo.appendChild(sep);
      }
      const crumb = document.createElement('span');
      const isLast = (i === segments.length - 1);
      crumb.className = 'crumb' + (isLast ? ' active' : '');
      const m = seg.match(/^(\*|[\w-]+)(?:\[(\d+)\])?/);
      if (m) {
        crumb.textContent = m[1];
        if (m[2]) {
          const idxSpan = document.createElement('span');
          idxSpan.className = 'idx';
          idxSpan.textContent = m[2];
          idxSpan.addEventListener('mousedown', (e) => {
            e.preventDefault();
            e.stopPropagation();
            e.stopImmediatePropagation();
            const newSegments = [...segments];
            newSegments[i] = seg.replace(/\[\d+\]/, '');
            const prefix = xpath.startsWith('//') ? '//' : '/';
            const newXPath = prefix + newSegments.join('/');
            xpathDisplay.value = newXPath;
            evaluateXPath(newXPath);
            setTimeout(() => buildBreadcrumbsFromXPath(newXPath), 0);
          });
          crumb.appendChild(idxSpan);
        }
      } else {
        crumb.textContent = seg;
      }

      if (!seg.startsWith('@')) {
        crumb.addEventListener('mousedown', (e) => {
          e.preventDefault();
          e.stopPropagation();
          e.stopImmediatePropagation();
          let newXPath;
          if (e.shiftKey) {
            newXPath = '//' + segments.slice(i).join('/');
          } else {
            const prefix = isRelative ? '//' : '/';
            newXPath = prefix + segments.slice(0, i + 1).join('/');
          }
          xpathDisplay.value = newXPath;
          evaluateXPath(newXPath);
          setTimeout(() => buildBreadcrumbsFromXPath(newXPath), 0);
        });
      }
      tagInfo.appendChild(crumb);
    });
  }

  // --- XPath input handlers ---
  let evalTimer = null;
  xpathDisplay.addEventListener('input', () => {
    clearTimeout(evalTimer);
    evalTimer = setTimeout(() => {
      evaluateXPath(xpathDisplay.value);
      buildBreadcrumbsFromXPath(xpathDisplay.value);
    }, 300);
  });

  xpathDisplay.addEventListener('keydown', e => {
    if (e.key === 'Enter') {
      e.preventDefault();
      evaluateXPath(xpathDisplay.value);
    }
  });

  // --- Button handlers ---
  btnToggle.addEventListener('mousedown', (e) => { e.preventDefault(); e.stopPropagation();
    inspecting = !inspecting;
    btnToggle.textContent = inspecting ? 'ON' : 'OFF';
    btnToggle.classList.toggle('active', inspecting);
    statusEl.textContent = `inspect mode: ${inspecting ? 'ON' : 'OFF'}`;
    if (!inspecting) {
      highlightOverlay.style.display = 'none';
      hoveredEl = null;
    }
  });

  btnClose.addEventListener('mousedown', (e) => { e.preventDefault(); e.stopPropagation(); cleanup(); });

  btnCopy.addEventListener('mousedown', (e) => { e.preventDefault(); e.stopPropagation();
    const text = xpathDisplay.value;
    const ta = document.createElement('textarea');
    ta.value = text;
    ta.style.cssText = 'position:fixed;left:-9999px;';
    document.body.appendChild(ta);
    ta.select();
    document.execCommand('copy');
    document.body.removeChild(ta);
    statusEl.textContent = '[copied!]';
    statusEl.style.color = '#a8ff60';
    setTimeout(() => { statusEl.textContent = `inspect mode: ${inspecting ? 'ON' : 'OFF'}`; statusEl.style.color = ''; }, 1500);
  });

  btnAnalyze.addEventListener('mousedown', (e) => { e.preventDefault(); e.stopPropagation();
    if (!lastResult) return;
    btnAnalyze.textContent = '⏳...';
    chrome.runtime.sendMessage({
      type: 'analyze',
      xpath: xpathDisplay.value,
      url: location.href,
      html: lastResult.tag
    }, (resp) => {
      btnAnalyze.textContent = '🔍 Analyze';
      if (resp && !resp.error) {
        textPreview.value = JSON.stringify(resp, null, 2).substring(0, 500);
      } else {
        textPreview.value = 'Error: ' + (resp?.error || 'no response');
      }
    });
  });

  // --- Cleanup ---
  function cleanup() {
    document.removeEventListener('mouseover', onMouseOver, true);
    document.removeEventListener('mouseout', onMouseOut, true);
    document.removeEventListener('click', onClick, true);
    highlightOverlay.remove();
    extraHighlights.forEach(h => h.remove());
    extraHighlights = [];
    host.remove();
    window.__xpathAbuActive = false;
    window.__xpathAbuCleanup = null;
  }

  window.__xpathAbuCleanup = cleanup;
})();
