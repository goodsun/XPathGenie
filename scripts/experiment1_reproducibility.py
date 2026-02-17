#!/usr/bin/env python3 -u
"""
実験1: Reproducibility Test - 全23サイトをWant Listモードで3回ずつ実行し、
各サイトのhit rateのmean±stdを計算する。

結果は ~/tools/XPathGenie/docs/evaluation/reproducibility_report.md に保存。
"""

import os
import sys
import json
import time
import statistics
import traceback
from pathlib import Path

# Add XPathGenie path for imports
sys.path.insert(0, '/home/ec2-user/tools/XPathGenie')

# Import evaluate_site function directly
from scripts.evaluate_site import evaluate_site

SITES = [
    "#1 tsukui-staff",
    "#2 selva-i",
    "#4 yakumatch",
    "#5 mynavi",
    "#6 phget",
    "#8 apuro",
    "#9 oshigoto-lab",
    "#10 yakuzaishisyusyoku",
    "#12 bestcareer",
    "#13 pharmapremium",
    "#14 caresta",
    "#16 pharmalink",
    "#18 nikken-care",
    "#19 nikken-nurse",
    "#20 cocofump",
    "#21 MRT-nurse",
    "#24 kaigo-work",
    "#25 w-medical-9",
    "#26 firstnavi",
    "#30 mc-pharma",
    "#31 ph-10",
    "#32 yakusta",
    "#35 kaigokango",
]

RESULTS_DIR = Path.home() / "tools" / "XPathGenie" / "docs" / "evaluation" / "results"
REPORT_PATH = Path.home() / "tools" / "XPathGenie" / "docs" / "evaluation" / "reproducibility_report.md"

def main():
    print("=== 実験1: Reproducibility Test ===")
    print(f"全{len(SITES)}サイトをWant Listモードで3回ずつ実行します")
    print(f"結果保存先: {RESULTS_DIR}")
    
    # Ensure results directory exists
    os.makedirs(RESULTS_DIR, exist_ok=True)
    
    # Track results for each site
    site_results = {}
    total_runs = 0
    failed_runs = 0
    
    for site_idx, site in enumerate(SITES, 1):
        print(f"\n{'='*60}")
        print(f"サイト {site_idx}/{len(SITES)}: {site}")
        print(f"{'='*60}")
        
        site_hit_rates = []
        
        for run in range(1, 4):  # 3 runs
            print(f"\n--- Run {run}/3 ---")
            
            try:
                # Call evaluate_site directly
                summary = evaluate_site(site, mode="wantlist")
                total_runs += 1
                
                if summary and 'avg_hit_rate' in summary:
                    hit_rate = summary['avg_hit_rate']
                    site_hit_rates.append(hit_rate)
                    print(f"Run {run} hit rate: {hit_rate:.3f}")
                    
                    # Save individual result with run number
                    safe_name = site.replace("#", "").replace(" ", "_").replace("-", "_")
                    result_file = RESULTS_DIR / f"{safe_name}_wantlist_run{run}.json"
                    with open(result_file, 'w', encoding='utf-8') as f:
                        json.dump(summary, f, indent=2, ensure_ascii=False)
                    print(f"Saved: {result_file}")
                    
                else:
                    print(f"Run {run} failed - no summary returned")
                    failed_runs += 1
                    
            except Exception as e:
                print(f"Run {run} failed with error: {e}")
                print(traceback.format_exc())
                failed_runs += 1
            
            # Rate limiting - wait 5 seconds between runs
            if run < 3:  # Don't wait after the last run
                print("Waiting 5s for rate limiting...")
                time.sleep(5)
        
        # Calculate stats for this site
        if site_hit_rates:
            mean_hit_rate = statistics.mean(site_hit_rates)
            std_hit_rate = statistics.stdev(site_hit_rates) if len(site_hit_rates) > 1 else 0.0
            
            site_results[site] = {
                'hit_rates': site_hit_rates,
                'mean': mean_hit_rate,
                'std': std_hit_rate,
                'runs_completed': len(site_hit_rates)
            }
            
            print(f"\nサイト {site} 統計:")
            print(f"  Hit rates: {[f'{hr:.3f}' for hr in site_hit_rates]}")
            print(f"  Mean±Std: {mean_hit_rate:.3f}±{std_hit_rate:.3f}")
        else:
            site_results[site] = {
                'hit_rates': [],
                'mean': 0.0,
                'std': 0.0,
                'runs_completed': 0
            }
            print(f"\nサイト {site}: 全実行が失敗")
        
        # Rate limiting between sites
        if site_idx < len(SITES):
            print("Waiting 5s before next site...")
            time.sleep(5)
    
    # Generate summary report
    print(f"\n{'='*60}")
    print("実験1完了 - サマリレポート生成中...")
    print(f"{'='*60}")
    
    generate_report(site_results, total_runs, failed_runs)
    
    print(f"レポート保存先: {REPORT_PATH}")
    print("実験1完了！")

