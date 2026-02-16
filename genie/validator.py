"""Validate XPaths against fetched HTML pages."""

from lxml import etree
from lxml.html import fromstring


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
                    # Pick the longest match (main content tends to be more detailed)
                    best_val = ""
                    for node in nodes:
                        if isinstance(node, str):
                            val = node.strip()
                        elif hasattr(node, "text_content"):
                            val = node.text_content().strip()
                        else:
                            val = str(node).strip()
                        if len(val) > len(best_val):
                            best_val = val
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
