# XPathGenie — Issues

## Open

### #1 コンプレッサーがメインコンテンツを見落とす — ✅ Resolved (2026-02-17)
- → Resolved セクションに移動

### #2 Shift-JISサイトでGenie分析タイムアウト (mc-pharma)
- **重要度**: Medium
- **発見日**: 2026-02-17
- **対象サイト**: mc-pharma
- **症状**: エンコーディング修正後もGenie分析でタイムアウト（5分超）。リトライ前はcompressed HTMLが文字化けしたまま分析に投入されていた
- **原因**: 未調査。エンコーディング修正後の再テスト必要。コンプレッサーの問題（#1）と複合している可能性
- **対策案**: エンコーディング修正 + コンプレッサー修正後に再テスト

### #3 ph-10, cadical でGenie解析が0フィールド — ✅ Resolved (2026-02-17)
- → Resolved セクションに移動

### #4 低精度サイトのDOM構造不一致 (phget, yakuzaishisyusyoku)
- **重要度**: Medium
- **発見日**: 2026-02-17
- **対象サイト**: phget (14.3%), yakuzaishisyusyoku (38.5%)
- **症状**: Genieが推定したXPathパターンが実際のDOM構造と合わない。ヘッダ系フィールドは取れるが詳細テーブルは全滅
- **原因**: サイトのHTML構造が非標準（phget: テーブルではなくdivベース、yakuzaishisyusyoku: spanベースのテキストとテーブルの混在）
- **対策案**:
  1. DOM構造の事前分析 → パターン分類
  2. 複数XPath戦略の生成・比較
  3. 低精度フィールドの自動再生成（フォールバック）

### #5 caresta の部分的XPath不一致
- **重要度**: Low
- **発見日**: 2026-02-17
- **対象サイト**: caresta (50.0%)
- **症状**: preceding-sibling軸を使った複雑なXPathが一部ページで不一致。「仕事情報」セクションは取れるが「給与・待遇」「施設情報」セクションは取れない
- **原因**: テーブルのセクション構造（h3見出し）がページによって異なる可能性
- **対策案**: XPath生成時にpreceding-sibling依存を減らす、またはページ差異を検出して警告

### #6 Full Eval実行時のセッション肥大化
- **重要度**: High（運用）
- **発見日**: 2026-02-17
- **症状**: サブエージェント経由でfull eval実行 → ポーリング往復が数百回蓄積 → セッションコンテキストが200Kトークン超過 → API 400エラー
- **対策**: full evalのような長時間バッチは `nohup bash scripts/run_full_eval.sh > /tmp/eval_full.log 2>&1 &` で直実行。サブエージェントは使わない。結果はJSONファイルから集計する
- **ステータス**: 運用回避策で対応済み

---

## Resolved

### ✅ コンプレッサーがメインコンテンツを見落とす (#1, #3)
- **解決日**: 2026-02-17
- **原因**: 複合問題
  1. `fromstring(str)` がencoding declaration付きHTMLでサイレントに失敗 → 圧縮結果0バイト
  2. `privacypolicyText` 等のノイズセクション内のth/dtがメインコンテンツ検出を狂わせた
  3. ノイズ除去がメインセクション検出の**後**だったため、ノイズのマーカーに引きずられた
  4. `_find_structured_section`がマーカー数のみでスコアリングし、テキスト量を考慮していなかった
- **対策**:
  1. `compress()` でstr→bytes fallback追加
  2. NOISE_PATTERNSに `privacy|policy|inquiry|contact|sns|share` 追加
  3. ノイズ除去をメインセクション検出の前に移動
  4. `_find_structured_section` のスコアリングをマーカー数×テキスト量に変更、複数セクションのマージ対応
  5. `body`をstructured section候補から除外

### ✅ 圧縮HTMLと生HTMLの空白差異でXPathが不一致 (ph-10: 0%→99.4%)
- **解決日**: 2026-02-17
- **原因**: 圧縮HTMLでは空白が除去されるため `text()='ラベル'` が動くが、バリデーション時の生HTMLではtd/th内に改行+空白がありマッチしない
- **対策**: Geminiプロンプトのテキストマッチ指示を `text()=` → `normalize-space()=` に全面変更

### ✅ API: 圧縮後0バイトの明示的エラー
- **解決日**: 2026-02-17
- **対策**: `app.py` で `total_compressed == 0` の場合に422エラーを理由付きで返却

### ✅ Shift-JIS/EUC-JPエンコーディング非対応
- **解決日**: 2026-02-17
- **対策**: fetcher.pyにmeta charset自動検出 + フォールバックデコード追加
- **コミット**: 24234e7

### ✅ XHTML (XML宣言付き) パース失敗
- **解決日**: 2026-02-17
- **対策**: compressor.pyでXML宣言とDOCTYPEを除去してからパース
- **コミット**: 24234e7

### ✅ API失敗時の理由が不明
- **解決日**: 2026-02-17
- **対策**: app.pyのレスポンスにstatus/reason/suggestion/diagnostics追加
- **コミット**: 24234e7
