#!/bin/bash
# Weekly: refresh citation and attention numbers, rebuild impact.json and publish it to GitHub Pages, along with
# any edits to conferences.json and news.json, and flag new press coverage (news_watch.py).
# Also records the numbers in job/metrics-history*.csv (record_history.py), copied to Upkeep/ and never pushed.
# Run weekly by run_weekly.sh (via ~/Library/LaunchAgents/com.laraweed.metrics.plist); output goes to ~/Library/Logs/laraweed-metrics.log.
# Run it by hand to publish a conference or news edit right away.
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
/usr/bin/python3 -I "$REPO/record_history.py" || echo "History not recorded."
cd "$REPO"
/usr/bin/python3 -I "$REPO/news_watch.py" || echo "News watch skipped."
PUSH=0
if git diff --quiet -- impact.json; then
  echo "No change in the numbers."
else
  git add impact.json
  git commit -q -m "Refresh metrics $(date +%Y-%m-%d)"
  echo "New numbers."
  PUSH=1
fi
# Lists Lara edits by hand, each published only if its checker passes
for list in conferences news; do
  if ! git diff --quiet -- "$list.json"; then
    if /usr/bin/python3 -I "$REPO/check_$list.py" "$REPO/$list.json"; then
      git add "$list.json"
      git commit -q -m "Update $list.json $(date +%Y-%m-%d)"
      PUSH=1
    fi
  fi
done
if [ "$PUSH" = 1 ]; then
  git push -q origin main
  echo "Published."
fi
