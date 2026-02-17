#!/usr/bin/env python3 -u
"""
Ablation Study v2 — APIベースで正しく実行

4条件:
1. Full pipeline (通常の /api/analyze)
2. w/o compression (analyzer直接呼び出し、raw HTML 8000char)
3. w/o refinement (app.pyのrefineロジックをスキップ)
4. w/o normalize-space (プロンプトをmonkey-patch)

2,3,4はmonkey-patchでコンポーネントを無効化してからAPIを叩く。
"""

import sys, os, json, time, re
sys.path.insert(0, '/home/ec2-user/tools/XPathGenie')

from scripts.evaluate_site import load_urls, fetch_html, eval_xpath, DEFAULT_WANTLIST, analyze as api_analyze
from lxml import html as lxml_html
import requests

API_BASE = "http://127.0.0.1:8789"

TARGET_SITES = [
    "#1 tsukui-staff",
    "#5 mynavi",
    "#14 caresta",
    "#25 w-medical-9",
    "#21 MRT-nurse"
]

def run_via_api(site_key, wantlist=None):
    """Fullパイプライン: 既存evaluate_site.pyと同じ方法でAPIを叩く"""
    urls = load_urls(site_key)
    if not urls:
        return None

    # Step 1: Analyze via API (1st URL)
    payload = {"urls": [urls[0]]}
    if wantlist:
        payload["wantlist"] = wantlist
    
    try:
        resp = requests.post(f"{API_BASE}/api/analyze", json=payload, timeout=120)
        if resp.status_code != 200:
            print(f"    API error: {resp.status_code}")
            return None
        data = resp.json()
        if data.get("status") == "error":
            print(f"    API error: {data.get('reason')}")
            return None
    except Exception as e:
        print(f"    Request failed: {e}")
        return None

    mappings = {}
    for k, v in data.get("mappings", {}).items():
        if isinstance(v, dict):
            mappings[k] = v.get("xpath", "")
        elif isinstance(v, str):
            mappings[k] = v

    if not mappings:
        return {"fields": 0, "pages": 0, "hit_rate": 0.0, "detail": {}}

    # Step 2: Validate across all pages
    pages = []
    for url in urls[:10]:
        html = fetch_html(url)
        if html:
            try:
                doc = lxml_html.fromstring(html)
                pages.append(doc)
            except:
                pass
        time.sleep(0.3)

    if not pages:
        return {"fields": len(mappings), "pages": 0, "hit_rate": 0.0, "detail": {}}

    # Step 3: Evaluate
    field_results = {}
    for field, xpath in mappings.items():
        hits = 0
        for doc in pages:
            result = eval_xpath(xpath, doc)
            if result:
                hits += 1
        field_results[field] = hits / len(pages) if pages else 0

    avg_hit_rate = sum(field_results.values()) / len(field_results) if field_results else 0

    return {
        "fields": len(field_results),
        "pages": len(pages),
        "hit_rate": round(avg_hit_rate, 3),
        "detail": field_results
    }


def run_ablation_no_compression(site_key):
    """w/o compression: raw HTMLの先頭8000文字をそのまま渡す"""
    import genie.compressor as comp
    import genie.analyzer as analyzer_mod
    
    urls = load_urls(site_key)
    if not urls:
        return None

    # Fetch raw HTML
    html = fetch_html(urls[0])
    if not html:
        return None

    # Raw HTML (no compression), truncated to 8000 chars
    raw_truncated = html[:8000]

    # Call analyzer directly with raw HTML
    try:
        result = analyzer_mod.analyze([raw_truncated], wantlist=DEFAULT_WANTLIST)
    except Exception as e:
        print(f"    Analyzer error: {e}")
        return None

    mappings = result.get("mappings", {})
    if not mappings:
        return {"fields": 0, "pages": 0, "hit_rate": 0.0, "detail": {}}

    # Validate
    pages = []
    for url in urls[:10]:
        h = fetch_html(url)
        if h:
            try:
                pages.append(lxml_html.fromstring(h))
            except:
                pass
        time.sleep(0.3)

    field_results = {}
    for field, xpath in mappings.items():
        hits = 0
        for doc in pages:
            result = eval_xpath(xpath, doc)
            if result:
                hits += 1
        field_results[field] = hits / len(pages) if pages else 0

    avg = sum(field_results.values()) / len(field_results) if field_results else 0
    return {"fields": len(field_results), "pages": len(pages), "hit_rate": round(avg, 3), "detail": field_results}


