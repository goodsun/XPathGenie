(() => {
  if (window.__xpathAbuActive) return;
  window.__xpathAbuActive = true;

  let hoveredEl = null;

  function getXPath(el) {
    if (el.id) return `//*[@id="${el.id}"]`;
    if (el === document.body) return '/html/body';
    if (el === document.documentElement) return '/html';

    // Try class-based if unique
    if (el.className && typeof el.className === 'string') {
      const cls = el.className.trim().split(/\s+/).join(' and contains(@class,"');
      const classXPath = `//${el.tagName.toLowerCase()}[contains(@class,"${cls}")]`;
      try {
        const result = document.evaluate(classXPath, document, null, XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null);
        if (result.snapshotLength === 1) return classXPath;
      } catch (e) {}
    }

    // Full path
    const parts = [];
    let current = el;
    while (current && current !== document) {
      let tag = current.tagName.toLowerCase();
      const parent = current.parentElement;
      if (parent) {
        const siblings = Array.from(parent.children).filter(c => c.tagName === current.tagName);
        if (siblings.length > 1) {
          tag += `[${siblings.indexOf(current) + 1}]`;
        }
      }
      parts.unshift(tag);
      current = parent;
    }
    return '/' + parts.join('/');
  }

  function getTextContent(el) {
    const text = el.innerText || el.textContent || '';
    return text.trim().substring(0, 2000);
  }

  function onMouseOver(e) {
    if (hoveredEl) hoveredEl.classList.remove('xpathabu-highlight');
    hoveredEl = e.target;
    hoveredEl.classList.add('xpathabu-highlight');
    e.stopPropagation();
  }

  function onMouseOut(e) {
    if (hoveredEl) hoveredEl.classList.remove('xpathabu-highlight');
    hoveredEl = null;
  }

  function onClick(e) {
    e.preventDefault();
    e.stopPropagation();
    const el = e.target;
    el.classList.remove('xpathabu-highlight');

    const xpath = getXPath(el);
    const text = getTextContent(el);
    const tag = el.tagName.toLowerCase();
    const attrs = {};
    for (const attr of el.attributes) {
      attrs[attr.name] = attr.value;
    }

    chrome.runtime.sendMessage({
      type: 'xpath_result',
      data: { xpath, text, tag, attrs }
    });
  }

  document.addEventListener('mouseover', onMouseOver, true);
  document.addEventListener('mouseout', onMouseOut, true);
  document.addEventListener('click', onClick, true);

  // Listen for toggle off
  chrome.runtime.onMessage.addListener((msg) => {
    if (msg.type === 'toggle_off') {
      cleanup();
    }
  });

  function cleanup() {
    document.removeEventListener('mouseover', onMouseOver, true);
    document.removeEventListener('mouseout', onMouseOut, true);
    document.removeEventListener('click', onClick, true);
    if (hoveredEl) hoveredEl.classList.remove('xpathabu-highlight');
    window.__xpathAbuActive = false;
  }
})();
