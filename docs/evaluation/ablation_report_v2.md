# XPathGenie Ablation Study v2

実行日時: 2026-02-17 09:25:54 UTC

## 条件

1. **Full**: 通常のフルパイプライン（API経由）
2. **w/o compression**: 生HTMLの先頭8000文字をそのまま渡す（圧縮なし）
3. **w/o refinement**: LLM分析後のTwo-Tier Refinementをスキップ
4. **w/o normalize-space**: プロンプトのnormalize-space()をtext()=に置換

## Hit Rate比較

| サイト | Full | w/o compression | w/o refinement | w/o normalize-space |
|--------|------|----------------|----------------|---------------------|
| #1 tsukui-staff | 89.3% (30f) | 95.0% (12f) | 91.0% (30f) | 87.8% (23f) |
| #5 mynavi | 69.6% (24f) | FAIL | 70.0% (20f) | 80.4% (28f) |
| #14 caresta | 81.5% (13f) | FAIL | 82.9% (14f) | 46.2% (13f) |
| #25 w-medical-9 | 100.0% (24f) | 100.0% (25f) | 100.0% (16f) | 100.0% (20f) |
| #21 MRT-nurse | 100.0% (8f) | 0.0% (0f) | 100.0% (5f) | 100.0% (6f) |

## 平均 Hit Rate

| 条件 | 平均 Hit Rate | Δ vs Full |
|------|---------------|----------|
| Full | 88.1% | +0.0% |
| w/o compression | 65.0% | -23.1% |
| w/o refinement | 88.8% | +0.7% |
| w/o normalize-space | 82.9% | -5.2% |

## サイト別詳細

### #1 tsukui-staff

- **Full**: hit_rate=89.3%, fields=30, pages=10
- **w/o compression**: hit_rate=95.0%, fields=12, pages=10
- **w/o refinement**: hit_rate=91.0%, fields=30, pages=10
- **w/o normalize-space**: hit_rate=87.8%, fields=23, pages=10

### #5 mynavi

- **Full**: hit_rate=69.6%, fields=24, pages=10
- **w/o compression**: FAILED
- **w/o refinement**: hit_rate=70.0%, fields=20, pages=10
- **w/o normalize-space**: hit_rate=80.4%, fields=28, pages=10

### #14 caresta

- **Full**: hit_rate=81.5%, fields=13, pages=10
- **w/o compression**: FAILED
- **w/o refinement**: hit_rate=82.9%, fields=14, pages=10
- **w/o normalize-space**: hit_rate=46.2%, fields=13, pages=10

### #25 w-medical-9

- **Full**: hit_rate=100.0%, fields=24, pages=1
- **w/o compression**: hit_rate=100.0%, fields=25, pages=1
- **w/o refinement**: hit_rate=100.0%, fields=16, pages=1
- **w/o normalize-space**: hit_rate=100.0%, fields=20, pages=1

### #21 MRT-nurse

- **Full**: hit_rate=100.0%, fields=8, pages=10
- **w/o compression**: hit_rate=0.0%, fields=0, pages=0
- **w/o refinement**: hit_rate=100.0%, fields=5, pages=10
- **w/o normalize-space**: hit_rate=100.0%, fields=6, pages=10

