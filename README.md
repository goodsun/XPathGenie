# XPathGenie

> **"Rub the lamp, get the XPath."**

URLを入力するだけで、ページから取得可能なデータ要素とXPathマッピングをAIが自動生成するWebアプリ。

## 何ができる？

1. 解析したいページのURLを2〜3個入力
2. AIがページ構造を解析し、取得可能な要素を発見
3. 各要素のXPathと汎用フィールド名を自動生成
4. 複数ページで検証済みの信頼度スコア付き

AIを使うのは**マッピング生成時の1回だけ**。生成されたXPathで以降はAI不要のデータ取得が可能。

## 技術スタック

- **Backend**: Python / Flask
- **Frontend**: Vue 3 (CDN) / Vanilla CSS
- **AI**: Gemini 2.5 Flash
- **HTML解析**: lxml

## セットアップ

```bash
pip install flask lxml
python app.py
```

## 使い方

1. ブラウザで `http://localhost:8789` を開く
2. 解析したいページのURLを入力（同一サイトの詳細ページを2〜3個）
3. 「Analyze」をクリック
4. 結果のマッピングをJSON/YAMLでコピー・ダウンロード

## API

```
POST /api/analyze
Content-Type: application/json

{
  "urls": [
    "https://example.com/detail?id=100",
    "https://example.com/detail?id=101"
  ]
}
```

## ライセンス

MIT License — see [LICENSE](LICENSE)

## Author

goodsun
