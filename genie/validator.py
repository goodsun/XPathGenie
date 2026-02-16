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
                    # Check if values are all identical
                    vals = set()
                    for node in nodes:
                        if isinstance(node, str):
                            vals.add(node.strip())
                        elif hasattr(node, "text_content"):
                            vals.add(node.text_content().strip())
                    all_identical = len(vals) <= 1
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
            multi[field] = {"xpath": xpath, "contexts": field_contexts, "all_identical": all_identical}

    return multi


def narrow_by_first_match(mappings: dict, multi_matches: dict, pages: list) -> dict:
    """
    For fields where all matched values are identical, narrow the XPath
    by adding an intermediate class-bearing ancestor to get exactly 1 match.
    Searches all matched elements' ancestors for a class that narrows to 1.
    Returns {field: narrowed_xpath} for fields that were successfully narrowed.
    """
    valid_pages = [p for p in pages if p.get("html")]
    if not valid_pages:
        return {}

    try:
        doc = fromstring(valid_pages[0]["html"])
    except Exception:
        return {}

    narrowed = {}
    for field, info in multi_matches.items():
        if not info.get("all_identical"):
            continue  # Different values — needs AI refine

        xpath = info["xpath"]

        # Split xpath into container // core
        parts = xpath.split("//", 2)  # ['', 'container[...]', 'core...']
        if len(parts) < 3:
            continue
        container_part = parts[1]
        core_part = "//" + parts[2]  # includes /@attr if present

        # Get element xpath (strip trailing /@attr if present) for element lookup
        elem_xpath = xpath.rsplit("/@", 1)[0] if "/@" in xpath else xpath

        try:
            elems = doc.xpath(elem_xpath)
        except Exception:
            continue
        if len(elems) < 2:
            continue

        # Extract container class name to skip it
        import re
        container_cls_m = re.search(r"contains\(@class,'([^']+)'\)", container_part)
        container_cls = container_cls_m.group(1) if container_cls_m else ""

        # Collect all intermediate classes from all matched elements
        found = False
        for elem in elems:
            for anc in elem.iterancestors():
                cls = anc.get("class")
                if not cls:
                    continue
                if container_cls and container_cls in cls:
                    break  # Reached the container level, stop
                for c in cls.split():
                    if len(c) < 3:
                        continue
                    candidate = f"//{container_part}//{anc.tag}[contains(@class,'{c}')]{core_part}"
                    try:
                        test_nodes = doc.xpath(candidate)
                        if len(test_nodes) == 1:
                            narrowed[field] = candidate
                            found = True
                            break
                    except Exception:
                        continue
                if found:
                    break
            if found:
                break

    return narrowed


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
