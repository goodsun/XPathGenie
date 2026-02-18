#!/usr/bin/env python3
"""Download SWDE dataset HTML files with correct URL encoding."""
import os
import time
import urllib.request
import json

BASE_API = "https://api.github.com/repos/W1ndness/SWDE-Dataset/contents"
BASE_RAW = "https://raw.githubusercontent.com/W1ndness/SWDE-Dataset/master"
HTML_DIR = os.path.expanduser("~/tools/XPathGenie/data/swde/html")
GT_DIR = os.path.expanduser("~/tools/XPathGenie/data/swde/groundtruth")
NUM_PAGES = 10

# Sites to download per vertical
TARGETS = {
    "auto": ["aol", "msn", "yahoo"],
    "camera": ["amazon", "buy", "beachaudio"],
    "nbaplayer": ["espn", "yahoo", "wiki"],
    "restaurant": ["opentable", "urbanspoon", "fodors"],
    "university": ["collegeboard", "matchcollege", "usnews"],
    # Already have these but re-download to be safe
    "job": ["monster", "dice", "careerbuilder"],
    "book": ["amazon", "borders"],
    "movie": ["imdb", "yahoo"],
}

FIELDS = {
    "auto": ["model", "price", "engine", "fuel_economy"],
    "camera": ["model", "manufacturer", "price"],
    "nbaplayer": ["name", "team", "height", "weight"],
    "restaurant": ["name", "address", "phone", "cuisine"],
    "university": ["name", "phone", "type", "website"],
    "job": ["title", "company", "location", "date_posted"],
    "book": ["title", "author", "isbn_13", "publisher", "publication_date"],
    "movie": ["title", "director", "genre", "mpaa_rating"],
}

def get_dir_listing(vertical):
    """Get actual directory names from GitHub API."""
    url = f"{BASE_API}/{vertical}"
    req = urllib.request.Request(url, headers={"User-Agent": "XPathGenie-Eval"})
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())

def download_file(url, path):
    """Download a file."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": "XPathGenie-Eval"})
    try:
        with urllib.request.urlopen(req) as resp:
            data = resp.read()
            with open(path, 'wb') as f:
                f.write(data)
            return len(data)
    except Exception as e:
        print(f"  FAIL: {e}")
        return 0

def main():
    total_downloaded = 0
    
    for vertical, sites in TARGETS.items():
        print(f"\n=== {vertical} ===")
        
        # Get actual directory names
        try:
            dirs = get_dir_listing(vertical)
            dir_map = {}
            for d in dirs:
                if d['type'] == 'dir':
                    # e.g. "camera-amazon(1767)" -> "amazon"
                    name = d['name']
                    site = name.split('(')[0].replace(f"{vertical}-", "")
                    dir_map[site] = name
            time.sleep(0.3)
        except Exception as e:
            print(f"  Error listing {vertical}: {e}")
            continue
        
        for site in sites:
            if site not in dir_map:
                print(f"  {site}: not found in repo")
                continue
            
            actual_dir = dir_map[site]
            encoded_dir = actual_dir.replace("(", "%28").replace(")", "%29")
            local_dir = f"{HTML_DIR}/{vertical}-{site}"
            os.makedirs(local_dir, exist_ok=True)
            
            print(f"  {site} ({actual_dir}):")
            
            # Download HTML pages
            for page in range(NUM_PAGES):
                page_id = f"{page:04d}"
                url = f"{BASE_RAW}/{vertical}/{encoded_dir}/{page_id}.htm"
                path = f"{local_dir}/{page_id}.htm"
                
                # Skip if already good
                if os.path.exists(path) and os.path.getsize(path) > 100:
                    continue
                
                size = download_file(url, path)
                if size > 0:
                    total_downloaded += 1
                time.sleep(0.2)
            
            # Verify
            valid = sum(1 for p in range(NUM_PAGES) 
                       if os.path.exists(f"{local_dir}/{p:04d}.htm") 
                       and os.path.getsize(f"{local_dir}/{p:04d}.htm") > 100)
            print(f"    HTML: {valid}/{NUM_PAGES} valid pages")
            
            # Download ground truth
            for field in FIELDS[vertical]:
                gt_file = f"{vertical}-{site}-{field}.txt"
                gt_path = f"{GT_DIR}/{gt_file}"
                if os.path.exists(gt_path) and os.path.getsize(gt_path) > 10:
                    continue
                url = f"{BASE_RAW}/groundtruth/{vertical}/{gt_file}"
                size = download_file(url, gt_path)
                if size > 0:
                    total_downloaded += 1
                time.sleep(0.2)
    
    print(f"\nDone! Downloaded {total_downloaded} new files.")

if __name__ == "__main__":
    main()
