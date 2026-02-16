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
- Do NOT include navigation, header, footer, or boilerplate fields
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


def analyze(compressed_htmls: list, wantlist: dict = None) -> dict:
    """Call Gemini API with compressed HTMLs, return {field: xpath} dict.
    
    If wantlist is provided, use targeted mode matching the requested schema.
    Otherwise, discover all extractable fields automatically.
    """
    api_key = _get_api_key()

    if wantlist:
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

    return _parse_response(resp.json())
