# XPathGenie — 設計書

> **"Rub the lamp, get the XPath."**
> 「3つの願いはいらない。URLだけくれ。」

## 概要

URLを複数入力するだけで、そのサイトから取得可能なデータ要素とXPathマッピングをAIが自動生成するWebアプリケーション。

AIのトークン消費は**サイトあたり1回だけ**（マッピング生成時のみ）。生成されたXPathマッピングを使えば、以降はAI不要で純粋なDOM操作だけでデータ取得できる。

## 解決する課題

- Webスクレイピングで最も面倒な「どのXPathで何が取れるか」の調査をAIが代行
- サイトごとにラベル表記が違っても（「お給料」「給与」「報酬」）、AIが意味を理解して統一フィールド名を付与
- 複数ページで検証するため、信頼性の高いXPathが得られる
- エンジニア以外でも使えるWeb UI

## ユースケース

- 求人サイトのデータ収集（teddy_crawler連携）
- ECサイトの価格・在庫監視
- 不動産サイトの物件情報取得
- ニュース・記事サイトの構造解析
- 行政サイトの公開情報取得
- 任意のWebサイトの構造化データ抽出

## アーキテクチャ

```
[Web UI]  URL入力 → 結果表示・編集 → JSON/YAML出力
    ↓
[API]  POST /api/analyze  {urls: [...]}
    ↓
[Backend]
    fetcher.py      HTML取得（SSRF防御付き）
        ↓
    compressor.py   メインコンテンツ抽出・構造圧縮（トークン節約）
        ↓
    analyzer.py     Gemini API → XPathマッピング生成
        ↓
    validator.py    全URLでXPath検証 → 信頼度スコア
        ↓
[Output]  {フィールド名: XPath, ...}
```

## ディレクトリ構成

```
XPathGenie/
├── app.py              # Flask API + Web UI サーブ
├── genie/
│   ├── __init__.py
│   ├── fetcher.py      # HTML取得（SSRF防御、User-Agent、タイムアウト）
│   ├── compressor.py   # HTML→構造要約（メインコンテンツ抽出、トークン圧縮）
│   ├── analyzer.py     # Gemini API呼び出し → XPathマッピング生成
│   └── validator.py    # 複数ページでXPath実行 → 値取得確認 → 信頼度
├── templates/
│   └── index.html      # Web UI
├── static/
│   └── style.css
├── docs/
│   └── DESIGN.md       # この設計書
├── README.md
└── requirements.txt
```

## 処理フロー詳細

### 1. fetcher.py — HTML取得

- 入力: URL配列（2〜5個推奨）
- SSRF防御: プライベートIP拒否、スキーム制限（http/https）
- レスポンスサイズ上限: 10MB
- User-Agent設定、タイムアウト15秒
- SSRサイト前提（SPA対応は将来Playwright連携で）

### 2. compressor.py — 構造圧縮

目的: AIに渡すトークン量を最小化する。

- `<header>`, `<footer>`, `<nav>`, `<script>`, `<style>` を除去
- `<main>` or `<article>` or 最大テキスト密度セクションを自動検出
- 繰り返し構造（同クラスの要素群）は1〜2サンプルに縮約
- テキストノードは先頭N文字に切り詰め（値のサンプルとして残す）
- 目標: 1ページあたり数KB以内

### 3. analyzer.py — AI解析

- Gemini API（gemini-2.5-flash）を使用
- 圧縮HTML + 「このページから取得可能な情報要素とXPathを列挙してください」
- AIが意味を理解して汎用フィールド名を付与（最小公倍数的命名）
  - 「時給1,200円」→ `price`
  - 「大阪府柏原市」→ `prefecture`
  - 「くすのきクリニック」→ `facility_name`
- 出力形式: `{"フィールド名": "XPath", ...}`
- 複数ページ分の圧縮HTMLをまとめて渡し、共通構造からXPathを導出

### 4. validator.py — 検証

- 生成されたXPathを全入力URLに対して実行
- 各XPathについて:
  - 値が取れたページ数 / 全ページ数 → 信頼度スコア
  - 取得値のサンプル表示
  - 値が取れないページがあれば「オプショナル」フラグ
- 信頼度が低いXPathは警告表示

## Web UI

### 入力画面
- URL入力フィールド（複数行、2〜5個）
- 「Analyze」ボタン
- ローディング表示（Gemini API待ち）

### 結果画面
- フィールド名 | XPath | 信頼度 | サンプル値 のテーブル
- 各行を編集可能（フィールド名のリネーム、XPathの修正）
- JSON / YAML でコピー・ダウンロード
- teddy_crawler用YAML形式でのエクスポート

## API

### POST /api/analyze

```json
// Request
{
  "urls": [
    "https://example.com/detail?id=100",
    "https://example.com/detail?id=101",
    "https://example.com/detail?id=102"
  ]
}

// Response
{
  "site": "example.com",
  "mappings": {
    "facility_name": {
      "xpath": "//dl[6]//dd",
      "confidence": 1.0,
      "samples": ["くすのきクリニック", "千種さわやかクリニック", "..."]
    },
    "price": {
      "xpath": "//dl[10]//dd",
      "confidence": 1.0,
      "samples": ["時給1,200円〜1,300円", "月給22万円〜25万円", "..."]
    }
  },
  "pages_analyzed": 3,
  "tokens_used": 1500
}
```

## teddy_crawler連携

生成されたマッピングはteddy_crawlerのYAML設定にそのまま流し込める:

```yaml
# XPathGenieが生成 → cadical.yaml の mapping セクションへ
mapping:
  facility_name: "//dl[6]//dd"
  prefecture: "//dl[7]//dd"
  price: "//dl[10]//dd"
  ...
```

将来的にはXPathGenieからteddy_crawlerの設定ファイルを直接生成するエクスポート機能も想定。

## 技術スタック

- **Backend**: Python + Flask
- **AI**: Gemini 2.5 Flash（低コスト、十分な解析能力）
- **HTML解析**: 標準ライブラリ（html.parser）+ 正規表現
- **XPath実行**: lxml（検証フェーズ用）
- **Frontend**: Vanilla HTML/CSS/JS（CDNなし、シンプル）

## セキュリティ

- SSRF防御（fetcher.pyにteddy_crawlerと同等の防御）
- Gemini APIキーはサーバーサイド保持（クライアントに露出しない）
- レート制限（連続リクエスト防止）

## 将来拡張

- SPA対応（Playwright連携でJSレンダリング後のHTML取得）
- 一覧ページ解析（ページネーション構造の自動検出）
- マッピング履歴の保存・バージョン管理
- サイト構造変更の自動検知（定期的にXPathが壊れてないか確認）
- teddy_crawler設定ファイルの直接生成・プッシュ
- 複数サイト間のフィールド名統一（統一スキーマへの自動マッピング）
