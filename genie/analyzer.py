"""Gemini 2.5 Flash API call for XPath mapping generation."""

import json
import os
import requests

API_KEY_PATHS = [
    os.path.expanduser("~/.config/gemini/api_key"),
    os.path.expanduser("~/.config/google/gemini_api_key"),
]

MODEL = "gemini-2.5-flash"


def _get_api_key() -> str:
    for p in API_KEY_PATHS:
        if os.path.exists(p):
            return open(p).read().strip()
    raise RuntimeError("Gemini API key not found")


PROMPT_DISCOVER = """You are an expert web scraper. Analyze the following compressed HTML samples from the same website.
Identify all meaningful data fields that can be extracted, and provide XPath expressions that work across all pages.

Rules:
- Return ONLY a JSON object: {"field_name": "xpath_expression", ...}
- Keep XPaths SHORT and SIMPLE. Avoid deeply nested conditions. Prefer: //dt[text()='ラベル']/following-sibling::dd[1]
- Field names must be lowercase English, descriptive, generic (e.g. price, title, facility_name, prefecture, address, phone, description, salary, job_type, access, working_hours)
- Limit to the 20 most important fields maximum
- XPaths must use // prefix and select element nodes (not text() nodes)
- For class matching, ALWAYS use contains() because classes often have multiple values (e.g. //div[contains(@class,'price')], NOT //div[@class='price'])
- For dt/dd patterns, use: //dl[dt[text()='ラベル']]/dd or //dt[text()='ラベル']/following-sibling::dd[1]
- Do NOT use XPath functions like substring-after or normalize-space. contains(@class,...) is OK.
- Include all extractable fields you can identify
- Do NOT include navigation, header, footer, sidebar, or boilerplate fields
- Output SIMPLE XPaths with NO container prefix (the system adds scoping automatically)
- Example: //dt[text()='給与']/following-sibling::dd[1] (correct)
- Example: //div[contains(@class,'xxx')]//dt[...] (WRONG — do not add container)
- Return valid JSON only, no markdown, no explanation

HTML samples:
"""

PROMPT_WANTLIST = """You are an expert web scraper. Analyze the following compressed HTML samples from the same website.
The user wants to extract SPECIFIC fields. Find the best XPath for each requested field.

Requested fields (JSON schema):
{wantlist}

Rules:
- Return ONLY a JSON object with the EXACT same keys as the requested schema: {{"field_name": "xpath_expression", ...}}
- You MUST include ALL requested field names in the output, even if you cannot find a match (use null for XPath in that case)
- Keep XPaths SHORT and SIMPLE. Prefer: //dt[text()='ラベル']/following-sibling::dd[1]
- XPaths must use // prefix and select element nodes (not text() nodes)
- For class matching, ALWAYS use contains() because classes often have multiple values
- For dt/dd patterns, use: //dl[dt[text()='ラベル']]/dd or //dt[text()='ラベル']/following-sibling::dd[1]
- Do NOT use XPath functions like substring-after or normalize-space. contains(@class,...) is OK.
- Match fields by MEANING, not by label text (e.g. "price" matches "給与", "時給", "報酬", "salary")
- The VALUES in the schema are hints/descriptions of what the user wants for that field. Use them to understand the intent (e.g. "contract": "雇用形態（正社員、契約社員、パート等）" means find the employment type field)
- Output SIMPLE XPaths with NO container prefix (the system adds scoping automatically)
- Example: //dt[text()='給与']/following-sibling::dd[1] (correct)
- Example: //div[contains(@class,'xxx')]//dt[...] (WRONG — do not add container)
- Return valid JSON only, no markdown, no explanation

HTML samples:
"""


def _parse_response(data: dict) -> dict:
    """Parse Gemini response, extract mappings and token count."""
    try:
        text = data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError):
        raise RuntimeError(f"Unexpected Gemini response: {json.dumps(data)[:500]}")

    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

    try:
        mappings = json.loads(text)
    except json.JSONDecodeError:
        start = text.find('{')
        end = text.rfind('}')
        if start >= 0 and end > start:
            try:
                mappings = json.loads(text[start:end+1])
            except json.JSONDecodeError:
                truncated = text[start:]
                last_comma = truncated.rfind('",')
                if last_comma > 0:
                    truncated = truncated[:last_comma+1] + "}"
                    try:
                        mappings = json.loads(truncated)
                    except json.JSONDecodeError:
                        raise RuntimeError(f"Failed to parse Gemini response as JSON: {text[:500]}")
                else:
                    raise RuntimeError(f"Failed to parse Gemini response as JSON: {text[:500]}")
        else:
            raise RuntimeError(f"Failed to parse Gemini response as JSON: {text[:500]}")

    # Remove null mappings
    mappings = {k: v for k, v in mappings.items() if v is not None}

    tokens_used = data.get("usageMetadata", {}).get("totalTokenCount", 0)
    return {"mappings": mappings, "tokens_used": tokens_used}


