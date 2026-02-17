#!/usr/bin/env python3 -u
"""
再現性テスト — 不足分の追加実行
欠落: #26, #30, #31, #32, #35
異常値: #6 phget (3回とも0%は元の100%と矛盾)
"""

import sys, os, time, json
sys.path.insert(0, '/home/ec2-user/tools/XPathGenie')
from scripts.evaluate_site import evaluate_site

MISSING_SITES = [
    "#6 phget",
    "#26 firstnavi",
    "#30 mc-pharma",
    "#31 ph-10",
    "#32 yakusta",
    "#35 kaigokango"
]

RESULTS_DIR = "/home/ec2-user/tools/XPathGenie/docs/evaluation/results"

def main():
    for site in MISSING_SITES:
        for run in range(1, 4):
            safe = site.strip('#').replace(' ', '_').replace('#', '')
            out_name = f"{safe}_wantlist_run{run}.json"
            out_path = os.path.join(RESULTS_DIR, out_name)
            
            # Skip if already exists and looks valid (>10 fields)
            if os.path.exists(out_path):
                try:
                    with open(out_path) as f:
                        d = json.load(f)
                    if d.get("fields_total", 0) > 5:
                        print(f"[SKIP] {out_name} exists with {d['fields_total']} fields")
                        continue
                    else:
                        print(f"[REDO] {out_name} has only {d.get('fields_total', 0)} fields")
                except:
                    pass
            
            print(f"\n{'='*50}")
            print(f"Running: {site} - Run {run}")
            print(f"{'='*50}")
            
            try:
                result = evaluate_site(site, mode="wantlist")
                if result:
                    # Save with run number
                    with open(out_path, "w") as f:
                        json.dump(result, f, indent=2, ensure_ascii=False)
                    print(f"[OK] Saved: {out_name} (hit_rate={result['avg_hit_rate']:.1%})")
                else:
                    print(f"[FAIL] {site} run {run}")
            except Exception as e:
                print(f"[ERROR] {site} run {run}: {e}")
            
            time.sleep(10)  # Rate limit

    print("\n✅ All missing runs complete!")

if __name__ == "__main__":
    main()
