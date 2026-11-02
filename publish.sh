#!/bin/bash
# Weekly: refresh citation and attention numbers, rebuild impact.json and publish it to GitHub Pages.
# Run by ~/Library/LaunchAgents/com.laraweed.metrics.plist; output goes to ~/Library/Logs/laraweed-metrics.log.
# Works from ./job, a copy kept outside OneDrive (which background jobs can't read). The paper list comes from
# Zotero My Publications each run, so sync_job.sh is only needed when the scripts change.
set -euo pipefail
REPO="$HOME/laraweed-metrics"
JOB="$REPO/job"
echo "=== $(date '+%Y-%m-%d %H:%M') ==="
/usr/bin/python3 -I "$REPO/zotero_papers.py"
cd "$JOB"
/usr/bin/python3 -I refresh_metrics.py
/usr/bin/python3 -I build_pub_stats.py "$JOB" "$REPO/impact.json"
cd "$REPO"
if git diff --quiet -- impact.json; then
  echo "No change in the numbers."
else
  git add impact.json
  git commit -q -m "Refresh metrics $(date +%Y-%m-%d)"
  git push -q origin main
  echo "Published new numbers."
fi
