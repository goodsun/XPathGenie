#!/bin/bash

BASE_URL="https://raw.githubusercontent.com/W1ndness/SWDE-Dataset/master"
BASE_DIR="$HOME/tools/XPathGenie/data/swde"
HTML_DIR="$BASE_DIR/html"
GT_DIR="$BASE_DIR/groundtruth"

total=0
success=0

download_file() {
    local url="$1"
    local path="$2"
    local desc="$3"
    
    total=$((total + 1))
    mkdir -p "$(dirname "$path")"
    
    if curl -s "$url" > "$path" 2>/dev/null; then
        if [ -s "$path" ]; then
            echo "✓ $desc"
            success=$((success + 1))
        else
            echo "✗ $desc (empty file)"
            rm -f "$path"
        fi
    else
        echo "✗ $desc (download failed)"
    fi
    
    sleep 0.5  # Rate limiting
}

echo "=== Downloading SWDE Dataset Extensions ==="

# Auto vertical (auto-aol, auto-msn)
echo -e "\n--- AUTO ---"
for site in aol msn; do
    echo "Processing auto-$site..."
    for i in {0..9}; do
        page=$(printf "%04d" $i)
        download_file "$BASE_URL/auto/auto-$site(2000)/$page.htm" \
                     "$HTML_DIR/auto-$site/$page.htm" \
                     "auto-$site/$page.htm"
    done
    
    for field in model price engine fuel_economy; do
        download_file "$BASE_URL/groundtruth/auto/auto-$site-$field.txt" \
                     "$GT_DIR/auto-$site-$field.txt" \
                     "auto-$site-$field.txt"
    done
done

# Camera vertical (camera-amazon, camera-buy)
echo -e "\n--- CAMERA ---"
for site in amazon buy; do
    echo "Processing camera-$site..."
    for i in {0..9}; do
        page=$(printf "%04d" $i)
        download_file "$BASE_URL/camera/camera-$site(2000)/$page.htm" \
                     "$HTML_DIR/camera-$site/$page.htm" \
                     "camera-$site/$page.htm"
    done
    
    for field in model manufacturer price; do
        download_file "$BASE_URL/groundtruth/camera/camera-$site-$field.txt" \
                     "$GT_DIR/camera-$site-$field.txt" \
                     "camera-$site-$field.txt"
    done
done

# NBA Player vertical (nbaplayer-espn, nbaplayer-yahoo)
echo -e "\n--- NBAPLAYER ---"
for site in espn yahoo; do
    echo "Processing nbaplayer-$site..."
    for i in {0..9}; do
        page=$(printf "%04d" $i)
        download_file "$BASE_URL/nbaplayer/nbaplayer-$site(2000)/$page.htm" \
                     "$HTML_DIR/nbaplayer-$site/$page.htm" \
                     "nbaplayer-$site/$page.htm"
    done
    
    for field in name team height weight; do
        download_file "$BASE_URL/groundtruth/nbaplayer/nbaplayer-$site-$field.txt" \
                     "$GT_DIR/nbaplayer-$site-$field.txt" \
                     "nbaplayer-$site-$field.txt"
    done
done

# Restaurant vertical (restaurant-opentable, restaurant-urbanspoon)
echo -e "\n--- RESTAURANT ---"
for site in opentable urbanspoon; do
    echo "Processing restaurant-$site..."
    for i in {0..9}; do
        page=$(printf "%04d" $i)
        download_file "$BASE_URL/restaurant/restaurant-$site(2000)/$page.htm" \
                     "$HTML_DIR/restaurant-$site/$page.htm" \
                     "restaurant-$site/$page.htm"
    done
    
    for field in name address phone cuisine; do
        download_file "$BASE_URL/groundtruth/restaurant/restaurant-$site-$field.txt" \
                     "$GT_DIR/restaurant-$site-$field.txt" \
                     "restaurant-$site-$field.txt"
    done
done

# University vertical (university-collegeboard, university-matchcollege)
echo -e "\n--- UNIVERSITY ---"
for site in collegeboard matchcollege; do
    echo "Processing university-$site..."
    for i in {0..9}; do
        page=$(printf "%04d" $i)
        download_file "$BASE_URL/university/university-$site(2000)/$page.htm" \
                     "$HTML_DIR/university-$site/$page.htm" \
                     "university-$site/$page.htm"
    done
    
    for field in name phone type website; do
        download_file "$BASE_URL/groundtruth/university/university-$site-$field.txt" \
                     "$GT_DIR/university-$site-$field.txt" \
                     "university-$site-$field.txt"
    done
done

# Job vertical (job-careerbuilder) - HTML only, we already have ground truth
echo -e "\n--- JOB (HTML only) ---"
echo "Processing job-careerbuilder..."
for i in {0..9}; do
    page=$(printf "%04d" $i)
    download_file "$BASE_URL/job/job-careerbuilder(2000)/$page.htm" \
                 "$HTML_DIR/job-careerbuilder/$page.htm" \
                 "job-careerbuilder/$page.htm"
done

echo -e "\n=== Download Summary ==="
echo "Total attempts: $total"
echo "Successful: $success"
echo "Failed: $((total - success))"
echo "Success rate: $(echo "scale=1; $success * 100 / $total" | bc)%"