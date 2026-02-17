# XPathGenie 実験2: Ablation Study

実行日時: 2026-02-17 05:40:39 UTC

## 概要

代表5サイトで4つの条件を比較し、各コンポーネントの影響を測定。

### 条件

1. **Full**: 通常のフルパイプライン
2. **w/o compression**: 生HTML8000文字切り出しでそのまま渡す
3. **w/o refinement**: refineステップをスキップ
4. **w/o normalize-space**: プロンプトのnormalize-space指示をtext()=に置換

## 結果

### Hit Rate比較

| サイト | Full | w/o compression | w/o refinement | w/o normalize-space |
|--------|------|----------------|----------------|---------------------|
| #1 tsukui-staff | 0.333 | 0.000 | 0.333 | 0.333 |
| #5 mynavi | 0.000 | 0.000 | 0.000 | 0.000 |
| #14 caresta | 0.333 | 0.000 | 0.333 | 0.333 |
| #25 w-medical-9 | 0.000 | 0.000 | 0.000 | 0.000 |
| #21 MRT-nurse | 0.000 | 0.000 | 0.000 | 0.000 |

### 平均 Hit Rate

| 条件 | 平均 Hit Rate |
|------|---------------|
| Full | 0.133 |
| w/o compression | 0.000 |
| w/o refinement | 0.133 |
| w/o normalize-space | 0.133 |

## 分析

### 各コンポーネントの影響

- **w/o compression**: 平均Hit Rate 0.000 (Fullとの差: +0.133, 影響: 正)
- **w/o refinement**: 平均Hit Rate 0.133 (Fullとの差: +0.000, 影響: なし)
- **w/o normalize-space**: 平均Hit Rate 0.133 (Fullとの差: +0.000, 影響: なし)

### サイト別詳細

#### #1 tsukui-staff

- Full: hit_rate=0.333, fields=3, pages=10
- w/o compression: hit_rate=0.000, fields=2, pages=10
- w/o refinement: hit_rate=0.333, fields=3, pages=10
- w/o normalize-space: hit_rate=0.333, fields=3, pages=10

#### #5 mynavi

- Full: hit_rate=0.000, fields=0, pages=0
- w/o compression: hit_rate=0.000, fields=2, pages=10
- w/o refinement: hit_rate=0.000, fields=0, pages=0
- w/o normalize-space: hit_rate=0.000, fields=0, pages=0

#### #14 caresta

- Full: hit_rate=0.333, fields=3, pages=10
- w/o compression: hit_rate=0.000, fields=0, pages=0
- w/o refinement: hit_rate=0.333, fields=3, pages=10
- w/o normalize-space: hit_rate=0.333, fields=3, pages=10

#### #25 w-medical-9

- Full: hit_rate=0.000, fields=2, pages=1
- w/o compression: hit_rate=0.000, fields=2, pages=1
- w/o refinement: hit_rate=0.000, fields=2, pages=1
- w/o normalize-space: hit_rate=0.000, fields=2, pages=1

#### #21 MRT-nurse

- Full: hit_rate=0.000, fields=2, pages=10
- w/o compression: hit_rate=0.000, fields=2, pages=10
- w/o refinement: hit_rate=0.000, fields=2, pages=10
- w/o normalize-space: hit_rate=0.000, fields=2, pages=10
