# Proposal: Adaptive Section Selection with Fallback

## 問題
コンプレッサーのメインセクション選択が、求人詳細テーブルではなく応募フォーム等の誤ったセクションを選ぶケースがある（例: yakuzaishisyusyoku）。

現状はNOISE_PATTERNSのハードコード正規表現で対応しているが：
- サイトごとに異なるclass命名に対応しきれない
- パターン追加で別サイトに副作用が出るリスク
- ルールベースの限界

## 提案: ヒット率0%自動リトライ

### 概要
分析後にバリデーションを行い、全フィールドヒット率0%の場合に圧縮セクションを変更して自動リトライする。

### フロー

```
[通常フロー]
URL → Fetch → Compress(候補1) → Gemini分析 → Validate(10URLs)
                                                    │
                                              全フィールド0%?
                                              │NO → 完了
                                              │YES ↓
                                    [フォールバック]
                                    Compress(候補1を除外, 候補2) → Gemini分析 → Validate → 完了
```

### 実装ポイント

1. **compressor改修**
   - `compress(html, exclude_sections=[])`に除外リスト引数を追加
   - `_find_structured_section()`が選んだセクションのidentifier（class/id/tagpath）を返す
   - 次回呼び出し時にそのidentifierを除外して次の候補を返す

2. **analyzer改修（app.py）**
   - analyze後にバリデーション（既存のvalidate相当）を実行
   - 全フィールドヒット率0%を検知
   - フォールバック圧縮→再分析のループ（最大2回）

3. **evaluate_site.py改修**
   - 同様のフォールバックロジック追加
   - ログに「Fallback triggered」を記録

### コスト影響

| ケース | 追加コスト | 頻度 |
|--------|-----------|------|
| 成功（通常） | なし | ~90%のサイト |
| フォールバック1回 | +1 Gemini APIコール + ~20秒 | ~10%のサイト |
| フォールバック2回（上限） | +2 Gemini APIコール + ~40秒 | ごく稀 |

### 論文への影響

- Section 3（Pipeline）に「Adaptive Section Selection」を追加可能
- 「自動検知→自己修復」は差別化ポイントになる
- 既存の失敗ケース分析（Section 4.9）と接続できる
- タイトル案: "Adaptive Section Selection with Zero-Hit Fallback"

### リスク

- フォールバック先も0%の場合は改善しない（ただし悪化もしない）
- 2回のGemini呼び出しで異なるフィールド名が出る可能性 → 2回目のマッピングで上書き
- formタグ内のtableが本当にメインコンテンツなサイトでは、正しいセクションを除外してしまう可能性 → ヒット率0%が条件なので、そもそも取れてない場合のみ発動するため安全

### 代替案

1. **LLMベースのセクション選択** — 圧縮前にGeminiに聞く。精度最高だがコスト常時増
2. **2段階圧縮** — 粗い全体→LLM判定→精密圧縮。アーキテクチャ変更大
3. **formタグスコア減算** — form配下のth/tdのスコアを0.5倍にする。簡単だがサイト依存のリスクあり

---

## 提案B: Interactive Section Selection（Human-in-the-loop）

### 概要
候補セクションを複数抽出し、実際のサイトプレビュー上でハイライト表示。ユーザーが目視で選択してから分析を実行する。

### UXフロー

```
URL入力 → Fetch → 候補セクション抽出（3-5個）
                         │
                    [プレビュー画面]
                    実サイトをiframe表示
                    候補セクションを紫の点滅ハイライトで表示
                    「候補1」「候補2」「候補3」ボタンで切り替え
                    ユーザーが選択 → クリック
                         │
                    選択セクションで Compress → Gemini分析 → 結果表示
```

### ハイライト実装

CSSアニメーション注入のみ。JS最小限（候補切り替え用）。

```css
@keyframes xpg-highlight {
  0%   { background-color: rgba(179, 102, 255, 0.3); }
  50%  { background-color: rgba(179, 102, 255, 0.0); }
  100% { background-color: rgba(179, 102, 255, 0.3); }
}
.xpg-candidate-active {
  animation: xpg-highlight 1s infinite;
  outline: 3px solid #b366ff;
  outline-offset: 2px;
}
.xpg-candidate-inactive {
  outline: 1px dashed rgba(179, 102, 255, 0.3);
}
```

### 技術実装

1. **候補抽出** — compressorの`_find_structured_section()`を拡張し、スコア上位3-5個を返す
2. **プレビュー生成** — fetchしたHTMLにCSS/JSを注入してiframe表示
   - 各候補セクションにdata属性（`data-xpg-candidate="1"`）を付与
   - 候補切り替えボタンのオーバーレイUI
3. **選択API** — `POST /api/analyze` に `section_selector` パラメータを追加
4. **Aladdin統合** — 分析前ステップとしてプレビュー画面を組み込み

### メリット

- **確実性が段違い** — 人間が見れば一発
- **ノイズパターンの副作用リスクがゼロ** — ルール追加不要
- **XPathGenieの設計思想と一致** — 「AIに丸投げしない」人間×AI協働
- **SaaS差別化** — 他のスクレイピングツールにはないインタラクティブUX
- **Aladdinとの親和性◎** — 検証UIの自然な拡張

### デメリット

- 完全自動化ではなくなる（ユーザー操作が1回必要）
- iframe内のCSS/JS競合リスク（sandbox + スタイルスコープで対応）
- CORS制約のあるサイトではプレビューが表示できない可能性

### SaaS化での位置づけ

```
Jasmine（フロント）: プレビュー＋候補選択UI
Genie（バックエンド）: 候補抽出＋分析
Aladdin（検証UI）: 結果検証＋修正
```

ユーザーの最初のタッチポイントがJasmineになる → キャラクターの役割と完全に一致。

---

## 推奨: A + B の組み合わせ

| モード | 用途 | 実装 |
|--------|------|------|
| **Auto（提案A）** | API/バッチ利用、プログラマティック実行 | ヒット率0%フォールバック |
| **Interactive（提案B）** | Aladdin UI / SaaS利用、初回セットアップ | ユーザー選択 |

- APIは `mode=auto`（デフォルト）と `mode=interactive` を切り替え可能
- Auto で十分な精度が出る場合はユーザー介入不要
- 困難なサイトや高精度が必要な場合は Interactive を選択

## 実装見積もり

### 提案A（Auto Fallback）
- compressor.py: 候補管理の追加 — 1-2時間
- app.py: フォールバックループ — 1時間
- evaluate_site.py: 同等の変更 — 30分
- テスト（yakuzaishisyusyoku + 回帰確認）— 1時間
- **小計: 4-5時間**

### 提案B（Interactive Selection）
- compressor.py: 複数候補返却 — 1-2時間
- 新API: `POST /api/candidates` — 1時間
- プレビューHTML生成（CSS/JS注入）— 2-3時間
- Aladdin UI統合 — 2-3時間
- テスト — 1時間
- **小計: 7-10時間**

### 合計: 11-15時間（A先行 → B追加）