def run_ablation_no_refinement(site_key):
    """w/o refinement: analyze後のrefineをスキップ"""
    import genie.compressor as comp
    import genie.analyzer as analyzer_mod
    from genie.fetcher import fetch_all
    
    urls = load_urls(site_key)
    if not urls:
        return None

    # Fetch & compress (normal)
    fetched = fetch_all([urls[0]])
    if not fetched or not fetched[0].get("html"):
        return None

    compressed = [comp.compress(fetched[0]["html"])]
    
    # Analyze (normal)
    try:
        result = analyzer_mod.analyze(compressed, wantlist=DEFAULT_WANTLIST)
    except Exception as e:
        print(f"    Analyzer error: {e}")
        return None

    mappings = result.get("mappings", {})
    # Skip ALL refinement — use raw mappings directly

    if not mappings:
        return {"fields": 0, "pages": 0, "hit_rate": 0.0, "detail": {}}

    # Validate
    pages = []
    for url in urls[:10]:
        h = fetch_html(url)
        if h:
            try:
                pages.append(lxml_html.fromstring(h))
            except:
                pass
        time.sleep(0.3)

    field_results = {}
    for field, xpath in mappings.items():
        hits = 0
        for doc in pages:
            r = eval_xpath(xpath, doc)
            if r:
                hits += 1
        field_results[field] = hits / len(pages) if pages else 0

    avg = sum(field_results.values()) / len(field_results) if field_results else 0
    return {"fields": len(field_results), "pages": len(pages), "hit_rate": round(avg, 3), "detail": field_results}


def run_ablation_no_normalize_space(site_key):
    """w/o normalize-space: プロンプトのnormalize-space()をtext()=に置換"""
    import genie.compressor as comp
    import genie.analyzer as analyzer_mod
    from genie.fetcher import fetch_all
    
    urls = load_urls(site_key)
    if not urls:
        return None

    # Fetch & compress (normal)
    fetched = fetch_all([urls[0]])
    if not fetched or not fetched[0].get("html"):
        return None

    compressed = [comp.compress(fetched[0]["html"])]

    # Monkey-patch prompts
    orig_discover = analyzer_mod.PROMPT_DISCOVER
    orig_wantlist = analyzer_mod.PROMPT_WANTLIST
    
    analyzer_mod.PROMPT_DISCOVER = orig_discover.replace("normalize-space()", "text()")
    analyzer_mod.PROMPT_WANTLIST = orig_wantlist.replace("normalize-space()", "text()")
    
    try:
        result = analyzer_mod.analyze(compressed, wantlist=DEFAULT_WANTLIST)
    except Exception as e:
        print(f"    Analyzer error: {e}")
        analyzer_mod.PROMPT_DISCOVER = orig_discover
        analyzer_mod.PROMPT_WANTLIST = orig_wantlist
        return None
    finally:
        # Restore
        analyzer_mod.PROMPT_DISCOVER = orig_discover
        analyzer_mod.PROMPT_WANTLIST = orig_wantlist

    mappings = result.get("mappings", {})
    if not mappings:
        return {"fields": 0, "pages": 0, "hit_rate": 0.0, "detail": {}}

    # Validate (with refinement via normal pipeline - only prompt was changed)
    pages = []
    for url in urls[:10]:
        h = fetch_html(url)
        if h:
            try:
                pages.append(lxml_html.fromstring(h))
            except:
                pass
        time.sleep(0.3)

    field_results = {}
    for field, xpath in mappings.items():
        hits = 0
        for doc in pages:
            r = eval_xpath(xpath, doc)
            if r:
                hits += 1
        field_results[field] = hits / len(pages) if pages else 0

    avg = sum(field_results.values()) / len(field_results) if field_results else 0
    return {"fields": len(field_results), "pages": len(pages), "hit_rate": round(avg, 3), "detail": field_results}


