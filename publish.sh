#!/bin/bash
# Weekly: refresh citation and attention numbers, rebuild impact.json and publish it to GitHub Pages.
# Run by ~/Library/LaunchAgents/com.laraweed.metrics.plist; output goes to ~/Library/Logs/laraweed-metrics.log.
set -euo pipefail
FOLDER="/Users/lara/Library/CloudStorage/OneDrive-Stanford/Scientific Visibility"
REPO="$HOME/laraweed-metrics"
echo "=== $(date '+%Y-%m-%d %H:%M') ==="
cd "$FOLDER"
/usr/bin/python3 -I refresh_metrics.py
/usr/bin/python3 -I brand-assets/source/build_pub_stats.py "$FOLDER" "$REPO/impact.json"
cd "$REPO"
if git diff --quiet -- impact.json; then
  echo "No change in the numbers."
else
  git add impact.json
  git commit -q -m "Refresh metrics $(date +%Y-%m-%d)"
  git push -q origin main
  echo "Published new numbers."
fi
