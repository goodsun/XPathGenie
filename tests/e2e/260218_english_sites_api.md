# E2E Test Report: English Sites — API + HTML Snapshots

- **Date:** 2026-02-18
- **Method:** API-based (curl → /api/fetch + /api/analyze, auto-discover mode)
- **Purpose:** 英語サイトでのXPathGenie動作検証 + HTMLスナップショット保存（再現性データセット）
- **Result:** 12サイト fetch、6ドメインで analyze成功

---

## HTML Snapshots (Reproducibility Dataset)

再現性担保のため、Fetch時のHTMLをスナップショットとして保存。オフラインでの再実行が可能。

| # | Site | File | Size | Domain |
|---|------|------|------|--------|
| 1 | Hacker News | [hackernews.html](snapshots/260218_en/hackernews.html) | 6.4K | News/Forum |
| 2 | StackOverflow | [stackoverflow.html](snapshots/260218_en/stackoverflow.html) | 1.1M | Q&A |
| 3 | Quotes to Scrape | [quotes.html](snapshots/260218_en/quotes.html) | 11K | Quote listing |
| 4 | Python PEP-8 | [pep8.html](snapshots/260218_en/pep8.html) | 120K | Documentation |
| 5 | httpbin | [httpbin.html](snapshots/260218_en/httpbin.html) | 9.4K | API Documentation |
| 6 | Wikipedia | [wikipedia.html](snapshots/260218_en/wikipedia.html) | 162K | Encyclopedia |
| 7 | AllRecipes | [allrecipes.html](snapshots/260218_en/allrecipes.html) | 385K | Recipe |
| 8 | Books to Scrape | [books.html](snapshots/260218_en/books.html) | 9.1K | E-commerce |
| 9 | IMDb | [imdb.html](snapshots/260218_en/imdb.html) | 1.5M | Entertainment |

---

## Analyze Results

### ✅ Hacker News — 14 fields
- **URL:** https://news.ycombinator.com/item?id=1
- **Domain:** News/Forum
- **Analysis:** [hackernews_analysis.json](snapshots/260218_en/hackernews_analysis.json)
- **Fields:** author, comment_author, comment_id, comment_indent_level, comment_posted_date, comment_posted_timestamp, comment_text, comments_count, domain, points, posted_date, posted_timestamp, title, url
- → コメントのネスト構造まで正確に認識

### ✅ Python PEP-8 — 8 fields
- **URL:** https://www.python.org/dev/peps/pep-0008/
- **Domain:** Documentation
- **Analysis:** [pep8_analysis.json](snapshots/260218_en/pep8_analysis.json)
- **Fields:** author, code_examples, created_date, description, post_history, ...
- → 技術ドキュメントのメタデータ＋コード例を抽出

### ✅ httpbin — 6 fields
- **URL:** https://httpbin.org/
- **Domain:** API Documentation
- **Analysis:** [httpbin_analysis.json](snapshots/260218_en/httpbin_analysis.json)
- **Fields:** base_url, description, developer_email_link, developer_website_link, name, ...
- → APIドキュメントの構造を認識

### ✅ Wikipedia — 4 fields
- **URL:** https://en.wikipedia.org/wiki/Web_scraping
- **Domain:** Encyclopedia
- **Analysis:** [wikipedia_analysis.json](snapshots/260218_en/wikipedia_analysis.json)
- **Fields:** introduction, main_content_paragraphs, section_titles, title
- → 百科事典のセクション構造を認識

### ✅ Quotes to Scrape — 3 fields
- **URL:** https://quotes.toscrape.com/page/1/
- **Domain:** Quote listing
- **Analysis:** [quotes_analysis.json](snapshots/260218_en/quotes_analysis.json)
- **Fields:** author, quote_text, tags
- → リスト型コンテンツの典型的な3要素を正確に抽出

### ✅ StackOverflow — 2 fields
- **URL:** https://stackoverflow.com/questions/11227809/...
- **Domain:** Q&A
- **Analysis:** [stackoverflow_analysis.json](snapshots/260218_en/stackoverflow_analysis.json)
- **Fields:** scenario, time_seconds
- → 記事本文中のベンチマークテーブルを検出

### ⚠️ 未成功サイト
| Site | Reason |
|------|--------|
| AllRecipes | HTML 385KB、React/SSR構造でauto-discover 0 fields。Jasmine連携推奨 |
| Books to Scrape | auto-discover 0 fields。商品詳細テーブルがパターン外 |
| IMDb | HTML 1.5MB、解析未実行（スナップショットのみ） |
| Craigslist | リンク一覧ページで構造化データなし |
| BBC News | 0 fields |

---

## Summary

| # | Site | Domain | Fields | Status |
|---|------|--------|--------|--------|
| 1 | Hacker News | News/Forum | 14 | ✅ |
| 2 | Python PEP-8 | Documentation | 8 | ✅ |
| 3 | httpbin | API Doc | 6 | ✅ |
| 4 | Wikipedia | Encyclopedia | 4 | ✅ |
| 5 | Quotes to Scrape | Quote listing | 3 | ✅ |
| 6 | StackOverflow | Q&A | 2 | ✅ |

**成功率:** 6/12 サイト (50%), 6ドメインをカバー
**合計フィールド:** 37 fields across 6 domains
**平均フィールド数:** 6.2 fields/site

## Observations (論文への示唆)

1. **英語サイトで6ドメイン成功** — 国際誌の査読者への説得力を確保
2. **HTMLスナップショット9サイト分保存** — 再現性データセットとして公開可能
3. **auto-discoverモードの限界** — 大規模HTML（>100KB）ではセクション選択（Jasmine）が事実上必須
4. **多様なドメインで動作** — News, Q&A, Documentation, Encyclopedia, API Doc, Quote listing
5. **日本語サイトのcross-domain評価（Section 4.12）と対になる英語版データ**

## Scripts
- [run_e2e_english.sh](run_e2e_english.sh) — 自動テストスクリプト
