"""Compress HTML to minimal structure for AI analysis."""

from lxml import etree
from lxml.html import fromstring, tostring
import re

REMOVE_TAGS = {"script", "style", "noscript", "iframe", "svg", "link", "meta", "head"}
STRIP_TAGS = {"header", "footer", "nav", "aside"}
# Class patterns that indicate non-main content (sidebar, recommendations, etc.)
NOISE_PATTERNS = re.compile(
    r'recommend|related|sidebar|widget|breadcrumb|modal|slide|footer|banner|ad-|popup|cookie',
    re.IGNORECASE
)
TEXT_LIMIT = 30


def _safe_text_content(el):
    """Safely get text content, handling comments etc."""
    try:
        return el.text_content() or ""
    except Exception:
        return ""


def _find_main_section(doc):
    """Find the primary content section, excluding recommendations/sidebar."""
    # Try <main> first
    main = doc.find(".//main")
    if main is None:
        main = doc.find(".//article")
    
    if main is not None:
        # Within main, find the first large content block that isn't noise
        children = [c for c in main if isinstance(getattr(c, 'tag', ''), str)]
        best = None
        best_len = 0
        for child in children:
            cls = (child.get("class") or "") + " " + (child.get("id") or "")
            if NOISE_PATTERNS.search(cls):
                continue
            text_len = len(_safe_text_content(child))
            if text_len > best_len:
                best_len = text_len
                best = child
        if best is not None and best_len > 200:
            return best
        return main
    
    # No main/article — find div with most text, excluding noise
    best = doc
    best_len = 0
    for div in doc.iter("div", "section"):
        cls = (div.get("class") or "") + " " + (div.get("id") or "")
        if NOISE_PATTERNS.search(cls):
            continue
        text_len = len(_safe_text_content(div))
        if text_len > best_len:
            best_len = text_len
            best = div
    return best if best_len > 200 else doc


def compress(html: str) -> str:
    """Compress HTML to structural summary of main content only."""
    try:
        doc = fromstring(html)
    except Exception:
        return ""

    # Remove unwanted tags
    for tag in REMOVE_TAGS:
        for el in list(doc.iter(tag)):
            parent = el.getparent()
            if parent is not None:
                parent.remove(el)

    # Remove header/footer/nav/aside
    for tag in STRIP_TAGS:
        for el in list(doc.iter(tag)):
            parent = el.getparent()
            if parent is not None:
                parent.remove(el)

    # Find main content section (excludes recommendations etc.)
    main = _find_main_section(doc)

    # Remove noise children within main
    _remove_noise(main)

    # Truncate text nodes
    _truncate_text(main)

    # Remove empty elements
    _remove_empty(main)

    # Serialize
    try:
        result = tostring(main, encoding="unicode", method="html")
    except Exception:
        return ""

    # Clean up whitespace
    result = re.sub(r'\s+', ' ', result)
    result = re.sub(r'>\s+<', '><', result)

    return result


def _remove_noise(el):
    """Remove child elements that match noise patterns."""
    for child in list(el):
        if not isinstance(getattr(child, 'tag', ''), str):
            continue
        cls = (child.get("class") or "") + " " + (child.get("id") or "")
        if NOISE_PATTERNS.search(cls):
            el.remove(child)
        else:
            _remove_noise(child)


def _truncate_text(el):
    """Truncate text nodes to TEXT_LIMIT chars."""
    if not isinstance(getattr(el, 'tag', ''), str):
        return
    if el.text and el.text.strip():
        t = el.text.strip()
        if len(t) > TEXT_LIMIT:
            el.text = t[:TEXT_LIMIT] + "…"
    if el.tail and el.tail.strip():
        t = el.tail.strip()
        if len(t) > TEXT_LIMIT:
            el.tail = t[:TEXT_LIMIT] + "…"
    for child in el:
        _truncate_text(child)


def _remove_empty(el):
    """Remove elements with no text content."""
    if not isinstance(getattr(el, 'tag', ''), str):
        return
    for child in list(el):
        _remove_empty(child)
        if not isinstance(getattr(child, 'tag', ''), str):
            continue
        if (not child.text or not child.text.strip()) and \
           len(child) == 0 and \
           (not child.tail or not child.tail.strip()) and \
           child.tag not in ("br", "hr", "img", "input"):
            el.remove(child)
