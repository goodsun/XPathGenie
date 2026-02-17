#!/bin/bash
# Full evaluation: Auto Discover + Want List for all 22 SSR sites
# Results saved to docs/evaluation/results/{site}_auto.json and {site}_wantlist.json

cd /home/ec2-user/tools/XPathGenie

SITES=(
  "#1 tsukui-staff"
  "#2 selva-i"
  "#4 yakumatch"
  "#5 mynavi"
  "#6 phget"
  "#8 apuro"
  "#9 oshigoto-lab"
  "#10 yakuzaishisyusyoku"
  "#12 bestcareer"
  "#13 pharmapremium"
  "#14 caresta"
  "#16 pharmalink"
  "#18 nikken-care"
  "#19 nikken-nurse"
  "#20 cocofump"
  "#21 MRT-nurse"
  "#24 kaigo-work"
  "#25 w-medical-9"
  "#26 firstnavi"
  "#30 mc-pharma"
  "#31 ph-10"
  "#32 yakusta"
  "#35 kaigokango"
)

echo "=== AUTO DISCOVER MODE ==="
for site in "${SITES[@]}"; do
  echo ""
  echo ">>> $site (Auto Discover)"
  python3 -u scripts/evaluate_site.py "$site" --mode auto
done

echo ""
echo "=== WANT LIST MODE ==="
for site in "${SITES[@]}"; do
  echo ""
  echo ">>> $site (Want List)"
  python3 -u scripts/evaluate_site.py "$site" --mode wantlist
done

echo ""
echo "=== DONE ==="
