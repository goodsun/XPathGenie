#!/usr/bin/env python3 -u
"""
XPathGenie 実証実験 — 1サイト評価スクリプト

Usage:
  python3 -u scripts/evaluate_site.py "#1 tsukui-staff"

1. url_lists.txt からサイトのURL群を取得
2. 1件目を /api/analyze に投げてマッピング生成
3. 全URL(最大10件)のHTMLを取得
4. lxmlでXPath評価、フィールドごとのヒット率計算
5. 結果をJSONで docs/evaluation/results/ に保存
"""

import sys, json, time, re, os, requests
from lxml import html as lxml_html

API_BASE = "http://127.0.0.1:8789"
RESULTS_DIR = os.path.join(os.path.dirname(__file__), "..", "docs", "evaluation", "results")
URL_LISTS = os.path.join(os.path.dirname(__file__), "..", "docs", "evaluation", "url_lists.txt")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

# Default WantList — unified schema for job listing sites
DEFAULT_WANTLIST = {
    "original_id": "",
    "access": "",
    "access_label": "駅からの移動手段",
    "access_minutes": "駅からの時間",
    "address": "",
    "area": "",
    "bonus": "",
    "caractoristic": "特徴・おすすめポイント",
    "city": "",
    "contract": "雇用形態（正社員、契約社員、パート等）",
    "dept": "部署",
    "detail": "",
    "facility_name": "勤務先の施設名・会社名",
    "facility_type": "施設形態",
    "holiday": "",
    "license": "資格・免許",
    "line": "路線名",
    "name": "",
    "occupation": "職種（看護師・介護士・薬剤師等）",
    "position": "役職",
    "prefecture": "",
    "price": "",
    "price_rule": "手当や昇給などの給与の備考",
    "required_skill": "求めるスキル",
    "staff_comment": "",
    "staff_comment_title": "",
    "station": "",
    "test_period": "試用期間",
    "title_original": "",
    "welfare_program": "",
    "working_hours": "勤務時間",
    "working_style": "勤務形態",
}


def load_urls(site_key):
    """url_lists.txt からサイトのURL群を取得"""
    urls = []
    found = False
    with open(URL_LISTS) as f:
        for line in f:
            line = line.strip()
            if line.startswith(f"{site_key} ") or line == site_key:
                found = True
                continue
            if found:
                if line.startswith("#") or line == "":
                    if urls:
                        break
                    continue
                if line.startswith("http"):
                    urls.append(line)
    return urls


def analyze(url, wantlist=None):
    """Genie APIで1URLを分析"""
    print(f"[Genie] Analyzing: {url}")
    t0 = time.time()
    payload = {"urls": [url]}
    if wantlist:
        payload["wantlist"] = wantlist
    resp = requests.post(f"{API_BASE}/api/analyze", json=payload, timeout=120)
    elapsed = time.time() - t0
    if resp.status_code != 200:
        print(f"[Genie] Error {resp.status_code}: {resp.text[:200]}")
        return None, elapsed
    data = resp.json()
    if data.get("status") == "error":
        print(f"[Genie] Error: {data.get('reason', 'unknown')} — {data.get('message', '')}")
        return None, elapsed
    mappings = {}
    for k, v in data.get("mappings", {}).items():
        if isinstance(v, dict):
            mappings[k] = {
                "xpath": v["xpath"],
                "confidence": v.get("confidence", 0),
                "sample": v.get("sample", ""),
            }
        elif isinstance(v, str):
            mappings[k] = {"xpath": v, "confidence": 0, "sample": ""}
    print(f"[Genie] Got {len(mappings)} fields in {elapsed:.1f}s")
    return mappings, elapsed


def fetch_html(url):
    """HTMLを取得（エンコーディング自動検出 + XML宣言除去）"""
    try:
        resp = requests.get(url, headers={"User-Agent": UA}, timeout=15)
        resp.raise_for_status()
        content = resp.content
        # Detect encoding from meta charset
        encoding = resp.encoding or "utf-8"
        meta_match = re.search(rb'charset=["\']?([a-zA-Z0-9_-]+)', content[:4096], re.IGNORECASE)
        if meta_match:
            encoding = meta_match.group(1).decode("ascii", errors="ignore")
        # Decode
        try:
            html = content.decode(encoding)
        except (UnicodeDecodeError, LookupError):
            for enc in ("utf-8", "shift_jis", "euc-jp", "cp932"):
                try:
                    html = content.decode(enc)
                    break
                except (UnicodeDecodeError, LookupError):
                    continue
            else:
                html = content.decode("utf-8", errors="replace")
        # Strip XML declaration and DOCTYPE (breaks lxml HTML parser)
        html = re.sub(r'<\?xml[^>]*\?>', '', html, count=1)
        html = re.sub(r'<!DOCTYPE[^>]*>', '', html, count=1, flags=re.IGNORECASE)
        return html
    except Exception as e:
        print(f"[Fetch] Failed {url}: {e}")
        return None


