#!/usr/bin/env python3 -u
"""
実験2: Ablation Study - 代表5サイトで以下の4条件を比較:
- Full pipeline (通常)
- w/o compression (生HTML8000文字切り出しでそのまま渡す)
- w/o refinement (refineステップをスキップ)
- w/o normalize-space (プロンプトのnormalize-space指示をtext()=に置換)

結果は ~/tools/XPathGenie/docs/evaluation/ablation_report.md に保存。
"""

import os
import sys
import json
import time
import re
import traceback
from pathlib import Path
from lxml import html as lxml_html
import requests

# Add XPathGenie path for imports
sys.path.insert(0, '/home/ec2-user/tools/XPathGenie')

# Import genie modules directly
from genie.fetcher import fetch_all
from genie.compressor import compress
from genie.analyzer import analyze, refine
from genie.validator import validate, find_multi_matches, narrow_by_first_match

# Import URL loading from evaluate_site
from scripts.evaluate_site import load_urls, fetch_html, eval_xpath

# Ablation target sites
TARGET_SITES = [
    "#1 tsukui-staff",
    "#5 mynavi", 
    "#14 caresta",
    "#25 w-medical-9",
    "#21 MRT-nurse"
]

# Default WantList (same as evaluate_site.py)
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

RESULTS_DIR = Path.home() / "tools" / "XPathGenie" / "docs" / "evaluation" / "results"
REPORT_PATH = Path.home() / "tools" / "XPathGenie" / "docs" / "evaluation" / "ablation_report.md"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

def run_full_pipeline(site_key):
    """Run the full normal pipeline (baseline)."""
    print(f"  [Full] Running full pipeline for {site_key}")
    
    # Load URLs
    urls = load_urls(site_key)
    if not urls:
        return None
        
    # Fetch HTMLs
    pages = []
    for url in urls:
        result = fetch_all([url])
        if result and result[0].get('html'):
            pages.append(result[0])
        time.sleep(0.5)
    
    if not pages:
        return None
    
    # Compress HTMLs
    compressed_htmls = []
    for page in pages:
        compressed = compress(page['html'])
        compressed_htmls.append(compressed)
    
    # Analyze with wantlist
    mappings = analyze(compressed_htmls, wantlist=DEFAULT_WANTLIST)
    
    # Find multi matches and refine
    multi_matches = find_multi_matches(mappings, pages)
    refined = refine(multi_matches) if multi_matches else {}
    
    # Apply refinements
    final_mappings = {**mappings, **refined}
    
    # Narrow by first match if still multiple
    narrowed = narrow_by_first_match(final_mappings, multi_matches, pages)
    final_mappings = {**final_mappings, **narrowed}
    
    # Validate
    validation = validate(final_mappings, pages)
    
    return {
        'mappings': final_mappings,
        'validation': validation,
        'pages_count': len(pages),
        'fields_count': len(final_mappings)
    }

def run_no_compression(site_key):
    """Run without compression - use raw HTML first 8000 chars."""
    print(f"  [No Compress] Running w/o compression for {site_key}")
    
    # Load URLs
    urls = load_urls(site_key)
    if not urls:
        return None
        
    # Fetch HTMLs
    pages = []
    for url in urls:
        result = fetch_all([url])
        if result and result[0].get('html'):
            pages.append(result[0])
        time.sleep(0.5)
    
    if not pages:
        return None
    
    # Use raw HTML first 8000 chars instead of compression
    raw_htmls = []
    for page in pages:
        raw_html = page['html'][:8000]  # First 8000 chars
        raw_htmls.append(raw_html)
    
    # Analyze with wantlist using raw HTML
    mappings = analyze(raw_htmls, wantlist=DEFAULT_WANTLIST)
    
    # Find multi matches and refine (same as full pipeline)
    multi_matches = find_multi_matches(mappings, pages)
    refined = refine(multi_matches) if multi_matches else {}
    
    # Apply refinements
    final_mappings = {**mappings, **refined}
    
    # Narrow by first match if still multiple
    narrowed = narrow_by_first_match(final_mappings, multi_matches, pages)
    final_mappings = {**final_mappings, **narrowed}
    
    # Validate
    validation = validate(final_mappings, pages)
    
    return {
        'mappings': final_mappings,
        'validation': validation,
        'pages_count': len(pages),
        'fields_count': len(final_mappings)
    }