PROMPT_REFINE = """You are an expert web scraper. Some XPath expressions matched MULTIPLE nodes on the same page.
For each field, examine the surrounding HTML context of the multiple matches, determine which match is the PRIMARY/most important one (the main job detail, not sidebar/recommendations/summary), and return a MORE SPECIFIC XPath that matches only that one.

Strategy:
- Look for intermediate structural containers (divs with meaningful class names) between the page-level container and the target dt/dd
- Use these intermediate containers to narrow down to the correct section
- For example: if both "job detail" and "job summary" sections have dt[text()='勤務地'], add the job-detail section's parent class
- Pick the match that contains the MOST DETAILED information (full description > summary)
- Keep XPaths as simple as possible while being unique

Fields that need refinement:
{fields_json}

Rules:
- Return ONLY a JSON object: {{"field_name": "refined_xpath", ...}}
- Include ONLY the fields listed above (the ones that need fixing)
- XPaths must start with // and use contains(@class,...) for class matching
- Do NOT use functions like substring-after or normalize-space
- Return valid JSON only, no markdown, no explanation
"""


def refine(multi_matches: dict) -> dict:
    """
    Call Gemini to refine XPaths that have multiple matches.
    
    Args:
        multi_matches: {field: {xpath, contexts: [{url, count, snippets}]}}
    
    Returns:
        {field: refined_xpath} for successfully refined fields
    """
    if not multi_matches:
        return {}

    api_key = _get_api_key()

    # Build context for the AI
    fields_info = {}
    for field, info in multi_matches.items():
        ctx = info["contexts"][0]  # Use first page's context
        fields_info[field] = {
            "current_xpath": info["xpath"],
            "match_count": ctx["count"],
            "surrounding_html": ctx["snippets"],
        }

    content = PROMPT_REFINE.format(fields_json=json.dumps(fields_info, ensure_ascii=False, indent=2))

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={api_key}"
    payload = {
        "contents": [{"parts": [{"text": content}]}],
        "generationConfig": {
            "temperature": 0.1,
            "maxOutputTokens": 4096,
            "responseMimeType": "application/json",
        }
    }

    resp = requests.post(url, json=payload, timeout=120)
    resp.raise_for_status()

    result = _parse_response(resp.json())
    return result.get("mappings", {})


def _detect_root_prefix(compressed_html: str) -> str:
    """Detect the root container element from compressed HTML and return an XPath prefix."""
    import re
    # Match the first opening tag with class
    m = re.match(r'<(\w+)\s+class="([^"]+)"', compressed_html.strip())
    if m:
        tag, classes = m.group(1), m.group(2)
        # Use the first meaningful class name
        cls_list = classes.split()
        for cls in cls_list:
            if len(cls) > 2 and cls not in ('l-centering', 'is-bg', 'wow', 'fadeInUp'):
                return f"//{tag}[contains(@class,'{cls}')]"
    return ""


def _add_prefix(mappings: dict, prefix: str) -> dict:
    """Ensure all XPaths are scoped under the container with // (descendant)."""
    if not prefix:
        return mappings
    # Extract the class name from prefix for stripping AI-added prefixes
    # e.g. "//div[contains(@class,'p-offerContainer')]" → "p-offerContainer"
    import re
    cls_match = re.search(r"contains\(@class,'([^']+)'\)", prefix)
    cls_name = cls_match.group(1) if cls_match else ""
    
    result = {}
    for field, xpath in mappings.items():
        # Strip any container prefix the AI may have added
        if cls_name and cls_name in xpath:
            # Find where the container selector ends and the real xpath begins
            idx = xpath.find(cls_name)
            # Skip past the closing )] and any /
            rest = xpath[idx + len(cls_name):]
            bracket_end = rest.find(']')
            if bracket_end >= 0:
                rest = rest[bracket_end + 1:].lstrip('/')
                xpath = "//" + rest if rest else xpath
        
        # Add the correct prefix with // (descendant axis)
        if xpath.startswith("//"):
            result[field] = prefix + "//" + xpath[2:]
        else:
            result[field] = xpath
    return result


def _sanitize_wantlist(wantlist: dict) -> dict:
    """Sanitize wantlist values to prevent prompt injection."""
    sanitized = {}
    for k, v in wantlist.items():
        # Keys: only allow alphanumeric + underscore
        clean_key = "".join(c for c in str(k) if c.isalnum() or c == "_")[:50]
        # Values: truncate and strip control characters
        clean_val = str(v)[:200].replace("\n", " ").replace("\r", " ")
        if clean_key:
            sanitized[clean_key] = clean_val
    return sanitized


def analyze(compressed_htmls: list, wantlist: dict = None) -> dict:
    """Call Gemini API with compressed HTMLs, return {field: xpath} dict.
    
    If wantlist is provided, use targeted mode matching the requested schema.
    Otherwise, discover all extractable fields automatically.
    """
    api_key = _get_api_key()

    if wantlist:
        wantlist = _sanitize_wantlist(wantlist)
        content = PROMPT_WANTLIST.format(wantlist=json.dumps(wantlist, ensure_ascii=False, indent=2))
    else:
        content = PROMPT_DISCOVER

    for i, html in enumerate(compressed_htmls):
        content += f"\n--- Page {i+1} ---\n{html[:8000]}\n"

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={api_key}"
    payload = {
        "contents": [{"parts": [{"text": content}]}],
        "generationConfig": {
            "temperature": 0.1,
            "maxOutputTokens": 8192,
            "responseMimeType": "application/json",
        }
    }

    resp = requests.post(url, json=payload, timeout=120)
    resp.raise_for_status()

    result = _parse_response(resp.json())

    # Auto-prefix XPaths with main content container
    if compressed_htmls:
        prefix = _detect_root_prefix(compressed_htmls[0])
        if prefix:
            result["mappings"] = _add_prefix(result["mappings"], prefix)
            result["container"] = prefix

    return result