def eval_xpath(xpath_str, doc):
    """lxmlでXPath評価"""
    try:
        results = doc.xpath(xpath_str)
        values = []
        for r in results:
            if hasattr(r, "text_content"):
                v = r.text_content().strip()
            else:
                v = str(r).strip()
            if v:
                values.append(v)
        return values if values else None
    except Exception:
        return None


def evaluate_site(site_key, mode="wantlist"):
    urls = load_urls(site_key)
    if not urls:
        print(f"[Error] No URLs found for {site_key}")
        return

    print(f"\n{'='*60}")
    print(f"Evaluating: {site_key} ({len(urls)} URLs) [mode={mode}]")
    print(f"{'='*60}")

    # Step 1: Genie analysis (1st URL)
    wantlist = DEFAULT_WANTLIST if mode == "wantlist" else None
    mappings, genie_time = analyze(urls[0], wantlist=wantlist)
    if not mappings:
        print("[Error] Genie analysis failed")
        return

    # Step 2: Fetch all pages
    pages = []
    for i, url in enumerate(urls):
        print(f"[Fetch] {i+1}/{len(urls)}: {url}")
        html_text = fetch_html(url)
        if html_text:
            try:
                doc = lxml_html.fromstring(html_text)
                pages.append({"url": url, "doc": doc})
            except Exception as e:
                print(f"[Parse] Failed: {e}")
        time.sleep(0.5)  # polite delay

    print(f"[Fetch] {len(pages)}/{len(urls)} pages fetched")

    # Step 3: Evaluate XPaths across all pages
    field_results = {}
    for field, info in mappings.items():
        xpath = info["xpath"]
        hits = 0
        values = []
        for p in pages:
            result = eval_xpath(xpath, p["doc"])
            if result:
                hits += 1
                values.append(result[0][:200])  # first value, truncated
            else:
                values.append(None)

        hit_rate = hits / len(pages) if pages else 0
        field_results[field] = {
            "xpath": xpath,
            "confidence": info["confidence"],
            "hits": hits,
            "total": len(pages),
            "hit_rate": round(hit_rate, 2),
            "sample_values": values[:3],
            "all_values": values,
        }
        status = "OK" if hit_rate == 1.0 else "WARN" if hit_rate > 0 else "FAIL"
        print(f"  [{status}] {field}: {hits}/{len(pages)} ({hit_rate:.0%})")

    # Step 4: Summary
    total_fields = len(field_results)
    perfect_fields = sum(1 for f in field_results.values() if f["hit_rate"] == 1.0)
    avg_hit_rate = sum(f["hit_rate"] for f in field_results.values()) / total_fields if total_fields else 0

    summary = {
        "site": site_key,
        "urls": [p["url"] for p in pages],
        "urls_total": len(urls),
        "urls_fetched": len(pages),
        "genie_time_sec": round(genie_time, 1),
        "fields_total": total_fields,
        "fields_perfect": perfect_fields,
        "avg_hit_rate": round(avg_hit_rate, 3),
        "fields": field_results,
    }

    print(f"\n--- Summary ---")
    print(f"Fields: {perfect_fields}/{total_fields} perfect, avg hit rate: {avg_hit_rate:.1%}")
    print(f"Genie time: {genie_time:.1f}s")

    # Step 5: Save
    os.makedirs(RESULTS_DIR, exist_ok=True)
    safe_name = re.sub(r'[^a-zA-Z0-9_-]', '_', site_key.strip('#'))
    suffix = f"_{mode}" if mode != "wantlist" else "_wantlist"
    out_path = os.path.join(RESULTS_DIR, f"{safe_name}{suffix}.json")
    with open(out_path, "w") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print(f"[Saved] {out_path}")

    return summary


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 -u scripts/evaluate_site.py '#1 tsukui-staff' [--mode auto|wantlist]")
        sys.exit(1)
    mode = "wantlist"
    if "--mode" in sys.argv:
        idx = sys.argv.index("--mode")
        if idx + 1 < len(sys.argv):
            mode = sys.argv[idx + 1]
    evaluate_site(sys.argv[1], mode=mode)
