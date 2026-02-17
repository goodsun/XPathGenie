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

## 推奨: A + B の統合 — Escalation Model

### コンセプト: 「困った時だけ助けを求めるAI」

普段は完全自動。失敗した時だけ人間に聞く。

### 統合フロー

```
URL → Fetch → 候補セクション抽出
                 │
           候補が1個のみ?
           │YES                    │NO（複数候補）
           ↓                       ↓
    [確認モード]               [選択モード]
    ブラックアウト             候補を切り替えながら
    プレビュー表示             ブラックアウト確認
    「これでOK?」             「どれ?」
           │                       │
           ↓                       ↓
    選択セクションで Compress → Gemini分析 → Validate
                                              │
                                        全フィールド0%?
                                        │NO → ✅ 完了
                                        │YES ↓
                                   [エスカレーション]
                                   ブラックアウトプレビュー再表示
                                   「うまくいかなかった。別の部分を選んで」
                                   ユーザーが別候補を選択 → 再分析
```

### モード切り替え

| モード | 挙動 | 用途 |
|--------|------|------|
| `auto` | 候補1で自動実行 → 0%なら候補2で自動リトライ（最大2回） | API/バッチ/CLI |
| `confirm` | 候補1をブラックアウトプレビューで確認 → OK/変更 | 初回セットアップ |
| `auto+escalate` | 普段はauto、失敗時のみプレビューでユーザーに聞く | **SaaS推奨** |

### ブラックアウト表示

削除される部分を暗転させることで「Geminiに見える範囲」を直感的に可視化。

```css
/* 削除される部分 */
.xpg-removed {
  opacity: 0.1;
  filter: grayscale(1);
  pointer-events: none;
  transition: opacity 0.3s;
}

/* メインセクション（残る部分） */
.xpg-main-section {
  outline: 3px solid #b366ff;
  outline-offset: 2px;
  position: relative;
}

/* 候補切り替え時のアニメーション */
@keyframes xpg-pulse {
  0%   { outline-color: rgba(179, 102, 255, 1.0); }
  50%  { outline-color: rgba(179, 102, 255, 0.3); }
  100% { outline-color: rgba(179, 102, 255, 1.0); }
}
.xpg-main-section.active {
  animation: xpg-pulse 1.5s infinite;
}
```

### 副次効果

- **compression-generation gapの可視化ツール**としても機能
- 論文の図（Before/After）をこのプレビューからスクショで作れる
- ノイズパターン調整のデバッグが直感的に
- ユーザーが「なぜ失敗したか」を自分で理解できる → サポートコスト減

---

## 提案C: Pre-Analysis Section Selector（本命）

### コンセプト: AIの前に人間が範囲を絞る

Tier 1（圧縮）の**前**にユーザーがメインコンテンツを指定する。既存パイプラインに変更不要、入力HTMLの範囲が狭まるだけ。

### フロー

```
URL入力 → Fetch → プレビュー表示
                      │
              [1. メインコンテンツ選択]
              ユーザーがクリック → 緑枠で「ここを分析」
                      │
              [2. 除外選択（オプション）]
              ネストされた不要部分をクリック → 赤枠で「ここは除外」
              （例: 応募フォーム、関連求人、SNSシェアボタン）
                      │
              選択範囲のHTML抽出
                      │
              Tier 1: Compress（選択範囲のみ）
                      │
              Tier 2: Gemini生成
                      │
              結果表示
```

### 利用パターン

| パターン | フロー | 対象ユーザー |
|----------|--------|-------------|
| フル自動 | URL → analyze（従来通り） | 初心者、大半のサイト |
| 手動選択 | URL → プレビュー → 選択 → analyze | 上級者、初回セットアップ |
| フォールバック | フル自動で失敗 → 選択モードで再実行 | トラブル時 |

### 2段階セレクション

1. **Include（緑）**: メインコンテンツ範囲を指定
   - `<body>`全体 → `<section id="maincontents">` に絞るイメージ
2. **Exclude（赤）**: その中から除外する部分を指定（オプション）
   - 応募フォーム、関連記事、広告など
   - NOISE_PATTERNSのハードコードが不要になる

```
ページ全体
  └─ メインコンテンツ ← 緑: Include
       ├─ 求人テーブル ← 残る
       ├─ 詳細情報 ← 残る
       └─ 応募フォーム ← 赤: Exclude
```

### 技術実装

```python
# API変更（既存analyzeにパラメータ追加のみ）
POST /api/analyze
{
  "urls": [...],
  "selector": "section#maincontents",      # Include
  "exclude": [".entry_box", "form.apply"]   # Exclude（オプション）
}

# 内部処理
html = fetch(url)
if selector:
    html = extract_section(html, selector)  # 選択範囲だけ抽出
if exclude:
    html = remove_sections(html, exclude)   # 除外部分を削除
compressed = compress(html)                 # 既存ロジックそのまま
```

### なぜこれが本命か

- **既存パイプラインの変更がほぼゼロ** — compress()への入力が変わるだけ
- **AIコスト増なし** — セクション選択にGeminiを使わない
- **NOISE_PATTERNSのハードコード問題を根本解決** — 人間が目で見て判断
- **副作用リスクゼロ** — 他のサイトに影響しない
- **SaaS差別化** — 「見て選ぶ」直感的UX
- **3パターンのユースケースを1機能でカバー**

### サイトプロファイル保存（将来）

選択結果をドメイン単位で保存すれば、同じサイトの2回目以降は自動適用。
使えば使うほど賢くなるプロダクト。

```json
{
  "domain": "yakuzaishisyusyoku.net",
  "selector": "div.detail_box",
  "exclude": ["div.entry_box"],
  "created": "2026-02-18",
  "last_used": "2026-02-18"
}
```

---

## 全体の推奨優先順位

| 優先度 | 提案 | 内容 | 工数 |
|--------|------|------|------|
| ★★★ | **C** | Pre-Analysis Section Selector（Include/Exclude） | 3-5時間 |
| ★★☆ | **A** | Auto Fallback（0%リトライ） | 4-5時間 |
| ★☆☆ | **B** | ブラックアウトプレビュー（Escalation） | 7-10時間 |

- C → A → B の順で実装
- Cだけでも大きな価値がある
- BはCのUIを拡張する形で後から追加可能

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
