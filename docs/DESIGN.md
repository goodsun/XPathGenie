# XPathGenie — Design Document

> **"Rub the lamp, get the XPath."**

## Overview

XPathGenie is a web application that auto-generates XPath mappings from URLs using AI. The AI is invoked **once per site** (at mapping generation time); subsequent data extraction uses pure DOM operations with no AI cost.

## Problem Statement

- Manual XPath discovery for web scraping is time-consuming (~5-6 hours per site)
- Label variations across sites ("お給料", "給与", "報酬") require semantic understanding
- Single-page testing is unreliable; cross-page validation is needed
- Non-engineers need accessible tooling

## 3-Tool Architecture: G-A-J

```
┌─────────────┐    localStorage    ┌─────────────┐    localStorage    ┌─────────────┐
│   Jasmine    │ ──────────────→  │    Genie     │ ──────────────→  │   Aladdin    │
│  (Join)      │                   │  (Generate)  │                   │  (Analyze)   │
│              │                   │              │                   │              │
│ Section      │                   │ AI-powered   │                   │ Cross-page   │
│ selector     │                   │ XPath gen    │                   │ validation   │
│ with preview │                   │ + Refine     │                   │ + editing    │
└─────────────┘                   └─────────────┘                   └─────────────┘
  jasmine.html                      index.html                       aladdin.html
```

**Cross-tool communication:** All three tools share state via `localStorage`, enabling seamless handoffs (e.g., "Open in Aladdin" button passes URLs + mappings automatically).

### Jasmine — Pre-Analysis Section Selector
- Interactive preview of fetched pages
- Click to select main content (include) and noise sections (exclude)
- Client-side HTML extraction before sending to API
- i18n support (Japanese/English)

### Genie — XPath Mapping Generator
- Two modes: Auto Discover and Want List
- Compresses HTML → sends to Gemini → validates XPaths → auto-refines
- Core pipeline: Fetch → Compress → Analyze → Validate → Refine

### Aladdin — Cross-Page Validator
- Tests XPaths against up to 10 URLs simultaneously
- Tab-based per-page result comparison
- Real-time XPath editing with instant re-evaluation
- Export to JSON/YAML

## Directory Structure

```
XPathGenie/
├── app.py                  # Flask API server (routes + orchestration)
├── index.html              # Genie frontend (Vue 3 CDN)
├── aladdin.html            # Aladdin frontend
├── jasmine.html            # Jasmine frontend (i18n)
├── requirements.txt
├── genie/                  # Backend modules
│   ├── __init__.py
│   ├── fetcher.py          # HTML fetcher (SSRF protection, encoding detection)
│   ├── compressor.py       # HTML structural compression (lxml)
│   ├── analyzer.py         # Gemini API integration + Refine
│   └── validator.py        # XPath validation, multi-match detection, narrowing
├── templates/
│   └── index.html          # Flask root route template
├── static/
│   ├── css/
│   ├── js/
│   └── images/
├── wallpapers/             # Wallpaper gallery page
│   ├── index.html
│   └── images/
├── scripts/                # Evaluation & experiment scripts
│   ├── evaluate_site.py
│   ├── experiment1_reproducibility.py
│   ├── experiment2_ablation.py
│   └── ...
├── docs/
│   ├── DESIGN.md           # This document
│   ├── whitepaper.md       # Technical whitepaper
│   ├── ISSUES.md
│   ├── evaluation/         # Experiment reports & results
│   └── proposals/          # Design proposals
├── README.md
└── LICENSE
```

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Backend | Python / Flask |
| Frontend | Vue 3 (CDN) / Vanilla CSS |
| AI | Gemini 2.5 Flash |
| HTML Parsing | **lxml** (fromstring, etree, tostring) |
| XPath Execution | lxml |
| Theme | Dark theme + glassmorphism |

## Pipeline Detail

### 1. fetcher.py — HTML Retrieval

- **Input:** URL array (2-10)
- **SSRF protection:** Blocks private IPs (10.x, 172.16.x, 192.168.x, 127.x, link-local, IPv6 private)
- **Encoding detection:** HTTP header → HTML meta charset → fallback chain (utf-8, shift_jis, euc-jp, cp932)
- **Parallel fetching:** ThreadPoolExecutor, max 5 workers
- **Limits:** 10MB response size, 15s timeout
- **Cleanup:** Strips XML declarations and DOCTYPE to prevent lxml parser issues

### 2. compressor.py — Structural Compression

Reduces full HTML pages (often 500KB+) to a few KB for AI analysis.

