#!/usr/bin/env python3
import os
import time
import requests
from pathlib import Path

# Base URL for SWDE dataset
BASE_URL = "https://raw.githubusercontent.com/W1ndness/SWDE-Dataset/master"

# Sites to download
SITES_TO_DOWNLOAD = {
    "auto": {
        "sites": ["aol", "msn"],
        "fields": ["model", "price", "engine", "fuel_economy"]
    },
    "camera": {
        "sites": ["amazon", "buy"],
        "fields": ["model", "manufacturer", "price"]
    },
    "nbaplayer": {
        "sites": ["espn", "yahoo"],
        "fields": ["name", "team", "height", "weight"]
    },
    "restaurant": {
        "sites": ["opentable", "urbanspoon"],
        "fields": ["name", "address", "phone", "cuisine"]
    },
    "university": {
        "sites": ["collegeboard", "matchcollege"],
        "fields": ["name", "phone", "type", "website"]
    },
    "job": {
        "sites": ["careerbuilder"],  # Only need HTML for this one
        "fields": []  # Already have ground truth
    }
}

def download_file(url, local_path):
    """Download a file from URL to local path"""
    try:
        response = requests.get(url)
        if response.status_code == 200:
            local_path.parent.mkdir(parents=True, exist_ok=True)
            with open(local_path, 'w', encoding='utf-8') as f:
                f.write(response.text)
            print(f"✓ Downloaded: {local_path}")
            return True
        else:
            print(f"✗ Failed to download {url} (status: {response.status_code})")
            return False
    except Exception as e:
        print(f"✗ Error downloading {url}: {e}")
        return False

def main():
    base_dir = Path("~/tools/XPathGenie/data/swde").expanduser()
    html_dir = base_dir / "html"
    gt_dir = base_dir / "groundtruth"
    
    total_downloads = 0
    successful_downloads = 0
    
    for vertical, config in SITES_TO_DOWNLOAD.items():
        print(f"\n=== Downloading {vertical.upper()} vertical ===")
        
        for site in config["sites"]:
            print(f"\n--- Processing {vertical}-{site} ---")
            
            # Download HTML pages (0000-0009)
            site_dir = html_dir / f"{vertical}-{site}"
            for i in range(10):
                page_num = f"{i:04d}"
                html_url = f"{BASE_URL}/{vertical}/{vertical}-{site}(2000)/{page_num}.htm"
                html_path = site_dir / f"{page_num}.htm"
                
                total_downloads += 1
                if download_file(html_url, html_path):
                    successful_downloads += 1
                
                # Rate limiting
                time.sleep(0.5)
            
            # Download ground truth files (skip for job-careerbuilder)
            if vertical != "job":
                for field in config["fields"]:
                    gt_url = f"{BASE_URL}/groundtruth/{vertical}/{vertical}-{site}-{field}.txt"
                    gt_path = gt_dir / f"{vertical}-{site}-{field}.txt"
                    
                    total_downloads += 1
                    if download_file(gt_url, gt_path):
                        successful_downloads += 1
                    
                    # Rate limiting
                    time.sleep(0.5)
    
    print(f"\n=== Download Summary ===")
    print(f"Total attempts: {total_downloads}")
    print(f"Successful: {successful_downloads}")
    print(f"Failed: {total_downloads - successful_downloads}")
    print(f"Success rate: {successful_downloads/total_downloads*100:.1f}%")

if __name__ == "__main__":
    main()