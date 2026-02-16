"""Validate XPaths against fetched HTML pages."""

import re
from lxml import etree
from lxml.html import fromstring

# Tags/classes that indicate main content vs sidebar
MAIN_SIGNALS = {'main', 'article', 'detail', 'content', 'primary', 'job-detail', 'recruit-detail'}
SIDE_SIGNALS = {'aside', 'sidebar', 'recommend', 'related', 'sub', 'widget', 'footer', 'nav'}


def _content_score(node):
    """Score a node by structural context. Higher = more likely main content."""
    score = 0
    ancestor = node.getparent()
    while ancestor is not None:
        tag = ancestor.tag or ""
        cls = (ancestor.get("class") or "").lower()
        aid = (ancestor.get("id") or "").lower()
        context = f"{tag} {cls} {aid}"
        for sig in MAIN_SIGNALS:
            if sig in context:
                score += 10
        for sig in SIDE_SIGNALS:
            if sig in context:
                score -= 10
        # main/article tags are strong signals
        if tag in ("main", "article"):
            score += 20
        elif tag in ("aside", "nav", "footer"):
            score -= 20
        ancestor = ancestor.getparent()
    return score


def validate(mappings: dict, pages: list) -> dict:
    """
    Validate XPath mappings against HTML pages.
    
    Args:
        mappings: {field_name: xpath_expression}
        pages: [{url, html, error}, ...]
    
    Returns:
        {field_name: {xpath, confidence, samples, optional}}
    """
    valid_pages = [p for p in pages if p.get("html")]
    total = len(valid_pages)
    if total == 0:
        return {}

    # Parse all pages
    docs = []
    for p in valid_pages:
        try:
            doc = fromstring(p["html"])
            docs.append((p["url"], doc))
        except Exception:
            pass

    total = len(docs)
    if total == 0:
        return {}

    results = {}
    for field, xpath in mappings.items():
        hits = 0
        samples = []
        multi_hits = []
        for url, doc in docs:
            try:
                nodes = doc.xpath(xpath)
                if nodes:
                    hits += 1
                    # Pick the best match by structural content score
                    best_val = ""
                    best_score = -999
                    for node in nodes:
                        if isinstance(node, str):
                            val = node.strip()
                            sc = 0  # can't score text nodes
                        elif hasattr(node, "text_content"):
                            val = node.text_content().strip()
                            sc = _content_score(node)
                        else:
                            val = str(node).strip()
                            sc = 0
                        if sc > best_score or (sc == best_score and len(val) > len(best_val)):
                            best_val = val
                            best_score = sc
                    if best_val:
                        samples.append(best_val[:100])
                    else:
                        samples.append("(empty)")
                    if len(nodes) > 1:
                        multi_hits.append(url)
                else:
                    samples.append(None)
            except Exception as e:
                samples.append(f"(error: {e})")

        confidence = hits / total if total > 0 else 0
        result_entry = {
            "xpath": xpath,
            "confidence": round(confidence, 2),
            "samples": samples,
            "optional": confidence < 1.0,
        }
        if multi_hits:
            result_entry["warning"] = f"Multiple matches on {len(multi_hits)}/{total} pages — may include sidebar/recommended items"
        results[field] = result_entry

    return results