def run_no_refinement(site_key):
    """Run without refinement steps."""
    print(f"  [No Refine] Running w/o refinement for {site_key}")
    
    # Load URLs
    urls = load_urls(site_key)
    if not urls:
        return None
        
    # Fetch HTMLs
    pages = []
    for url in urls:
        result = fetch_all([url])
        if result and result[0].get('html'):
            pages.append(result[0])
        time.sleep(0.5)
    
    if not pages:
        return None
    
    # Compress HTMLs
    compressed_htmls = []
    for page in pages:
        compressed = compress(page['html'])
        compressed_htmls.append(compressed)
    
    # Analyze with wantlist
    mappings = analyze(compressed_htmls, wantlist=DEFAULT_WANTLIST)
    
    # Skip refinement steps completely
    # No multi_matches, no refine(), no narrow_by_first_match()
    
    # Validate with original mappings
    validation = validate(mappings, pages)
    
    return {
        'mappings': mappings,
        'validation': validation,
        'pages_count': len(pages),
        'fields_count': len(mappings)
    }

def run_no_normalize_space(site_key):
    """Run without normalize-space() in prompts - monkey patch to use text()= instead."""
    print(f"  [No Normalize] Running w/o normalize-space for {site_key}")
    
    # Load URLs
    urls = load_urls(site_key)
    if not urls:
        return None
        
    # Fetch HTMLs
    pages = []
    for url in urls:
        result = fetch_all([url])
        if result and result[0].get('html'):
            pages.append(result[0])
        time.sleep(0.5)
    
    if not pages:
        return None
    
    # Compress HTMLs
    compressed_htmls = []
    for page in pages:
        compressed = compress(page['html'])
        compressed_htmls.append(compressed)
    
    # Monkey patch the analyzer module to replace normalize-space with text()
    import genie.analyzer as analyzer_module
    
    # Store original prompts
    original_wantlist_prompt = analyzer_module.PROMPT_WANTLIST
    original_discover_prompt = analyzer_module.PROMPT_DISCOVER
    
    # Create modified prompts
    modified_wantlist = original_wantlist_prompt.replace('normalize-space()=', 'text()=')
    modified_discover = original_discover_prompt.replace('normalize-space()=', 'text()=')
    
    try:
        # Apply monkey patch
        analyzer_module.PROMPT_WANTLIST = modified_wantlist
        analyzer_module.PROMPT_DISCOVER = modified_discover
        
        # Analyze with modified prompts
        mappings = analyze(compressed_htmls, wantlist=DEFAULT_WANTLIST)
        
    finally:
        # Restore original prompts
        analyzer_module.PROMPT_WANTLIST = original_wantlist_prompt
        analyzer_module.PROMPT_DISCOVER = original_discover_prompt
    
    # Find multi matches and refine (same as full pipeline)
    multi_matches = find_multi_matches(mappings, pages)
    refined = refine(multi_matches) if multi_matches else {}
    
    # Apply refinements
    final_mappings = {**mappings, **refined}
    
    # Narrow by first match if still multiple
    narrowed = narrow_by_first_match(final_mappings, multi_matches, pages)
    final_mappings = {**final_mappings, **narrowed}
    
    # Validate
    validation = validate(final_mappings, pages)
    
    return {
        'mappings': final_mappings,
        'validation': validation,
        'pages_count': len(pages),
        'fields_count': len(final_mappings)
    }

def calculate_hit_rate(result):
    """Calculate average hit rate from validation results."""
    if not result or not result.get('validation'):
        return 0.0
        
    validation = result['validation']
    if not validation:
        return 0.0
        
    hit_rates = []
    for field_info in validation.values():
        confidence = field_info.get('confidence', 0.0)
        hit_rates.append(confidence)
    
    return sum(hit_rates) / len(hit_rates) if hit_rates else 0.0

def main():
    print("=== 実験2: Ablation Study ===")
    print(f"代表{len(TARGET_SITES)}サイトで4条件を比較します")
    print(f"条件: Full, w/o compression, w/o refinement, w/o normalize-space")
    
    # Ensure results directory exists
    os.makedirs(RESULTS_DIR, exist_ok=True)
    
    # Track results
    ablation_results = {}
    
    conditions = [
        ('Full', run_full_pipeline),
        ('w/o compression', run_no_compression),
        ('w/o refinement', run_no_refinement),
        ('w/o normalize-space', run_no_normalize_space)
    ]
    
    for site_idx, site in enumerate(TARGET_SITES, 1):
        print(f"\n{'='*60}")
        print(f"サイト {site_idx}/{len(TARGET_SITES)}: {site}")
        print(f"{'='*60}")
        
        site_results = {}
        
        for condition_name, condition_func in conditions:
            print(f"\n--- {condition_name} ---")
            
            try:
                result = condition_func(site)
                if result:
                    hit_rate = calculate_hit_rate(result)
                    site_results[condition_name] = {
                        'hit_rate': hit_rate,
                        'fields_count': result['fields_count'],
                        'pages_count': result['pages_count']
                    }
                    print(f"  {condition_name}: hit_rate={hit_rate:.3f}, fields={result['fields_count']}")
                else:
                    site_results[condition_name] = {
                        'hit_rate': 0.0,
                        'fields_count': 0,
                        'pages_count': 0
                    }
                    print(f"  {condition_name}: FAILED")
                    
            except Exception as e:
                print(f"  {condition_name}: ERROR - {e}")
                print(traceback.format_exc())
                site_results[condition_name] = {
                    'hit_rate': 0.0,
                    'fields_count': 0,
                    'pages_count': 0
                }
            
            # Rate limiting between conditions
            print("Waiting 5s for rate limiting...")
            time.sleep(5)
        
        ablation_results[site] = site_results
        
        # Show site summary
        print(f"\nサイト {site} 結果:")
        for cond, res in site_results.items():
            print(f"  {cond:20}: {res['hit_rate']:.3f}")
    
    # Generate report
    print(f"\n{'='*60}")
    print("実験2完了 - サマリレポート生成中...")
    print(f"{'='*60}")
    
    generate_ablation_report(ablation_results)
    
    print(f"レポート保存先: {REPORT_PATH}")
    print("実験2完了！")