def generate_report(site_results, total_runs, failed_runs):
    """Generate markdown report with statistics."""
    
    # Calculate overall statistics
    successful_sites = [s for s in site_results.values() if s['runs_completed'] > 0]
    overall_means = [s['mean'] for s in successful_sites]
    overall_stds = [s['std'] for s in successful_sites]
    
    overall_mean = statistics.mean(overall_means) if overall_means else 0.0
    avg_std = statistics.mean(overall_stds) if overall_stds else 0.0
    
    # Start building report
    report_lines = [
        "# XPathGenie 実験1: Reproducibility Test",
        "",
        f"実行日時: {time.strftime('%Y-%m-%d %H:%M:%S UTC')}",
        "",
        "## 概要",
        "",
        f"全{len(SITES)}サイトをWant Listモードで3回ずつ実行し、hit rateの再現性を測定。",
        "",
        "## 実行統計",
        "",
        f"- 総実行数: {total_runs}",
        f"- 失敗数: {failed_runs}",
        f"- 成功率: {(total_runs-failed_runs)/total_runs*100:.1f}%" if total_runs > 0 else "- 成功率: N/A",
        f"- 成功サイト数: {len(successful_sites)}/{len(SITES)}",
        "",
        "## 全体統計",
        "",
        f"- Hit rate平均: {overall_mean:.3f}",
        f"- 標準偏差平均: {avg_std:.3f}",
        "",
        "## サイト別統計",
        "",
        "| サイト | Run1 | Run2 | Run3 | Mean | Std | 完了数 |",
        "|--------|------|------|------|------|-----|--------|"
    ]
    
    # Add table rows
    for site, stats in site_results.items():
        hit_rates = stats['hit_rates']
        mean = stats['mean']
        std = stats['std']
        completed = stats['runs_completed']
        
        # Format hit rates with padding for missing runs
        hr1 = f"{hit_rates[0]:.3f}" if len(hit_rates) > 0 else "---"
        hr2 = f"{hit_rates[1]:.3f}" if len(hit_rates) > 1 else "---"
        hr3 = f"{hit_rates[2]:.3f}" if len(hit_rates) > 2 else "---"
        
        mean_str = f"{mean:.3f}" if completed > 0 else "---"
        std_str = f"{std:.3f}" if completed > 1 else "---"
        
        report_lines.append(f"| {site} | {hr1} | {hr2} | {hr3} | {mean_str} | {std_str} | {completed}/3 |")
    
    # Add analysis section
    report_lines.extend([
        "",
        "## 分析",
        "",
        "### 再現性の評価",
        "",
    ])
    
    # Analyze reproducibility
    stable_sites = [s for s in successful_sites if s['std'] < 0.05]  # std < 5%
    variable_sites = [s for s in successful_sites if s['std'] >= 0.1]  # std >= 10%
    
    report_lines.extend([
        f"- 安定サイト (std < 0.05): {len(stable_sites)}サイト",
        f"- 変動大サイト (std >= 0.10): {len(variable_sites)}サイト",
        "",
    ])
    
    if variable_sites:
        report_lines.extend([
            "### 変動が大きいサイト",
            "",
        ])
        for site, stats in site_results.items():
            if stats in variable_sites:
                report_lines.append(f"- {site}: std={stats['std']:.3f}")
        report_lines.append("")
    
    # Write report
    with open(REPORT_PATH, 'w', encoding='utf-8') as f:
        f.write('\n'.join(report_lines))

if __name__ == "__main__":
    main()