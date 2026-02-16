# サイト分析プロンプト

XPathGenie評価対象サイトの構造分析を自動化するためのプロンプト。
サブエージェントに投げて並列実行可能。

## 目的

各求人サイトについて以下を調査し、`info.txt` と `url_lists.txt` に記録する：

1. **レンダリング方式** — SSR（curl取得可）か SPA（JS必須）か
2. **一覧ページの構造** — 求人カードの並び方、使用タグ
3. **詳細ページの構造** — dt/dd, th/td, div-based 等のデータ表示パターン
4. **詳細ページURL 10件** — Genie/Aladdinに直接投入できる形式
5. **特記事項** — 文字コード、WAF、ログイン必須、特殊構造など

## 手順

```
対象サイト: {URL}

以下の手順で分析してください。

### Step 1: 一覧ページ取得
curl -sL -o /tmp/site_list.html -w "%{http_code}" -A "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36" "{URL}" --max-time 15

- 403/5xx → アクセス不可として記録
- 200 → Step 2へ

### Step 2: 一覧ページ構造分析
pythonでlxmlを使い以下を確認:
- title
- 求人詳細へのリンクパターン（/detail, /job/, /offer/, 数字ID等）
- dt/dd, th/td の数とラベル
- カード構造（class名にjob, item, result, card, recruit等を含む要素）
- body textの文字数（少なすぎる = SPA疑い）
- script srcにchunk, app, nuxt, next, react, vue等 = SPA確定

詳細リンクが0件 & body text < 5000文字 → SPA疑い

### Step 3: 詳細ページ取得・分析
一覧から見つかった詳細リンク1件をcurlで取得し:
- dt/dd の数とラベル一覧（先頭10件）
- th/td の数とラベル一覧（先頭10件）
- table数
- body textが少なければSPA

### Step 4: URL 10件収集
一覧ページから詳細リンクを最大10件抽出:
- フラグメント(#xxx)は除去
- 相対URLは絶対URLに変換
- 重複除去
- 1行1URL、番号なし

### Step 5: 200チェック
10件全てに対してHTTPステータス確認:
curl -sL -o /dev/null -w "%{http_code}" -A "Mozilla/5.0 ..." --max-time 10 "{url}"

### Step 6: 記録

info.txt に追記（フォーマット）:
======================================================================
#{番号} {サイト名} ({ドメイン}) — {業種}
分析日: {日付}
----------------------------------------------------------------------
レンダリング: 一覧={SSR|SPA}, 詳細={SSR|SPA}

一覧ページ ({パス}):
  構造: {タグ.class} カード形式, {N}件/ページ
  カード内{dt|th}: {ラベル一覧}
  詳細リンク: {パターン}
  ページネーション: {方式}

詳細ページ ({例URL}):
  構造: {dt/dd|th/td|混在} 形式, {dt|th}数{N}
  主要ラベル: {ラベル一覧}
  テーブル: {N}

ID取得: {URLパス|URLクエリ} {パターン}
特記: {文字コード, WAF, 特殊構造等}

url_lists.txt に追記:
#{番号} {サイト名} ({業種}, {構造タイプ})
{URL1}
{URL2}
...
{URL10}
```

## 構造パターン分類

| パターン | 説明 | 例 |
|----------|------|-----|
| dt/dd | 定義リスト。ラベル=dt, 値=dd | tsukui, selva-i, nikken |
| th/td | テーブル。ラベル=th, 値=td | phget, yakumatch, caresta |
| dt/dd+th/td | 混在。概要=dt/dd, 詳細=th/td等 | apuro, cocofump, yakusta |
| テーブル(分割) | 1フィールド=1テーブル | pharmapremium |
| div-based | セマンティックタグなし、class依存 | SPA系 |

## SPA判定基準

以下のいずれかに該当 → SPA（Playwright必須）:
- curlで取得したbody textが3000文字未満
- 求人詳細リンクが1件も見つからない
- script srcに `chunk`, `app.`, `nuxt`, `_next`, `react`, `vue`, `angular` を含む
- Tailwind utility classesのみでセマンティック構造なし

## 注意事項

- 文字コード: Shift_JIS/EUC-JPの場合、lxmlパース時にエンコーディング指定が必要
- WAF: Incapsula, CloudFlare等でブロックされる場合あり
- 会員制: /offer/list等がログインページにリダイレクトされる場合は「ログイン必須」
- URL正規化: フラグメント(#form_01等)は除去、相対パスは絶対URLに変換
