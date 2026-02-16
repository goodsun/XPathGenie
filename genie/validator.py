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


def find_multi_matches(mappings: dict, pages: list) -> dict:
    """
    Find fields where XPath matches multiple nodes on any page.
    Returns {field: {xpath, contexts: [{url, count, snippets: [html_context, ...]}]}}
    for fields that need refinement.
    """
    valid_pages = [p for p in pages if p.get("html")]
    if not valid_pages:
        return {}

    docs = []
    for p in valid_pages:
        try:
            doc = fromstring(p["html"])
            docs.append((p["url"], doc))
        except Exception:
            pass

    multi = {}
    for field, xpath in mappings.items():
        field_contexts = []
        for url, doc in docs:
            try:
                nodes = doc.xpath(xpath)
                if len(nodes) > 1:
                    # Skip if all values are identical (harmless duplication)
                    vals = set()
                    for node in nodes:
                        if isinstance(node, str):
                            vals.add(node.strip())
                        elif hasattr(node, "text_content"):
                            vals.add(node.text_content().strip())
                    if len(vals) <= 1:
                        continue  # Same value everywhere, no need to refine
                    snippets = []
                    for node in nodes[:4]:  # max 4 matches
                        # Get the parent chain (up to 2 levels) as context
                        parent = node.getparent()
                        if parent is not None:
                            grandparent = parent.getparent()
                            context_node = grandparent if grandparent is not None else parent
                        else:
                            context_node = node
                        try:
                            html_snippet = etree.tostring(context_node, encoding="unicode", method="html")
                            # Truncate long snippets
                            if len(html_snippet) > 1500:
                                html_snippet = html_snippet[:1500] + "..."
                            snippets.append(html_snippet)
                        except Exception:
                            snippets.append("(could not serialize)")
                    field_contexts.append({
                        "url": url,
                        "count": len(nodes),
                        "snippets": snippets,
                    })
            except Exception:
                pass
        if field_contexts:
            multi[field] = {"xpath": xpath, "contexts": field_contexts}

    return multi


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
                        # Check if all matched values are identical
                        all_vals = set()
                        for node in nodes:
                            if isinstance(node, str):
                                all_vals.add(node.strip())
                            elif hasattr(node, "text_content"):
                                all_vals.add(node.text_content().strip())
                        if len(all_vals) > 1:
                            multi_hits.append(url)  # Different values = real problem
                        # Same values = harmless, skip warning
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
