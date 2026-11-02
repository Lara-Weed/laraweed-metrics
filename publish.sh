#!/bin/bash
# Weekly: refresh citation and attention numbers, rebuild impact.json and publish it to GitHub Pages, along with
# any edits to conferences.json. Run by ~/Library/LaunchAgents/com.laraweed.metrics.plist; output goes to
# ~/Library/Logs/laraweed-metrics.log. Run it by hand to publish a conference edit right away.
# Works from ./job, a copy kept outside OneDrive (which background jobs can't read). The paper list comes from
# Zotero My Publications each run, so sync_job.sh is only needed when the scripts change.
set -euo pipefail
REPO="$HOME/laraweed-metrics"
JOB="$REPO/job"
echo "=== $(date '+%Y-%m-%d %H:%M') ==="
cd "$REPO"
# Pick up edits made on github.com, such as a conference added there
git pull -q --rebase --autostash origin main || echo "Couldn't pull from GitHub; using the local files."
/usr/bin/python3 -I "$REPO/zotero_papers.py"
cd "$JOB"
/usr/bin/python3 -I refresh_metrics.py
/usr/bin/python3 -I build_pub_stats.py "$JOB" "$REPO/impact.json"
cd "$REPO"
PUSH=0
if git diff --quiet -- impact.json; then
  echo "No change in the numbers."
else
  git add impact.json
  git commit -q -m "Refresh metrics $(date +%Y-%m-%d)"
  echo "New numbers."
  PUSH=1
fi
if ! git diff --quiet -- conferences.json; then
  if /usr/bin/python3 -I "$REPO/check_conferences.py" "$REPO/conferences.json"; then
    git add conferences.json
    git commit -q -m "Update conference presentations $(date +%Y-%m-%d)"
    PUSH=1
  fi
fi
if [ "$PUSH" = 1 ]; then
  git push -q origin main
  echo "Published."
fi
