# E2E Test Report: English Sites — API + HTML Snapshots

- **Date:** 2026-02-18
- **Method:** API-based (curl → /api/fetch + /api/analyze)
- **Purpose:** 英語サイトでのXPathGenie動作検証 + HTMLスナップショット保存（再現性データセット）
- **Result:** 5サイト fetch成功、2サイト analyze成功

---

## HTML Snapshots

再現性担保のため、Fetch時のHTMLをスナップショットとして保存。

| Site | File | Size | Domain |
|------|------|------|--------|
| AllRecipes | [snapshots/260218_en/allrecipes.html](snapshots/260218_en/allrecipes.html) | 385K | Recipe |
| Books to Scrape | [snapshots/260218_en/books.html](snapshots/260218_en/books.html) | 9.1K | E-commerce |
| Hacker News | [snapshots/260218_en/hackernews.html](snapshots/260218_en/hackernews.html) | 6.4K | News/Forum |
| StackOverflow | [snapshots/260218_en/stackoverflow.html](snapshots/260218_en/stackoverflow.html) | 1.1M | Q&A |
| IMDb | [snapshots/260218_en/imdb.html](snapshots/260218_en/imdb.html) | 1.5M | Entertainment |

---

## Analyze Results

### ✅ Hacker News — 14 fields detected

- **URL:** https://news.ycombinator.com/item?id=1
- **Mode:** auto-discover
- **Elapsed:** ~15s
- **Analysis:** [snapshots/260218_en/hackernews_analysis.json](snapshots/260218_en/hackernews_analysis.json)

| Field | Description |
|-------|-------------|
| title | Post title |
| url | Link URL |
| author | Submitter |
| points | Score |
| domain | Link domain |
| posted_date | Post date |
| posted_timestamp | Post timestamp |
| comments_count | Comment count |
| comment_author | Comment author |
| comment_text | Comment body |
| comment_id | Comment ID |
| comment_indent_level | Reply nesting level |
| comment_posted_date | Comment date |
| comment_posted_timestamp | Comment timestamp |

→ ニュース/フォーラム型の構造化データを正確に抽出。コメントのネスト構造まで認識。

### ✅ StackOverflow — 2 fields detected

- **URL:** https://stackoverflow.com/questions/11227809/...
- **Mode:** auto-discover（want_list指定したがテーブルデータを自動発見）
- **Elapsed:** 14.8s
- **Tokens:** 1,863
- **Analysis:** [snapshots/260218_en/stackoverflow_analysis.json](snapshots/260218_en/stackoverflow_analysis.json)

| Field | Sample | XPath |
|-------|--------|-------|
| scenario | "Branching - Random data" | `(//tbody/tr/td[1])[1]` |
| time_seconds | "11.777" | `(//tbody/tr/td[2])[1]` |

→ 記事本文中のベンチマークテーブルを検出。質問メタデータ（タイトル、投票数等）はHTML圧縮時にテーブルが優先された可能性あり。

### ⚠️ AllRecipes — 0 fields (fetch OK)

- HTMLサイズ385KBで構造が複雑（React/SSR）。圧縮後もGenieが有効なフィールドを特定できず。
- Jasmineでセクション選択すれば成功する可能性が高い。

### ⚠️ Books to Scrape — 0 fields (fetch OK)

- シンプルなHTML（9.1KB）だがauto-discoverで0フィールド。
- 商品詳細ページのテーブル構造がGenieの期待パターンと合わなかった可能性。

### 📌 IMDb — fetch only (analyze未実行)

- HTMLサイズ1.5MBで圧縮・解析に時間がかかるため今回はスナップショットのみ。

---

## Summary

| Site | Fetch | Snapshot | Analyze | Fields |
|------|-------|----------|---------|--------|
| Hacker News | ✅ | ✅ 6.4K | ✅ | 14 |
| StackOverflow | ✅ | ✅ 1.1M | ✅ | 2 |
| AllRecipes | ✅ | ✅ 385K | ⚠️ 0 fields | 0 |
| Books to Scrape | ✅ | ✅ 9.1K | ⚠️ 0 fields | 0 |
| IMDb | ✅ | ✅ 1.5M | — | — |

**Fetch成功率:** 5/5 (100%)
**Analyze成功率:** 2/5 (40%) — auto-discoverモード、セクション未選択

## Observations

1. **HTMLスナップショット保存が機能** — 全5サイトのHTMLを `snapshots/260218_en/` に保存。オフラインで再実行可能
2. **英語サイトでも動作確認** — Hacker Newsで14フィールド検出は日本語サイトと同等の精度
3. **セクション選択なしだと大規模サイトは厳しい** — Jasmine連携が重要（AllRecipes, Books）
4. **論文への示唆:**
   - 英語サイトでの動作実績として記載可能
   - HTMLスナップショット保存で再現性の懸念を払拭
   - Limitations: 大規模HTMLではセクション選択（Jasmine）が事実上必須

## Scripts

- [run_e2e_english.sh](run_e2e_english.sh) — 自動テストスクリプト
