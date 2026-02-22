# XPathAbu — DomCatcher 🐒

## Proposal: Interactive XPath Inspector Chrome Extension

**Date:** 2026-02-22
**Status:** Proposal
**Author:** goodsun / Teddy

---

## Overview

XPathAbu（通称 Abu）は、XPathGenieファミリーの新メンバーとなるChrome拡張機能。
ページ上のDOM要素をクリックするだけでXPathを取得し、XPathGenie APIと連携してAI推論による最適化まで行うインタラクティブなXPath調査ツール。

**名前の由来:** アラジンの猿の相棒Abu + Abuse（悪用）。DOMから情報を「かっぱらう」小さな相棒。

---

## XPathGenieファミリー

| Tool | Character | Role | Head Letter |
|------|-----------|------|-------------|
| **Genie** | 魔法のランプの精 | AI推論エンジン（XPath自動生成） | G |
| **Jasmine** | 王女 | インタラクティブUI（セクション選択、吹き出し） | J |
| **Aladdin** | 盗賊→英雄 | 分析・評価（Analyze） | A |
| **Abu** 🆕 | 猿の相棒、手癖が悪い | DOM要素キャッチャー（Chrome拡張） | A |

---

## UI Design

```
┌──────────────────────────────────┐
│  🐒 XPathAbu — DomCatcher       │
├──────────────────────────────────┤
│ XPath:                           │
│ ┌──────────────────────────────┐ │
│ │ /html/body/div[2]/h1         │ │  ← 上段: XPath入力テキストボックス
│ └──────────────────────────────┘ │    （DOM要素クリックで自動入力）
│                                  │
│  [📋 Copy]  [🔍 Analyze]        │  ← ボタン2つ
│                                  │
│ Result:                          │
│ ┌──────────────────────────────┐ │
│ │ "AIエージェントの脳トレ入門" │ │  ← 下段: 取得結果表示エリア
│ │                              │ │    （XPathで取れる情報を表示）
│ └──────────────────────────────┘ │
└──────────────────────────────────┘
```

---

## Core Features

### 1. DOM Click → XPath Auto-fill
- ページ上の任意の要素をクリック
- クリックされた要素のXPathを上段テキストボックスに自動入力
- 同時にそのXPathで取得できるテキスト/属性を下段に表示
- ホバー時にハイライト表示（要素の境界を可視化）

### 2. Copy Button
- 上段のXPathをクリップボードにコピー
- ワンクリックで他のツール（Jasmine、スクレイパー等）に貼り付け可能

### 3. Analyze Button → XPathGenie API連携
- 現在のXPathとページ構造をXPathGenie API (localhost:8789) に送信
- Genie（AI推論）が最適なXPathを推論して返す
- 推論結果を上段に反映、下段に取得結果を更新
- 「手動で見つけたXPath」→「AIが最適化したXPath」への橋渡し

---

## Use Cases

1. **XPath調査**: 「この要素のXPathって何？」をクリックだけで即座に確認
2. **スクレイピング開発**: XPathを試行錯誤しながら、Copy→コードに貼り付け
3. **XPathGenie連携**: 手動XPathをAIに投げて、より堅牢なXPathに改善
4. **教育**: XPathの学習ツールとして（クリック→XPath→結果が見える）

---

## Technical Stack

- Chrome Extension (Manifest V3)
- Content Script: DOM要素のクリック検知、XPath生成、ハイライト
- Popup/Side Panel: UI（テキストボックス2つ + ボタン2つ）
- Background Service Worker: XPathGenie API通信

---

## Mascot

🐒 Abu — 小さな猿。ブラウザの片隅にちょこんといて、クリックしたDOM要素をかっぱらってくる。
キャラデザ: XPathGenieファミリーの壁紙ページ（https://corp.bon-soleil.com/xpathgenie/wallpapers/）に追加予定。

---

## Priority

Medium — XPathGenieの実用性を大幅に向上させる補助ツール。
開発規模は小（Chrome拡張のみ、バックエンドはGenie API既存）。
