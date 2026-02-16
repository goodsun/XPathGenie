"""Compress HTML to minimal structure for AI analysis."""

from lxml import etree
from lxml.html import fromstring, tostring
import re

REMOVE_TAGS = {"script", "style", "noscript", "iframe", "svg", "link", "meta", "head"}
STRIP_TAGS = {"header", "footer", "nav", "aside"}
TEXT_LIMIT = 30


def compress(html: str) -> str:
    """Compress HTML to structural summary."""
    try:
        doc = fromstring(html)
    except Exception:
        return ""

    # Remove unwanted tags
    for tag in REMOVE_TAGS:
        for el in doc.iter(tag):
            el.getparent().remove(el)

    # Remove header/footer/nav/aside
    for tag in STRIP_TAGS:
        for el in doc.iter(tag):
            el.getparent().remove(el)

    # Try to find main content
    main = doc.find(".//main")
    if main is None:
        main = doc.find(".//article")
    if main is None:
        # Find div with most text
        best = doc
        best_len = 0
        for div in doc.iter("div", "section"):
            text = div.text_content() or ""
            if len(text) > best_len:
                best_len = len(text)
                best = div
        if best_len > 200:
            main = best
        else:
            main = doc

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


def _truncate_text(el):
    """Truncate text nodes to TEXT_LIMIT chars."""
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
    for child in list(el):
        _remove_empty(child)
        if (not child.text or not child.text.strip()) and \
           len(child) == 0 and \
           (not child.tail or not child.tail.strip()) and \
           child.tag not in ("br", "hr", "img", "input"):
            el.remove(child)
