#!/usr/bin/env python3
"""SWDE-style evaluation for XPathGenie.

Since the original SWDE dataset is difficult to obtain, this creates a 
SWDE-style benchmark using publicly available websites that match the 
SWDE verticals and attribute categories.

SWDE Verticals (original):
- Auto: model, price, engine, fuel_economy
- Book: title, author, isbn_13, publisher, publication_date  
- Camera: model, price, manufacturer
- Job: title, company, location, date_posted
- Movie: title, director, genre, mpaa_rating
- NBA Player: name, team, height, weight
- Restaurant: name, address, phone, cuisine
- University: name, phone, website, type
"""

import json
import requests
import time
import sys
import os
from datetime import datetime
import logging
from typing import Dict, List, Any
from lxml import html, etree

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.expanduser('~/tools/XPathGenie/docs/evaluation/swde_eval.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

API_BASE = "http://127.0.0.1:8789/api/analyze"
TIMEOUT = 180  # 3 minutes per site

# SWDE-style test sites - publicly available sites matching SWDE categories
SWDE_SITES = [
    {
        "vertical": "auto",
        "site_id": "cars_com", 
        "name": "Cars.com",
        "urls": [
            "https://www.cars.com/shopping/results/?stock_type=used&makes%5B%5D=toyota&models%5B%5D=toyota-camry&list_price_max=&maximum_distance=20&zip=10001"
        ],
        "expected_fields": ["model", "price", "year", "mileage"],
        "description": "Used car listings"
    },
    {
        "vertical": "book",
        "site_id": "goodreads",
        "name": "Goodreads", 
        "urls": [
            "https://www.goodreads.com/book/show/2767052-the-hunger-games"
        ],
        "expected_fields": ["title", "author", "rating", "genre"],
        "description": "Book information page"
    },
    {
        "vertical": "camera", 
        "site_id": "bhphoto",
        "name": "B&H Photo",
        "urls": [
            "https://www.bhphotovideo.com/c/products/Digital-Cameras/ci/9811/N/4288586282"
        ],
        "expected_fields": ["model", "price", "manufacturer", "features"],
        "description": "Camera product listings"
    },
    {
        "vertical": "job",
        "site_id": "indeed", 
        "name": "Indeed",
        "urls": [
            "https://www.indeed.com/jobs?q=software+engineer&l=San+Francisco%2C+CA"
        ],
        "expected_fields": ["title", "company", "location", "salary"],
        "description": "Job search results"
    },
    {
        "vertical": "movie",
        "site_id": "imdb",
        "name": "IMDb", 
        "urls": [
            "https://www.imdb.com/title/tt0111161/"  # The Shawshank Redemption
        ],
        "expected_fields": ["title", "director", "genre", "rating"],
        "description": "Movie information page"
    },
    {
        "vertical": "restaurant",
        "site_id": "yelp",
        "name": "Yelp",
        "urls": [
            "https://www.yelp.com/biz/lombards-seafood-grille-seattle"
        ], 
        "expected_fields": ["name", "address", "phone", "cuisine"],
        "description": "Restaurant page"
    },
    {
        "vertical": "university",
        "site_id": "harvard",
        "name": "Harvard University",
        "urls": [
            "https://www.harvard.edu/"
        ],
        "expected_fields": ["name", "location", "website", "type"], 
        "description": "University homepage"
    }
]

class SWDEEvaluator:
    def __init__(self, output_dir: str = None):
        self.output_dir = output_dir or os.path.join(
            os.path.dirname(__file__), "results"
        )
        os.makedirs(self.output_dir, exist_ok=True)
        
    def evaluate_site(self, site: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate a single site via XPathGenie API."""
        logger.info(f"\n{'='*60}")
        logger.info(f"Evaluating: {site['name']} ({site['vertical']})")
        logger.info(f"URLs: {site['urls']}")
        logger.info(f"Expected fields: {site['expected_fields']}")
        logger.info(f"{'='*60}")

        payload = {"urls": site["urls"]}
        
        start_time = time.time()
        try:
            response = requests.post(API_BASE, json=payload, timeout=TIMEOUT)
            elapsed = time.time() - start_time
            data = response.json()
        except Exception as e:
            elapsed = time.time() - start_time
            error_msg = f"API request failed: {e}"
            logger.error(f"  {error_msg} (after {elapsed:.1f}s)")
            return {
                "site_id": site["site_id"],
                "vertical": site["vertical"], 
                "name": site["name"],
                "error": str(e),
                "elapsed_sec": round(elapsed, 1),
                "timestamp": datetime.now().isoformat()
            }

        result = {
            "site_id": site["site_id"],
            "vertical": site["vertical"],
            "name": site["name"], 
            "urls": site["urls"],
            "expected_fields": site["expected_fields"],
            "elapsed_sec": round(elapsed, 1),
            "status": data.get("status", "unknown"),
            "timestamp": datetime.now().isoformat()
        }

        if data.get("status") != "ok":
            result["error"] = data.get("message", data.get("error", "unknown error"))
            result["reason"] = data.get("reason", "")
            logger.error(f"  API Error: {result['error']}")
            logger.error(f"  Reason: {result.get('reason', '')}")
            return result

        # Process successful response
        mappings = data.get("mappings", {})
        result["fields_count"] = len(mappings)
        result["pages_analyzed"] = data.get("pages_analyzed", 0)
        result["tokens_used"] = data.get("tokens_used", 0)
        result["refined_fields"] = data.get("refined_fields", [])

        # Calculate metrics
        confidences = []
        result["fields"] = {}
        result["discovered_fields"] = list(mappings.keys())
        
        for field_name, field_data in mappings.items():
            confidence = field_data.get("confidence", 0)
            confidences.append(confidence)
            result["fields"][field_name] = {
                "xpath": field_data.get("xpath", ""),
                "confidence": confidence,
                "samples": field_data.get("samples", [])[:3],
                "optional": field_data.get("optional", False),
                "warning": field_data.get("warning", None)
            }

        result["avg_confidence"] = round(sum(confidences) / len(confidences), 3) if confidences else 0
        result["perfect_fields"] = sum(1 for c in confidences if c == 1.0)
        
        # Field coverage analysis
        expected_set = set(site["expected_fields"])
        discovered_set = set(mappings.keys())
        
        result["field_coverage"] = {
            "expected": list(expected_set),
            "discovered": list(discovered_set),
            "matched": list(expected_set.intersection(discovered_set)),
            "missing": list(expected_set - discovered_set),
            "extra": list(discovered_set - expected_set)
        }
        
        coverage_ratio = len(result["field_coverage"]["matched"]) / len(expected_set) if expected_set else 0
        result["coverage_score"] = round(coverage_ratio, 3)

        # Log results
        logger.info(f"  Status: {data['status']}")
        logger.info(f"  Fields discovered: {len(mappings)}")
        logger.info(f"  Expected fields: {len(site['expected_fields'])}")
        logger.info(f"  Field coverage: {result['coverage_score']:.1%}")
        logger.info(f"  Avg confidence: {result['avg_confidence']:.1%}")
        logger.info(f"  Perfect fields: {result['perfect_fields']}/{len(mappings)}")
        logger.info(f"  Time: {elapsed:.1f}s")
        logger.info(f"  Tokens: {result['tokens_used']}")

        # Log field details
        for field_name, field_data in result["fields"].items():
            status = "✓" if field_data["confidence"] == 1.0 else f"{field_data['confidence']:.0%}"
            expected = "📌" if field_name in expected_set else ""
            warning = " ⚠" if field_data.get("warning") else ""
            samples = [s[:40] if s else "(miss)" for s in field_data["samples"][:2]]
            logger.info(f"    {field_name}: {status}{expected}{warning}  {samples}")

        return result

    def run_evaluation(self, site_filter: str = None) -> Dict[str, Any]:
        """Run evaluation on all sites or filtered sites."""
        logger.info("Starting SWDE-style evaluation for XPathGenie")
        logger.info(f"Total sites: {len(SWDE_SITES)}")
        if site_filter:
            logger.info(f"Filter: {site_filter}")

        results = []
        for site in SWDE_SITES:
            if site_filter and site_filter not in site["site_id"]:
                continue
                
            result = self.evaluate_site(site)
            results.append(result)
            
            # Save individual result
            output_file = os.path.join(
                self.output_dir, 
                f"swde_{site['vertical']}_{site['site_id']}.json"
            )
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            logger.info(f"  Saved: {output_file}")
            
            # Brief pause between sites
            time.sleep(2)

        # Calculate overall metrics
        summary = self.calculate_summary(results)
        
        # Save complete results
        complete_results = {
            "evaluation_type": "SWDE-style",
            "timestamp": datetime.now().isoformat(),
            "summary": summary,
            "individual_results": results
        }
        
        results_file = os.path.join(self.output_dir, "swde_results.json")
        with open(results_file, "w", encoding="utf-8") as f:
            json.dump(complete_results, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Complete results saved: {results_file}")
        return complete_results

    def calculate_summary(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate summary metrics across all results."""
        successful = [r for r in results if r.get("status") == "ok"]
        failed = [r for r in results if r.get("status") != "ok"]
        
        if not successful:
            return {
                "total_sites": len(results),
                "successful_sites": 0,
                "failed_sites": len(failed),
                "overall_success_rate": 0.0
            }

        # Overall metrics
        total_fields = sum(r.get("fields_count", 0) for r in successful)
        total_perfect = sum(r.get("perfect_fields", 0) for r in successful)
        
        avg_confidence = sum(r.get("avg_confidence", 0) for r in successful) / len(successful)
        avg_coverage = sum(r.get("coverage_score", 0) for r in successful) / len(successful)
        
        # Per-vertical breakdown
        vertical_stats = {}
        for result in successful:
            vertical = result.get("vertical")
            if vertical not in vertical_stats:
                vertical_stats[vertical] = {
                    "sites": 0,
                    "total_fields": 0,
                    "perfect_fields": 0,
                    "confidence_sum": 0,
                    "coverage_sum": 0
                }
            
            stats = vertical_stats[vertical]
            stats["sites"] += 1
            stats["total_fields"] += result.get("fields_count", 0)
            stats["perfect_fields"] += result.get("perfect_fields", 0)
            stats["confidence_sum"] += result.get("avg_confidence", 0)
            stats["coverage_sum"] += result.get("coverage_score", 0)
        
        # Calculate vertical averages
        for vertical, stats in vertical_stats.items():
            if stats["sites"] > 0:
                stats["avg_confidence"] = stats["confidence_sum"] / stats["sites"]
                stats["avg_coverage"] = stats["coverage_sum"] / stats["sites"]
                stats["fields_per_site"] = stats["total_fields"] / stats["sites"]
            del stats["confidence_sum"]
            del stats["coverage_sum"]

        summary = {
            "total_sites": len(results),
            "successful_sites": len(successful),
            "failed_sites": len(failed),
            "overall_success_rate": len(successful) / len(results),
            
            "field_metrics": {
                "total_fields_discovered": total_fields,
                "total_perfect_fields": total_perfect,
                "avg_fields_per_site": total_fields / len(successful) if successful else 0,
                "perfect_field_ratio": total_perfect / total_fields if total_fields > 0 else 0
            },
            
            "performance_metrics": {
                "macro_avg_confidence": round(avg_confidence, 3),
                "macro_avg_coverage": round(avg_coverage, 3),
                "combined_f1_score": round(2 * avg_confidence * avg_coverage / (avg_confidence + avg_coverage), 3) if (avg_confidence + avg_coverage) > 0 else 0
            },
            
            "vertical_breakdown": vertical_stats,
            
            "comparison_with_axe": {
                "axe_f1_score": 0.881,  # AXE's reported F1 score on SWDE
                "xpathgenie_f1_score": round(2 * avg_confidence * avg_coverage / (avg_confidence + avg_coverage), 3) if (avg_confidence + avg_coverage) > 0 else 0,
                "note": "XPathGenie is zero-shot, AXE is supervised learning"
            }
        }
        
        logger.info("\n" + "="*60)
        logger.info("SWDE-STYLE EVALUATION SUMMARY")
        logger.info("="*60)
        logger.info(f"Success rate: {summary['overall_success_rate']:.1%} ({len(successful)}/{len(results)})")
        logger.info(f"Macro avg confidence: {summary['performance_metrics']['macro_avg_confidence']:.1%}")
        logger.info(f"Macro avg coverage: {summary['performance_metrics']['macro_avg_coverage']:.1%}")
        logger.info(f"Combined F1 score: {summary['performance_metrics']['combined_f1_score']:.1%}")
        logger.info(f"Total fields discovered: {summary['field_metrics']['total_fields_discovered']}")
        logger.info(f"Perfect fields: {summary['field_metrics']['total_perfect_fields']}")
        logger.info("\nPer-vertical results:")
        for vertical, stats in vertical_stats.items():
            logger.info(f"  {vertical}: {stats['avg_confidence']:.1%} conf, {stats['avg_coverage']:.1%} cov, {stats['fields_per_site']:.1f} fields/site")
        
        return summary


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Run SWDE-style evaluation for XPathGenie")
    parser.add_argument("--site", help="Filter to specific site ID")
    parser.add_argument("--output-dir", help="Output directory for results")
    args = parser.parse_args()
    
    evaluator = SWDEEvaluator(args.output_dir)
    results = evaluator.run_evaluation(args.site)
    
    print("\n" + "="*60)
    print("EVALUATION COMPLETE")
    print("="*60)
    print(f"Results saved to: {evaluator.output_dir}")
    print(f"Combined F1 Score: {results['summary']['performance_metrics']['combined_f1_score']:.1%}")
    print(f"vs AXE F1 Score: {results['summary']['comparison_with_axe']['axe_f1_score']:.1%}")


if __name__ == "__main__":
    main()