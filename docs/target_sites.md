# XPathGenie 評価対象サイト（33サイト）

論文評価用。詳細ページURLの自動発見→Genie分析→Aladdin検証のパイプラインで使う。

## アイデア: Auto URL Discovery
1. サイトのトップ/一覧ページをfetch
2. 全 `<a href>` 抽出
3. URLパターン検出（数値IDを含むパス等）
4. 同一パターンのURLを10件収集
5. → そのままGenieに投入

## サイトリスト

| # | URL | ドメイン |
|---|-----|---------|
| 1 | https://kaigo-garden.jp/ | 介護 |
| 2 | https://phama.selva-i.co.jp/ | 薬剤師 |
| 3 | https://www.pha-navi.net/kensaku/?sien=3&kinmu=&rosen= | 薬剤師 |
| 4 | https://yakuzaishi.yakumatch.com/ | 薬剤師 |
| 5 | https://pharma.mynavi.jp/ | 薬剤師 |
| 6 | https://www.phget.com/search | 薬剤師 |
| 7 | https://career.pha-net.jp/search/ | 薬剤師 |
| 8 | https://www.apuro.com/search/?tabType=1 | 薬剤師 |
| 9 | https://www.oshigoto-lab.com/job?tab=area&pref=&line= | 医療 |
| 10 | https://www.yakuzaishisyusyoku.net/kyujin/#kyujin_list | 薬剤師 |
| 11 | https://rikunabi-yakuzaishi.jp/ | 薬剤師 |
| 12 | https://yakuzaishibestcareer.com/pref/search/ALL/ | 薬剤師 |
| 13 | https://pharmapremium.jp/list/?search_type=search | 薬剤師 |
| 14 | https://www.caresta.jp/search/result.php?areas=&search=do | 介護 |
| 15 | https://mjc-pharmajob.com/search/ | 薬剤師 |
| 16 | https://www.k-pharmalink.co.jp/search-result/?mode=search&job_type=&employment=&area=&line=&area_city=&station=&fuwatto=&special_conditions=&keyword= | 薬剤師 |
| 17 | https://kaigo.medical-cubic.com/ | 介護 |
| 18 | https://nikken-mc.com/care/search | 介護 |
| 19 | https://nikken-mc.com/nurse/search | 看護 |
| 20 | https://cocofump-job.net/jobfind-pc/area/All | 介護 |
| 21 | https://nurse.medrt.com/recruit/list | 看護 |
| 22 | https://nurse.bunnabi.jp/ | 看護 |
| 23 | https://www.seiyakuonline.com/ | 製薬 |
| 24 | https://kaigo-work.jp/ | 介護 |
| 25 | https://w-medical-9.com/kyujin_ichiran.html?sel_jd_local_ken_code=&sel_free=&x=159&y=37 | 医療 |
| 26 | https://kango.firstnavi.jp/ | 看護 |
| 27 | https://www.iryou21.jp/ | 医療 |
| 28 | https://kaigo-career.jp/data.php?c=search | 介護 |
| 29 | https://tokyo-yakuzaishi-kyujin.com/ | 薬剤師 |
| 30 | https://mc-pharma.net/jobs/search | 薬剤師 |
| 31 | https://www.ph-10.com/search/area_staff/ | 薬剤師 |
| 32 | https://yakusta.com/job/ | 薬剤師 |
| 33 | https://www.pasonamedical.com/job_search/?jobType=11707,11711,11703 | 医療 |
| 34 | https://iryoushoku.cadical.jp/ | 医療 |
| 35 | https://kaigokango.jp/recruit?pref=&salary=&salary_type= | 介護看護 |

---

## サイト分析ログ

Genie分析・teddy_crawler統合時に記録する各サイトの特徴。プロンプト改善の素材 & SPA率の統計データとして蓄積。

### 記録項目
- **レンダリング**: SSR / SPA（JS必須） / SSR+部分SPA
- **一覧ページ構造**: `<table>`, `<ul>/<li>`, `<div>` カード, etc.
- **詳細ページ構造**: `<dl>/<dt>/<dd>`, `<table>`, 自由HTML, etc.
- **ID取得方法**: URLパラメータ / URLパス / HTML属性
- **特記事項**: CloudFlare防御, ページネーション方式, 特殊な構造など

---

### #34 cadical (iryoushoku.cadical.jp)
- **分析日**: 2026-02-16
- **ドメイン**: 医療求人
- **レンダリング**: **一覧=SPA（JSレンダリング）**, 詳細=SSR
  - 一覧ページはcurlで取得不可、Playwright経由で取得成功
  - 詳細ページはHTTP Engine（requests）で取得可能
- **一覧ページ構造**: `<div class="sc-recruit__item">` カード形式
  - タイトル: `.sc-recruit__item__title`
  - 求人ID: テキスト内 `求人ID : \d+`
  - 更新日: テキスト内 `更新日 : YYYY/MM/DD`
- **詳細ページ構造**: `<dl>/<dt>/<dd>` 形式（dt=ラベル, dd=値）
  - teddy_crawler の `dt_dd` パーサーで完全対応
  - 17フィールド → unified schema マッピング済み
- **ID取得方法**: URLクエリパラメータ `?job_id=\d+`
- **ページネーション**: `?p={page}` パラメータ、約90ページ
- **特記事項**:
  - 一覧がSPAなのは35サイト中では少数派（多くはSSR）
  - 詳細ページのdt/ddは非常に整った構造で、XPathGenie向き
  - Genieテスト時: 圧縮率良好、マッピング精度高
