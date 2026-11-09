#!/bin/bash
# Run by ~/Library/LaunchAgents/com.laraweed.metrics.plist on Mondays at 9:00, every hour, and whenever the
# network changes. It runs publish.sh once a week, starting Monday 9:00. If the Mac is offline then, it waits
# and runs as soon as a connection is back. Catch-up runs happen only Monday to Friday; a week that never got
# a connection is covered by the next Monday's run.
# If publish.sh fails while online, it tries again on later triggers, at most 4 times a week, then sends a Mac
# notification and waits for the next week.
# Run publish.sh directly to publish an edit right away; that skips these checks.
set -uo pipefail
REPO="$HOME/laraweed-metrics"
STATE="$REPO/job"
WEEK=$(date +%G-W%V)
DOW=$(date +%u)    # 1 = Monday
HOUR=$((10#$(date +%H)))

[ "$DOW" -le 5 ] || exit 0                                  # weekdays only
[ "$DOW" -gt 1 ] || [ "$HOUR" -ge 9 ] || exit 0              # not before Monday 9:00
[ "$(cat "$STATE/weekly-done" 2>/dev/null)" != "$WEEK" ] || exit 0

FAILS=0
read -r FWEEK FCOUNT 2>/dev/null < "$STATE/weekly-fails" && [ "$FWEEK" = "$WEEK" ] && FAILS=$FCOUNT
[ "$FAILS" -lt 4 ] || exit 0

# Offline: say so once a week in the log, then wait for the next trigger
if ! /usr/bin/curl -s -o /dev/null --max-time 15 https://github.com; then
  if [ "$(cat "$STATE/weekly-waiting" 2>/dev/null)" != "$WEEK" ]; then
    echo "=== $(date '+%Y-%m-%d %H:%M') === No network; the weekly job will run when the connection is back."
    echo "$WEEK" > "$STATE/weekly-waiting"
  fi
  exit 0
fi

if /bin/bash "$REPO/publish.sh"; then
  echo "$WEEK" > "$STATE/weekly-done"
  rm -f "$STATE/weekly-fails"
else
  FAILS=$((FAILS + 1))
  echo "$WEEK $FAILS" > "$STATE/weekly-fails"
  if [ "$FAILS" -ge 4 ]; then
    echo "Weekly job failed $FAILS times this week; stopping until next Monday."
    /usr/bin/osascript -e 'display notification "It failed 4 times this week. See ~/Library/Logs/laraweed-metrics.log." with title "Website metrics didn'"'"'t update"'
  else
    echo "Weekly job failed (attempt $FAILS of 4); it will try again later."
  fi
fi
