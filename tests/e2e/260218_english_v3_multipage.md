# English Multi-Page Evaluation Report (v3)

- **Date:** 2026-02-18
- **Method:** API `/api/analyze` with 3 URLs per site (auto-discover mode)
- **Referer:** `https://corp.bon-soleil.com/`
- **Purpose:** Multi-page hit rate evaluation for English sites that succeeded in v1 single-page tests

---

## Summary

| Site | Fields | Full Hit (1.0) | Partial Hit (>0) | Miss (0.0) | Avg Confidence | Elapsed |
|------|--------|----------------|-------------------|------------|----------------|---------|
| Wikipedia | 4 | 3 (75%) | 0 | 1 (25%) | 0.75 | 33.5s |
| Quotes to Scrape | 4 | 4 (100%) | 0 | 0 | **1.00** | 18.2s |
| StackOverflow | 12 | 7 (58%) | 5 (42%) | 0 | 0.86 | 44.3s |
| HackerNews | 3 | 2 (67%) | 1 (33%) | 0 | **0.89** | 33.5s |
| Python PEP | 13 | 2 (15%) | 1 (8%) | 10 (77%) | 0.21 | 16.5s |

### Overall (excl. PEP)
- **23 fields across 4 sites, 12 pages**
- **Full hit rate: 16/23 = 69.6%**
- **Any hit rate: 22/23 = 95.7%**
- **Average confidence: 0.87**

### Overall (all 5 sites)
- **36 fields across 5 sites, 15 pages**
- **Full hit rate: 18/36 = 50.0%**
- **Any hit rate: 25/36 = 69.4%**
- **Average confidence: 0.63**

---

## Per-Site Details

### ✅ Wikipedia (3 pages: Web_scraping, Data_mining, Machine_learning)

| Field | Confidence | Note |
|-------|------------|------|
| title | 1.0 | `//h1[contains(@class, 'firstHeading')]` |
| short_description | 1.0 | `//div[contains(@class, 'shortdescription')]` |
| introduction_text | 1.0 | Multi-match warning (includes multiple paragraphs) |
| section_headings | 0.0 | `//div[...]/h2` — refined but still 0 (XPath mismatch) |

**Notes:** Core fields (title, description, intro) work perfectly. Section headings XPath failed validation despite refinement. 3/4 fields = 75% hit rate.

### ✅ Quotes to Scrape (3 pages: /page/1/, /page/2/, /page/3/)

| Field | Confidence | Note |
|-------|------------|------|
| quote_text | 1.0 | Perfect extraction |
| author_name | 1.0 | Perfect extraction |
| tags | 1.0 | Perfect extraction |
| author_about_link | 1.0 | Perfect extraction |

**Notes:** Perfect 100% hit rate. Simple, well-structured HTML. Ideal benchmark site.

### ✅ StackOverflow (3 questions: #11227809, #927358, #231767)

| Field | Confidence | Note |
|-------|------------|------|
| question_title | 1.0 | |
| question_description | 1.0 | |
| asked_date | 1.0 | |
| modified_date | 1.0 | |
| view_count | 1.0 | |
| vote_count | 1.0 | |
| tags | 1.0 | |
| question_author_name | 0.67 | Missing on 1/3 pages |
| question_author_reputation | 0.67 | Missing on 1/3 pages |
| question_author_gold_badges | 0.67 | Missing on 1/3 pages |
| question_author_silver_badges | 0.67 | Missing on 1/3 pages |
| question_author_bronze_badges | 0.67 | Missing on 1/3 pages |

**Notes:** 12 fields discovered — impressive depth. Core Q&A metadata hits 100%. Author profile fields at 67% due to page layout variations (community wiki posts have no author card). Average confidence 0.86.

### ✅ HackerNews (3 threads: #35543855, #37052586, #38432486)

| Field | Confidence | Note |
|-------|------------|------|
| comment_text | 1.0 | |
| comment_paragraphs | 1.0 | |
| comment_code_blocks | 0.67 | Not all threads have code in comments |

**Notes:** 3 fields from comment-heavy pages. Clean extraction. Code block field is contextual (not all threads contain code snippets).

### ⚠️ Python PEP (3 PEPs: 0008, 0020, 0484)

| Field | Confidence | Note |
|-------|------------|------|
| title | 1.0 | |
| main_content | 1.0 | |
| abstract | 0.67 | PEP-20 has no abstract section |
| author–resolution (10 fields) | 0.0 | Metadata table structure varies between PEPs |

**Notes:** PEP pages have drastically different structures. PEP-8 has a full metadata table; PEP-20 ("Zen of Python") is minimal. The AI discovered 13 fields from PEP-8 but most XPaths didn't generalize. Title and main_content are the only reliable cross-page fields.

---

## Analysis

### Strengths
- **Consistent sites excel:** Quotes to Scrape (100%), Wikipedia core fields (100%), StackOverflow core fields (100%)
- **Auto-discover finds relevant fields:** SO found 12 fields including badges/reputation, HN found comment structure
- **Multi-page validation works:** Confidence scores accurately reflect generalizability

### Weaknesses
- **Heterogeneous page structures:** PEP pages vary too much for auto-discover to generalize
- **Over-discovery on variable sites:** PEP generated 13 fields but only 3 generalize — discovery was too aggressive

### Recommendations
- For heterogeneous sites (PEP-like), **Want List mode** with specific target fields would yield better results
- Consider filtering out fields with confidence < 0.5 in the final output
- StackOverflow's 0.67 fields are legitimate edge cases (community wiki), not bugs

---

## HTML Snapshots

All HTML snapshots saved in `snapshots/260218_en_v3/`:

| File | Size | Source |
|------|------|--------|
| wikipedia_1.html | 165KB | Web_scraping |
| wikipedia_2.html | 292KB | Data_mining |
| wikipedia_3.html | 689KB | Machine_learning |
| quotes_1.html | 11KB | /page/1/ |
| quotes_2.html | 14KB | /page/2/ |
| quotes_3.html | 10KB | /page/3/ |
| pep_1.html | 123KB | PEP-8 |
| pep_2.html | 11KB | PEP-20 |
| pep_3.html | 255KB | PEP-484 |
| so_1.html | 1.1MB | #11227809 |
| so_2.html | 963KB | #927358 |
| so_3.html | 769KB | #231767 |
| hn_1.html | 10KB | #35543855 |
| hn_2.html | 503KB | #37052586 |
| hn_3.html | 216KB | #38432486 |

Analysis JSONs: `*_analysis.json` (5 files)