def generate_ablation_report(ablation_results):
    """Generate markdown report for ablation study."""
    
    conditions = ['Full', 'w/o compression', 'w/o refinement', 'w/o normalize-space']
    
    # Start building report
    report_lines = [
        "# XPathGenie 実験2: Ablation Study",
        "",
        f"実行日時: {time.strftime('%Y-%m-%d %H:%M:%S UTC')}",
        "",
        "## 概要",
        "",
        f"代表{len(TARGET_SITES)}サイトで4つの条件を比較し、各コンポーネントの影響を測定。",
        "",
        "### 条件",
        "",
        "1. **Full**: 通常のフルパイプライン",
        "2. **w/o compression**: 生HTML8000文字切り出しでそのまま渡す",
        "3. **w/o refinement**: refineステップをスキップ",
        "4. **w/o normalize-space**: プロンプトのnormalize-space指示をtext()=に置換",
        "",
        "## 結果",
        "",
        "### Hit Rate比較",
        "",
        "| サイト | Full | w/o compression | w/o refinement | w/o normalize-space |",
        "|--------|------|----------------|----------------|---------------------|"
    ]
    
    # Add table rows
    for site, results in ablation_results.items():
        row = f"| {site} |"
        for condition in conditions:
            hit_rate = results.get(condition, {}).get('hit_rate', 0.0)
            row += f" {hit_rate:.3f} |"
        report_lines.append(row)
    
    # Calculate averages
    report_lines.extend([
        "",
        "### 平均 Hit Rate",
        "",
        "| 条件 | 平均 Hit Rate |",
        "|------|---------------|"
    ])
    
    for condition in conditions:
        hit_rates = [results.get(condition, {}).get('hit_rate', 0.0) 
                    for results in ablation_results.values()]
        avg_hit_rate = sum(hit_rates) / len(hit_rates) if hit_rates else 0.0
        report_lines.append(f"| {condition} | {avg_hit_rate:.3f} |")
    
    # Analysis
    report_lines.extend([
        "",
        "## 分析",
        "",
        "### 各コンポーネントの影響",
        ""
    ])
    
    # Compare to baseline (Full)
    full_rates = [results.get('Full', {}).get('hit_rate', 0.0) 
                  for results in ablation_results.values()]
    full_avg = sum(full_rates) / len(full_rates) if full_rates else 0.0
    
    for condition in conditions[1:]:  # Skip 'Full'
        cond_rates = [results.get(condition, {}).get('hit_rate', 0.0) 
                     for results in ablation_results.values()]
        cond_avg = sum(cond_rates) / len(cond_rates) if cond_rates else 0.0
        
        diff = full_avg - cond_avg
        impact = "正" if diff > 0 else "負" if diff < 0 else "なし"
        
        report_lines.append(f"- **{condition}**: 平均Hit Rate {cond_avg:.3f} (Fullとの差: {diff:+.3f}, 影響: {impact})")
    
    report_lines.extend([
        "",
        "### サイト別詳細",
        ""
    ])
    
    for site, results in ablation_results.items():
        report_lines.extend([
            f"#### {site}",
            ""
        ])
        
        for condition in conditions:
            res = results.get(condition, {})
            hit_rate = res.get('hit_rate', 0.0)
            fields = res.get('fields_count', 0)
            pages = res.get('pages_count', 0)
            report_lines.append(f"- {condition}: hit_rate={hit_rate:.3f}, fields={fields}, pages={pages}")
        
        report_lines.append("")
    
    # Write report
    with open(REPORT_PATH, 'w', encoding='utf-8') as f:
        f.write('\n'.join(report_lines))

if __name__ == "__main__":
    main()