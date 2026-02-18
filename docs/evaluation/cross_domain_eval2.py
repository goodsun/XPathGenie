#!/usr/bin/env python3
"""Cross-domain evaluation round 2 - second site per domain."""
import json, requests, time, sys, os

API = "http://127.0.0.1:8789/api/analyze"
TIMEOUT = 180

SITES = [
    {
        "id": "cd6_goo_net",
        "name": "goo-net (EC/中古車)",
        "domain": "E-commerce",
        "urls": ["https://www.goo-net.com/usedcar/brand-TOYOTA/"],
    },
    {
        "id": "cd7_homes",
        "name": "LIFULL HOME'S (不動産/賃貸)",
        "domain": "Real Estate",
        "urls": ["https://www.homes.co.jp/chintai/tokyo/chiyoda-city/list/"],
    },
    {
        "id": "cd8_rakuten_recipe",
        "name": "楽天レシピ (レシピ)",
        "domain": "Recipe",
        "urls": ["https://recipe.rakuten.co.jp/category/30/"],
    },
    {
        "id": "cd9_hotpepper",
        "name": "ホットペッパーグルメ (グルメ)",
        "domain": "Restaurant",
        "urls": ["https://www.hotpepper.jp/SA11/"],
    },
    {
        "id": "cd10_nhk_news",
        "name": "NHK NEWS WEB (ニュース)",
        "domain": "News",
        "urls": ["https://www3.nhk.or.jp/news/cat01.html"],
    },
]

def evaluate_site(site):
    print(f"\n{'='*60}")
    print(f"Evaluating: {site['name']} ({site['domain']})")
    print(f"{'='*60}")

    start = time.time()
    try:
        resp = requests.post(API, json={"urls": site["urls"]}, timeout=TIMEOUT)
        elapsed = time.time() - start
        data = resp.json()
    except Exception as e:
        elapsed = time.time() - start
        print(f"  ERROR: {e} ({elapsed:.1f}s)")
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
        result["error"] = data.get("message", data.get("error", "unknown"))
        result["reason"] = data.get("reason", "")
        print(f"  Error: {result['error']}")
        outpath = os.path.join(os.path.dirname(__file__), "results", f"{site['id']}_wantlist.json")
        with open(outpath, "w") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        return result

    mappings = data.get("mappings", {})
    confidences = []
    result["fields"] = {}
    for fname, fdata in mappings.items():
        conf = fdata.get("confidence", 0)
        confidences.append(conf)
        result["fields"][fname] = {
            "xpath": fdata.get("xpath", ""),
            "confidence": conf,
            "samples": fdata.get("samples", [])[:3],
            "warning": fdata.get("warning", None),
        }

    result["fields_count"] = len(mappings)
    result["avg_confidence"] = round(sum(confidences) / len(confidences), 3) if confidences else 0
    result["perfect_fields"] = sum(1 for c in confidences if c == 1.0)
    result["tokens_used"] = data.get("tokens_used", 0)

    print(f"  Fields: {len(mappings)} | Avg confidence: {result['avg_confidence']:.0%} | Perfect: {result['perfect_fields']}/{len(mappings)} | Time: {elapsed:.1f}s")
    for fname, fdata in result["fields"].items():
        status = "✓" if fdata["confidence"] == 1.0 else f"{fdata['confidence']:.0%}"
        warn = " ⚠" if fdata.get("warning") else ""
        samples = [s[:40] if s else "(miss)" for s in fdata["samples"][:2]]
        print(f"    {fname}: {status}{warn}  {samples}")

    outpath = os.path.join(os.path.dirname(__file__), "results", f"{site['id']}_wantlist.json")
    with open(outpath, "w") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print(f"  Saved: {outpath}")
    return result

def main():
    results = []
    for site in SITES:
        results.append(evaluate_site(site))
        time.sleep(2)

    print(f"\n{'='*60}")
    print("CROSS-DOMAIN ROUND 2 SUMMARY")
    print(f"{'='*60}")
    for r in results:
        if "error" in r and r.get("status") != "ok":
            print(f"  {r['site']}: ❌ {r.get('error','')[:60]}")
        else:
            print(f"  {r['site']}: {r.get('avg_confidence',0):.0%} hit rate, {r.get('fields_count',0)} fields ({r.get('perfect_fields',0)} perfect), {r.get('elapsed_sec',0):.0f}s")

if __name__ == "__main__":
    main()
