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
        for url, doc in docs:
            try:
                nodes = doc.xpath(xpath)
                if nodes:
                    hits += 1
                    # Extract text value
                    node = nodes[0]
                    if isinstance(node, str):
                        val = node.strip()
                    elif hasattr(node, "text_content"):
                        val = node.text_content().strip()
                    else:
                        val = str(node).strip()
                    if val:
                        samples.append(val[:100])
                    else:
                        samples.append("(empty)")
                else:
                    samples.append(None)
            except Exception as e:
                samples.append(f"(error: {e})")

        confidence = hits / total if total > 0 else 0
        results[field] = {
            "xpath": xpath,
            "confidence": round(confidence, 2),
            "samples": samples,
            "optional": confidence < 1.0,
        }

    return results