def main():
    results = {}
    
    for site in TARGET_SITES:
        print(f"\n{'='*60}")
        print(f"Site: {site}")
        print(f"{'='*60}")
        results[site] = {}
        
        conditions = [
            ("Full", run_via_api),
            ("w/o compression", run_ablation_no_compression),
            ("w/o refinement", run_ablation_no_refinement),
            ("w/o normalize-space", run_ablation_no_normalize_space),
        ]
        
        for name, func in conditions:
            print(f"\n  --- {name} ---")
            try:
                if name == "Full":
                    r = func(site, wantlist=DEFAULT_WANTLIST)
                else:
                    r = func(site)
                results[site][name] = r
                if r:
                    print(f"    => hit_rate={r['hit_rate']}, fields={r['fields']}, pages={r['pages']}")
                else:
                    print(f"    => FAILED")
            except Exception as e:
                print(f"    => ERROR: {e}")
                import traceback
                traceback.print_exc()
                results[site][name] = None
            
            time.sleep(10)  # Rate limit between conditions

    # Generate report
    report = "# XPathGenie Ablation Study v2\n\n"
    report += f"実行日時: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}\n\n"
    report += "## 条件\n\n"
    report += "1. **Full**: 通常のフルパイプライン（API経由）\n"
    report += "2. **w/o compression**: 生HTMLの先頭8000文字をそのまま渡す（圧縮なし）\n"
    report += "3. **w/o refinement**: LLM分析後のTwo-Tier Refinementをスキップ\n"
    report += "4. **w/o normalize-space**: プロンプトのnormalize-space()をtext()=に置換\n\n"
    
    report += "## Hit Rate比較\n\n"
    report += "| サイト | Full | w/o compression | w/o refinement | w/o normalize-space |\n"
    report += "|--------|------|----------------|----------------|---------------------|\n"
    
    for site in TARGET_SITES:
        row = f"| {site} "
        for cond in ["Full", "w/o compression", "w/o refinement", "w/o normalize-space"]:
            r = results[site].get(cond)
            if r:
                row += f"| {r['hit_rate']:.1%} ({r['fields']}f) "
            else:
                row += "| FAIL "
        row += "|"
        report += row + "\n"
    
    # Averages
    report += "\n## 平均 Hit Rate\n\n"
    report += "| 条件 | 平均 Hit Rate | Δ vs Full |\n"
    report += "|------|---------------|----------|\n"
    
    for cond in ["Full", "w/o compression", "w/o refinement", "w/o normalize-space"]:
        vals = [results[s].get(cond, {}) for s in TARGET_SITES if results[s].get(cond)]
        if vals:
            avg = sum(v["hit_rate"] for v in vals) / len(vals)
            full_vals = [results[s].get("Full", {}) for s in TARGET_SITES if results[s].get("Full")]
            full_avg = sum(v["hit_rate"] for v in full_vals) / len(full_vals) if full_vals else 0
            delta = avg - full_avg
            report += f"| {cond} | {avg:.1%} | {delta:+.1%} |\n"
    
    report += "\n## サイト別詳細\n\n"
    for site in TARGET_SITES:
        report += f"### {site}\n\n"
        for cond in ["Full", "w/o compression", "w/o refinement", "w/o normalize-space"]:
            r = results[site].get(cond)
            if r:
                report += f"- **{cond}**: hit_rate={r['hit_rate']:.1%}, fields={r['fields']}, pages={r['pages']}\n"
            else:
                report += f"- **{cond}**: FAILED\n"
        report += "\n"
    
    # Save
    with open("/home/ec2-user/tools/XPathGenie/docs/evaluation/ablation_report_v2.md", "w") as f:
        f.write(report)
    
    # Also save raw JSON
    with open("/home/ec2-user/tools/XPathGenie/docs/evaluation/ablation_raw_v2.json", "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False, default=str)
    
    print(f"\n✅ Report saved to ablation_report_v2.md")


if __name__ == "__main__":
    main()