**Process:**
1. Parse with `lxml.html.fromstring()`
2. Remove `<script>`, `<style>`, `<noscript>`, `<iframe>`, `<svg>`, `<link>`, `<meta>`, `<head>`
3. Strip `<header>`, `<footer>`, `<nav>`, `<aside>`
4. Remove noise sections matching `NOISE_PATTERNS` regex (recommend, sidebar, widget, breadcrumb, modal, footer, banner, ad, popup, cookie, privacy, contact, sns, share, entry, apply, registration)
5. Find main content section via `_find_main_section()`:
   - Try `<main>` → `<article>` → structured data section (th/td, dt/dd density) → largest div
   - Score candidates by text content, excluding noise-pattern matches
6. `_find_structured_section()`: Finds nearest common ancestor of th/dt elements, merges multiple sections if no dominant one
7. Truncate text nodes to 30 chars
8. Remove empty elements
9. Collapse whitespace

### 3. analyzer.py — AI Analysis

- **Model:** Gemini 2.5 Flash (`gemini-2.5-flash`)
- **Two prompts:** `PROMPT_DISCOVER` (auto) and `PROMPT_WANTLIST` (targeted)
- **Output:** JSON `{field_name: xpath_expression}`
- **Auto-prefixing:** Detects root container class from compressed HTML, scopes all XPaths under it
- **Wantlist sanitization:** Keys limited to alphanumeric+underscore (50 chars), values truncated to 200 chars
- **Response parsing:** Handles markdown code blocks, truncated JSON, null values

### 4. validator.py — Validation

- Executes each XPath against all fetched pages using lxml
- **Content scoring:** Ranks multiple matches by structural context:
  - `+20` for `<main>`/`<article>` ancestors
  - `-20` for `<aside>`/`<nav>`/`<footer>` ancestors
  - `+10`/`-10` for class-based signals (detail, content, sidebar, recommend, etc.)
  - `+depth` (deeper = more specific = preferred)
- Calculates confidence = pages_with_hits / total_pages
- Flags optional fields (confidence < 1.0)
- Warns on multi-match fields

### 5. Refine Pipeline

When XPaths match multiple nodes on a page:

```
validate() → find_multi_matches() → narrow_by_first_match() → refine() → re-validate()
```

#### find_multi_matches()
- Detects fields where `doc.xpath()` returns >1 node on any page
- Collects surrounding HTML snippets (parent chain, up to 4 matches) as context
- Tracks `all_identical` flag: whether all matched values across all pages are the same

#### narrow_by_first_match() — Mechanical Narrowing (AI cost: 0)
- For `all_identical=True` fields only
- Splits XPath into `container // core` parts
- Walks ancestor chain of each matched element looking for class-bearing ancestors
- Tests candidate XPaths with intermediate class insertion until exactly 1 match
- Example: `//container//core` → `//container//div[contains(@class,'detail-body')]//core`

#### refine() — AI Refinement
- For fields with different values across matches
- Sends surrounding HTML context to Gemini with `PROMPT_REFINE`
- AI determines which match is "primary" and returns more specific XPath

## Error Handling

The API uses structured error responses:

```json
{
  "status": "error",
  "reason": "fetch_failed | access_denied | timeout | compression_empty | analysis_failed | no_fields_detected",
  "message": "Human-readable error description",
  "suggestion": "Actionable advice for the user",
  "diagnostics": {
    "compressed_size_bytes": 0,
    "encoding_warning": "...",
    "compression_warning": "..."
  }
}
```

**Error reasons:**
| Reason | Trigger | HTTP Status |
|--------|---------|-------------|
| `fetch_failed` | All URLs failed to fetch | 400 |
| `access_denied` | 403 from target site | 400 |
| `timeout` | Fetch timeout | 400 |
| `compression_empty` | Compressed HTML is empty (likely SPA) | 422 |
| `analysis_failed` | Gemini API error | 500 |
| `no_fields_detected` | AI returned 0 fields | 200 |

## Security

- **SSRF protection:** Private IP blocking in fetcher.py
- **Rate limiting:** 30 requests/minute per IP (`_check_rate_limit()`)
- **Origin checking:** Referer/Origin header validation against `ALLOWED_ORIGINS` whitelist
- **API key isolation:** Gemini key stored server-side only
- **Wantlist sanitization:** Prevents prompt injection via field names/values

## API Endpoints

### POST /api/analyze
Main analysis endpoint. Accepts `{urls, wantlist?}`, returns validated XPath mappings with confidence scores.

### GET /api/fetch?url=...
Server-side HTML fetch for Aladdin (CORS bypass). Returns `{html, url}`.

### GET /
Serves the Genie frontend (`templates/index.html`).

## Future Extensions

- SPA support (Playwright integration for JS-rendered pages)
- Listing page analysis (pagination structure detection)
- Mapping history / version management
- Automated structure change detection
- Unified cross-site schema mapping
