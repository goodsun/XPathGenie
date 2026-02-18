#!/usr/bin/env python3
"""Cross-domain evaluation for XPathGenie whitepaper.
Evaluates 5 non-medical sites across different domains.
Uses the actual API response format (auto-discovery, mappings with confidence).
"""
import json, requests, time, sys, os

API = "http://127.0.0.1:8789/api/analyze"
TIMEOUT = 180  # 3 min per site

SITES = [
    {
        "id": "cd1_carsensor",
        "name": "カーセンサー (EC/中古車)",
        "domain": "E-commerce",
        "urls": [
            "https://www.carsensor.net/usedcar/bTO/index.html",
        ],
    },
    {
        "id": "cd2_suumo",
        "name": "SUUMO (不動産/賃貸)",
        "domain": "Real Estate",
        "urls": [
            "https://suumo.jp/jj/chintai/ichiran/FR301FC001/?ar=030&bs=040&ta=13&sc=13101",
        ],
    },
    {
        "id": "cd3_cookpad",
        "name": "Cookpad (レシピ/UGC)",
        "domain": "Recipe/UGC",
        "urls": [
            "https://cookpad.com/search/%E3%82%AB%E3%83%AC%E3%83%BC",
        ],
    },
    {
        "id": "cd4_tabelog",
        "name": "食べログ (グルメ/レビュー)",
        "domain": "Restaurant/Review",
        "urls": [
            "https://tabelog.com/tokyo/rstLst/RC1201/",
        ],
    },
    {
        "id": "cd5_yahoo_news",
        "name": "Yahoo!ニュース (ニュース)",
        "domain": "News",
        "urls": [
            "https://news.yahoo.co.jp/categories/domestic",
        ],
    },
]

def evaluate_site(site, run_num=None):
    """Evaluate a single site via XPathGenie API."""
    print(f"\n{'='*60}")
    print(f"Evaluating: {site['name']} ({site['domain']})")
    print(f"URLs: {site['urls']}")
    print(f"{'='*60}")

    payload = {"urls": site["urls"]}

    start = time.time()
    try:
        resp = requests.post(API, json=payload, timeout=TIMEOUT)
        elapsed = time.time() - start
        data = resp.json()
    except Exception as e:
        elapsed = time.time() - start
        print(f"  ERROR: {e} (after {elapsed:.1f}s)")
        return {"site": site["id"], "name": site["name"], "domain": site["domain"],
                "error": str(e), "elapsed_sec": round(elapsed, 1)}

    result = {
        "site": site["id"],
        "name": site["name"],
        "domain": site["domain"],
        "urls": site["urls"],
        "elapsed_sec": round(elapsed, 1),
        "status": data.get("status", "unknown"),
    }

    if data.get("status") != "ok":
        result["error"] = data.get("message", data.get("error", "unknown error"))
        result["reason"] = data.get("reason", "")
        print(f"  API Error: {result['error']}")
        print(f"  Reason: {result.get('reason', '')}")

        # Save anyway
        suffix = f"_run{run_num}" if run_num else ""
        outpath = os.path.join(os.path.dirname(__file__), "results",
                               f"{site['id']}_wantlist{suffix}.json")
        with open(outpath, "w") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        return result

    mappings = data.get("mappings", {})
    result["fields_count"] = len(mappings)
    result["pages_analyzed"] = data.get("pages_analyzed", 0)
    result["tokens_used"] = data.get("tokens_used", 0)
    result["refined_fields"] = data.get("refined_fields", [])

    # Compute hit rate from confidence values
    confidences = []
    result["fields"] = {}
    for fname, fdata in mappings.items():
        conf = fdata.get("confidence", 0)
        confidences.append(conf)
        result["fields"][fname] = {
            "xpath": fdata.get("xpath", ""),
            "confidence": conf,
            "samples": fdata.get("samples", [])[:3],
            "optional": fdata.get("optional", False),
            "warning": fdata.get("warning", None),
        }

    result["avg_confidence"] = round(sum(confidences) / len(confidences), 3) if confidences else 0
    result["perfect_fields"] = sum(1 for c in confidences if c == 1.0)

    print(f"  Status: {data['status']}")
    print(f"  Fields discovered: {len(mappings)}")
    print(f"  Avg confidence (=hit rate): {result['avg_confidence']:.0%}")
    print(f"  Perfect fields: {result['perfect_fields']}/{len(mappings)}")
    print(f"  Time: {elapsed:.1f}s")
    print(f"  Tokens: {result['tokens_used']}")

    for fname, fdata in result["fields"].items():
        status = "✓" if fdata["confidence"] == 1.0 else f"{fdata['confidence']:.0%}"
        warn = " ⚠" if fdata.get("warning") else ""
        samples = [s[:40] if s else "(miss)" for s in fdata["samples"][:2]]
        print(f"    {fname}: {status}{warn}  {samples}")

    # Save result
    suffix = f"_run{run_num}" if run_num else ""
    outpath = os.path.join(os.path.dirname(__file__), "results",
                           f"{site['id']}_wantlist{suffix}.json")
    with open(outpath, "w") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print(f"  Saved: {outpath}")

    return result


def main():
    run_num = int(sys.argv[1]) if len(sys.argv) > 1 else None
    site_filter = sys.argv[2] if len(sys.argv) > 2 else None

    results = []
    for site in SITES:
        if site_filter and site_filter not in site["id"]:
            continue
        result = evaluate_site(site, run_num)
        results.append(result)
        time.sleep(2)

    # Summary
    print(f"\n{'='*60}")
    print("CROSS-DOMAIN EVALUATION SUMMARY")
    print(f"{'='*60}")
    total_fields = 0
    total_perfect = 0
    successful = 0
    for r in results:
        if "error" in r and r.get("status") != "ok":
            print(f"  {r['site']}: ❌ {r.get('error','')[:60]}")
        else:
            hr = r.get("avg_confidence", 0)
            nf = r.get("fields_count", 0)
            pf = r.get("perfect_fields", 0)
            t = r.get("elapsed_sec", 0)
            total_fields += nf
            total_perfect += pf
            successful += 1
            print(f"  {r['site']}: {hr:.0%} hit rate, {nf} fields ({pf} perfect), {t:.0f}s")

    if successful > 0:
        print(f"\n  Total: {successful}/{len(results)} sites successful")
        print(f"  Total fields: {total_fields} ({total_perfect} perfect)")
        avg_hr = sum(r.get("avg_confidence", 0) for r in results if r.get("status") == "ok") / successful
        print(f"  Macro avg hit rate: {avg_hr:.1%}")


if __name__ == "__main__":
    main()
