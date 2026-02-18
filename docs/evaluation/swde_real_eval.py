#!/usr/bin/env python3
"""SWDE Real Dataset Evaluation for XPathGenie.

This evaluation uses the actual SWDE dataset (downloaded HTML files and ground truth)
instead of scraping live websites. It follows the standard SWDE evaluation methodology.

Dataset: W1ndness/SWDE-Dataset
- 8 verticals: job, book, movie, auto, camera, nbaplayer, restaurant, university
- 2-3 sites per vertical (17 sites total)
- Fields per vertical as specified in SWDE benchmark
- 10 pages per site (0000.htm through 0009.htm)
"""

import json
import requests
import time
import sys
import os
from datetime import datetime
import logging
from typing import Dict, List, Any, Tuple
from lxml import etree
import re
from collections import defaultdict

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.expanduser('~/tools/XPathGenie/docs/evaluation/swde_eval_v2.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

API_BASE = "http://127.0.0.1:8789/api/analyze"
HTML_BASE = "http://127.0.0.1:8790"
TIMEOUT = 180  # 3 minutes per site

# SWDE evaluation configuration
SWDE_CONFIG = {
    "job": {
        "sites": ["monster", "dice", "careerbuilder"],
        "fields": ["title", "company", "location", "date_posted"]
    },
    "book": {
        "sites": ["amazon", "borders"],
        "fields": ["title", "author", "isbn_13", "publisher", "publication_date"]
    },
    "movie": {
        "sites": ["imdb", "yahoo"],
        "fields": ["title", "director", "genre", "mpaa_rating"]
    },
    "auto": {
        "sites": ["aol", "msn", "yahoo"],
        "fields": ["model", "price", "engine", "fuel_economy"]
    },
    "camera": {
        "sites": ["amazon", "buy", "beachaudio"],
        "fields": ["model", "manufacturer", "price"]
    },
    "nbaplayer": {
        "sites": ["espn", "yahoo", "wiki"],
        "fields": ["name", "team", "height", "weight"]
    },
    "restaurant": {
        "sites": ["opentable", "urbanspoon", "fodors"],
        "fields": ["name", "address", "phone", "cuisine"]
    },
    "university": {
        "sites": ["collegeboard", "matchcollege", "usnews"],
        "fields": ["name", "phone", "type", "website"]
    }
}

def parse_groundtruth(filepath: str) -> Dict[str, List[str]]:
    """Parse SWDE ground truth file. Returns dict: page_id -> list of values"""
    results = {}
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        # Skip header (line 0) and counts (line 1)
        for line in lines[2:]:
            parts = line.strip().split('\t')
            if len(parts) >= 3:
                page_id = parts[0]  # e.g., "0000"
                num_values = int(parts[1])
                values = parts[2:2+num_values] if num_values > 0 else []
                results[page_id] = values
    except Exception as e:
        logger.error(f"Error parsing ground truth {filepath}: {e}")
        results = {}
    return results

def apply_xpath(html_path: str, xpath_expr: str) -> List[str]:
    """Apply XPath to HTML file and return extracted text values"""
    try:
        with open(html_path, 'rb') as f:
            tree = etree.parse(f, etree.HTMLParser())
        results = tree.xpath(xpath_expr)
        extracted = []
        for r in results:
            if isinstance(r, etree._Element):
                text = r.xpath("string(.)").strip()
            elif isinstance(r, str):
                text = r.strip()
            else:
                text = str(r).strip()
            if text:
                extracted.append(text)
        return extracted
    except Exception as e:
        logger.error(f"Error applying XPath {xpath_expr} to {html_path}: {e}")
        return []

def normalize_text(text: str) -> str:
    """Normalize text for comparison (strip, lowercase, normalize whitespace)"""
    if not text:
        return ""
    # Remove extra whitespace and normalize
    text = re.sub(r'\s+', ' ', text.strip().lower())
    return text

def fuzzy_match(extracted: List[str], ground_truth: List[str]) -> Tuple[int, int, int]:
    """
    Compare extracted values with ground truth using fuzzy matching.
    Returns (true_positives, false_positives, false_negatives)
    """
    if not ground_truth:
        return 0, len(extracted), 0
    
    # Normalize all values
    norm_extracted = [normalize_text(e) for e in extracted]
    norm_gt = [normalize_text(g) for g in ground_truth]
    
    true_positives = 0
    false_positives = 0
    
    # Count matches (handle duplicates by matching each GT value at most once)
    gt_matched = set()
    
    for i, ext_val in enumerate(norm_extracted):
        matched = False
        for j, gt_val in enumerate(norm_gt):
            if j not in gt_matched:
                # Exact match or containment match
                if ext_val == gt_val or gt_val in ext_val or ext_val in gt_val:
                    true_positives += 1
                    gt_matched.add(j)
                    matched = True
                    break
        if not matched:
            false_positives += 1
    
    false_negatives = len(norm_gt) - len(gt_matched)
    
    return true_positives, false_positives, false_negatives

def compute_metrics(tp: int, fp: int, fn: int) -> Dict[str, float]:
    """Compute precision, recall, F1 from true/false positives/negatives"""
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
    
    return {
        "precision": round(precision, 4),
        "recall": round(recall, 4), 
        "f1": round(f1, 4),
        "tp": tp,
        "fp": fp,
        "fn": fn
    }

def run_xpathgenie(urls: List[str], fields: List[str]) -> Dict[str, str]:
    """
    Run XPathGenie on the given URLs with the specified field names.
    Returns mapping of field_name -> xpath_expression
    """
    wantlist = {field: "" for field in fields}
    
    payload = {
        "urls": urls,
        "wantlist": wantlist
    }
    
    try:
        logger.info(f"Calling XPathGenie API with {len(urls)} URLs, fields: {list(fields)}")
        headers = {"Origin": "http://127.0.0.1:8789"}
        response = requests.post(API_BASE, json=payload, timeout=TIMEOUT, headers=headers)
        response.raise_for_status()
        
        result = response.json()
        
        if result.get("status") != "ok":
            logger.error(f"XPathGenie API error: {result}")
            return {}
        
        mappings = result.get("mappings", {})
        logger.info(f"XPathGenie returned {len(mappings)} field mappings")
        
        return mappings
    
    except Exception as e:
        logger.error(f"Error calling XPathGenie API: {e}")
        return {}

def evaluate_site(vertical: str, site: str) -> Dict[str, Any]:
    """Evaluate a single site (vertical-site combination)"""
    logger.info(f"Evaluating {vertical}-{site}")
    
    fields = SWDE_CONFIG[vertical]["fields"]
    
    # Step 1: Run XPathGenie on first 3 pages to generate XPaths
    sample_urls = [f"{HTML_BASE}/{vertical}-{site}/{page:04d}.htm" for page in range(3)]
    
    xpath_mappings = run_xpathgenie(sample_urls, fields)
    
    if not xpath_mappings:
        logger.error(f"No XPath mappings generated for {vertical}-{site}")
        return {"status": "failed", "reason": "no_xpaths"}
    
    logger.info(f"Generated XPaths for {vertical}-{site}: {xpath_mappings}")
    
    # Step 2: Apply XPaths to all 10 pages and compare with ground truth
    results_by_field = {}
    
    for field in fields:
        if field not in xpath_mappings:
            logger.warning(f"No XPath found for field {field}")
            results_by_field[field] = {"status": "no_xpath"}
            continue
            
        xpath_data = xpath_mappings[field]
        
        # Handle XPath data structure (could be string or dict)
        if isinstance(xpath_data, dict):
            xpath = xpath_data.get("xpath", "")
        else:
            xpath = str(xpath_data)
            
        if not xpath:
            logger.warning(f"Empty XPath for field {field}")
            results_by_field[field] = {"status": "empty_xpath"}
            continue
        
        # Load ground truth for this field
        gt_path = f"~/tools/XPathGenie/data/swde/groundtruth/{vertical}-{site}-{field}.txt"
        gt_path = os.path.expanduser(gt_path)
        ground_truth = parse_groundtruth(gt_path)
        
        if not ground_truth:
            logger.error(f"No ground truth data loaded for {vertical}-{site}-{field}")
            results_by_field[field] = {"status": "no_groundtruth"}
            continue
        
        # Apply XPath to all pages and compute metrics
        total_tp, total_fp, total_fn = 0, 0, 0
        page_results = {}
        
        for page in range(10):
            page_id = f"{page:04d}"
            html_path = f"~/tools/XPathGenie/data/swde/html/{vertical}-{site}/{page_id}.htm"
            html_path = os.path.expanduser(html_path)
            
            if not os.path.exists(html_path):
                logger.warning(f"HTML file not found: {html_path}")
                continue
            
            # Extract values using XPath
            extracted = apply_xpath(html_path, xpath)
            
            # Get ground truth for this page
            gt_values = ground_truth.get(page_id, [])
            
            # Compute metrics
            tp, fp, fn = fuzzy_match(extracted, gt_values)
            total_tp += tp
            total_fp += fp
            total_fn += fn
            
            page_results[page_id] = {
                "extracted": extracted,
                "ground_truth": gt_values,
                "metrics": compute_metrics(tp, fp, fn)
            }
        
        # Aggregate metrics for this field
        field_metrics = compute_metrics(total_tp, total_fp, total_fn)
        
        results_by_field[field] = {
            "status": "completed",
            "xpath": xpath,
            "metrics": field_metrics,
            "page_results": page_results
        }
        
        logger.info(f"{vertical}-{site}-{field}: F1={field_metrics['f1']:.4f}")
    
    return {
        "status": "completed",
        "vertical": vertical,
        "site": site,
        "xpath_mappings": xpath_mappings,
        "results_by_field": results_by_field
    }

def main():
    """Run SWDE evaluation on all configured verticals and sites"""
    start_time = datetime.now()
    logger.info("Starting SWDE Real Dataset Evaluation for XPathGenie")
    
    all_results = {}
    
    for vertical in SWDE_CONFIG:
        all_results[vertical] = {}
        
        for site in SWDE_CONFIG[vertical]["sites"]:
            try:
                site_results = evaluate_site(vertical, site)
                all_results[vertical][site] = site_results
                
                # Log summary metrics
                if site_results.get("status") == "completed":
                    field_f1s = []
                    for field, field_data in site_results["results_by_field"].items():
                        if field_data.get("status") == "completed":
                            field_f1s.append(field_data["metrics"]["f1"])
                    
                    if field_f1s:
                        avg_f1 = sum(field_f1s) / len(field_f1s)
                        logger.info(f"{vertical}-{site} average F1: {avg_f1:.4f}")
                
            except Exception as e:
                logger.error(f"Error evaluating {vertical}-{site}: {e}")
                all_results[vertical][site] = {"status": "error", "error": str(e)}
    
    # Save detailed results
    results_path = "~/tools/XPathGenie/docs/evaluation/swde_results_v2.json"
    results_path = os.path.expanduser(results_path)
    
    with open(results_path, 'w') as f:
        json.dump(all_results, f, indent=2)
    
    logger.info(f"Detailed results saved to {results_path}")
    
    # Generate summary report
    generate_summary_report(all_results, start_time)
    
    logger.info("SWDE evaluation completed")

def generate_summary_report(all_results: Dict, start_time: datetime):
    """Generate a summary report in markdown format"""
    summary_path = "~/tools/XPathGenie/docs/evaluation/swde_summary_v2.md"
    summary_path = os.path.expanduser(summary_path)
    
    with open(summary_path, 'w') as f:
        f.write("# SWDE Real Dataset Evaluation Results (v2)\n\n")
        f.write(f"**Evaluation Date**: {start_time.strftime('%Y-%m-%d %H:%M:%S UTC')}\n")
        f.write(f"**Duration**: {(datetime.now() - start_time).total_seconds():.1f} seconds\n\n")
        
        f.write("## Dataset Configuration\n\n")
        f.write("- **Dataset**: SWDE Real Dataset (W1ndness/SWDE-Dataset)\n")
        f.write("- **Verticals**: job, book, movie, auto, camera, nbaplayer, restaurant, university (8 total)\n")
        f.write("- **Sites**: 17 total (2-3 per vertical)\n")
        f.write("- **Pages per site**: 10 (0000.htm - 0009.htm)\n")
        f.write("- **Sample pages for XPath generation**: 3 (first 3 pages)\n\n")
        
        f.write("## Overall Results\n\n")
        
        overall_metrics = defaultdict(list)
        
        # Collect all F1 scores
        for vertical in all_results:
            f.write(f"### {vertical.title()} Vertical\n\n")
            
            vertical_f1s = []
            
            for site in all_results[vertical]:
                site_data = all_results[vertical][site]
                
                if site_data.get("status") != "completed":
                    f.write(f"- **{site}**: {site_data.get('status', 'unknown')} ({site_data.get('error', 'no details')})\n")
                    continue
                
                f.write(f"#### {site}\n\n")
                f.write("| Field | F1 | Precision | Recall | TP | FP | FN |\n")
                f.write("|-------|----|-----------|---------|----|----|----|\\n")
                
                site_f1s = []
                for field, field_data in site_data["results_by_field"].items():
                    if field_data.get("status") == "completed":
                        m = field_data["metrics"]
                        f.write(f"| {field} | {m['f1']:.4f} | {m['precision']:.4f} | {m['recall']:.4f} | {m['tp']} | {m['fp']} | {m['fn']} |\n")
                        site_f1s.append(m['f1'])
                        overall_metrics[field].append(m['f1'])
                    else:
                        f.write(f"| {field} | - | - | - | - | - | - |\n")
                
                if site_f1s:
                    avg_f1 = sum(site_f1s) / len(site_f1s)
                    f.write(f"\n**{site} Average F1**: {avg_f1:.4f}\n\n")
                    vertical_f1s.append(avg_f1)
            
            if vertical_f1s:
                vertical_avg = sum(vertical_f1s) / len(vertical_f1s)
                f.write(f"**{vertical.title()} Vertical Average F1**: {vertical_avg:.4f}\n\n")
        
        # Overall summary
        f.write("## Summary\n\n")
        
        all_f1s = []
        for field_f1s in overall_metrics.values():
            all_f1s.extend(field_f1s)
        
        if all_f1s:
            overall_f1 = sum(all_f1s) / len(all_f1s)
            f.write(f"**Overall F1 Score**: {overall_f1:.4f}\n\n")
            
            # Compare with AXE baseline
            f.write("### Comparison with AXE\n\n")
            f.write("| System | SWDE F1 Score |\n")
            f.write("|--------|---------------|\n")
            f.write(f"| **XPathGenie** | **{overall_f1:.4f}** |\n")
            f.write("| AXE (baseline) | 0.881 |\n\n")
            
            if overall_f1 > 0.881:
                f.write("✅ **XPathGenie outperforms the AXE baseline!**\n\n")
            elif overall_f1 > 0.85:
                f.write("✅ **XPathGenie achieves competitive performance with AXE.**\n\n")
            else:
                f.write("📊 **XPathGenie shows promising results but has room for improvement.**\n\n")
        else:
            f.write("❌ **No valid results obtained.**\n\n")
        
        f.write("## Notes\n\n")
        f.write("- Evaluation uses fuzzy text matching (normalized whitespace, case-insensitive)\n")
        f.write("- XPath generation uses first 3 pages as samples, evaluation on all 10 pages\n")
        f.write("- Ground truth comparison handles multiple values per field correctly\n")
        f.write("- This evaluation uses the actual SWDE dataset HTML files (not live websites)\n")
    
    logger.info(f"Summary report saved to {summary_path}")

if __name__ == "__main__":
    main()