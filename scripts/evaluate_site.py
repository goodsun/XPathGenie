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


def analyze(url):
    """Genie APIで1URLを分析"""
    print(f"[Genie] Analyzing: {url}")
    t0 = time.time()
    resp = requests.post(f"{API_BASE}/api/analyze", json={"urls": [url]}, timeout=120)
    elapsed = time.time() - t0
    if resp.status_code != 200:
        print(f"[Genie] Error {resp.status_code}: {resp.text[:200]}")
        return None, elapsed
    data = resp.json()
    mappings = {}
    for k, v in data.get("mappings", {}).items():
        mappings[k] = {
            "xpath": v["xpath"],
            "confidence": v.get("confidence", 0),
            "sample": v.get("sample", ""),
        }
    print(f"[Genie] Got {len(mappings)} fields in {elapsed:.1f}s")
    return mappings, elapsed


def fetch_html(url):
    """HTMLを取得"""
    try:
        resp = requests.get(url, headers={"User-Agent": UA}, timeout=15)
        resp.raise_for_status()
        return resp.text
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


def evaluate_site(site_key):
    urls = load_urls(site_key)
    if not urls:
        print(f"[Error] No URLs found for {site_key}")
        return

    print(f"\n{'='*60}")
    print(f"Evaluating: {site_key} ({len(urls)} URLs)")
    print(f"{'='*60}")

    # Step 1: Genie analysis (1st URL)
    mappings, genie_time = analyze(urls[0])
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
                values.append(result[0][:100])  # first value, truncated
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
        }
        status = "OK" if hit_rate == 1.0 else "WARN" if hit_rate > 0 else "FAIL"
        print(f"  [{status}] {field}: {hits}/{len(pages)} ({hit_rate:.0%})")

    # Step 4: Summary
    total_fields = len(field_results)
    perfect_fields = sum(1 for f in field_results.values() if f["hit_rate"] == 1.0)
    avg_hit_rate = sum(f["hit_rate"] for f in field_results.values()) / total_fields if total_fields else 0

    summary = {
        "site": site_key,
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
    out_path = os.path.join(RESULTS_DIR, f"{safe_name}.json")
    with open(out_path, "w") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print(f"[Saved] {out_path}")

    return summary


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 -u scripts/evaluate_site.py '#1 tsukui-staff'")
        sys.exit(1)
    evaluate_site(sys.argv[1])
