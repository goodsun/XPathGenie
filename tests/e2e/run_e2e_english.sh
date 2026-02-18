#!/bin/bash
# E2E Test: English sites — fetch HTML snapshots + analyze via API
# Usage: ./run_e2e_english.sh

set -e

BASE_DIR="$(cd "$(dirname "$0")" && pwd)"
DATE="260218_en"
SNAP_DIR="$BASE_DIR/snapshots/$DATE"
IMG_DIR="$BASE_DIR/images/$DATE"
API="http://localhost:8789"
REFERER="https://corp.bon-soleil.com/"

mkdir -p "$SNAP_DIR" "$IMG_DIR"

# Test sites
declare -A SITES
SITES[allrecipes]="https://www.allrecipes.com/recipe/22180/waffles-i/"
SITES[books]="https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html"
SITES[hackernews]="https://news.ycombinator.com/item?id=1"

echo "=== XPathGenie E2E Test (English Sites) ==="
echo "Date: $(date -u '+%Y-%m-%d %H:%M UTC')"
echo ""

for site in "${!SITES[@]}"; do
    url="${SITES[$site]}"
    echo "--- Testing: $site ($url) ---"
    
    # Step 1: Fetch HTML via API
    echo "[1] Fetching HTML..."
    RESPONSE=$(curl -s "$API/api/fetch?url=$url" -H "Referer: $REFERER")
    ERROR=$(echo "$RESPONSE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('error',''))" 2>/dev/null)
    
    if [ -n "$ERROR" ]; then
        echo "  FAIL: $ERROR"
        continue
    fi
    
    # Save HTML snapshot
    echo "$RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin)['html'])" > "$SNAP_DIR/${site}.html"
    SIZE=$(ls -lh "$SNAP_DIR/${site}.html" | awk '{print $5}')
    echo "  Saved snapshot: $SNAP_DIR/${site}.html ($SIZE)"
    
    # Step 2: Analyze via API (auto-discover mode)
    echo "[2] Analyzing..."
    ANALYZE_RESPONSE=$(curl -s -X POST "$API/api/analyze" \
        -H "Content-Type: application/json" \
        -H "Referer: $REFERER" \
        -d "{\"urls\": [\"$url\"], \"mode\": \"auto\"}")
    
    STATUS=$(echo "$ANALYZE_RESPONSE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('status',''))" 2>/dev/null)
    
    if [ "$STATUS" = "error" ]; then
        REASON=$(echo "$ANALYZE_RESPONSE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('message','unknown'))" 2>/dev/null)
        echo "  Analyze failed: $REASON"
        # Still save fetch result
        echo "  (HTML snapshot saved, analyze failed)"
        continue
    fi
    
    # Save analysis result
    echo "$ANALYZE_RESPONSE" | python3 -m json.tool > "$SNAP_DIR/${site}_analysis.json" 2>/dev/null || \
        echo "$ANALYZE_RESPONSE" > "$SNAP_DIR/${site}_analysis.json"
    
    # Count fields
    FIELDS=$(echo "$ANALYZE_RESPONSE" | python3 -c "
import sys, json
d = json.load(sys.stdin)
m = d.get('mapping', d.get('mappings', {}))
if isinstance(m, dict):
    print(len(m))
elif isinstance(m, list):
    print(len(m))
else:
    print('?')
" 2>/dev/null || echo "?")
    
    echo "  Fields found: $FIELDS"
    echo "  Saved analysis: $SNAP_DIR/${site}_analysis.json"
    echo "  ✅ PASS"
    echo ""
done

echo "=== Summary ==="
echo "Snapshots: $(ls $SNAP_DIR/*.html 2>/dev/null | wc -l) HTML files"
echo "Analyses:  $(ls $SNAP_DIR/*_analysis.json 2>/dev/null | wc -l) results"
echo "Location:  $SNAP_DIR/"
echo "=== Done ==="
