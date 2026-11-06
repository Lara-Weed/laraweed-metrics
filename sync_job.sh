#!/bin/bash
# Copy what the weekly job needs out of the OneDrive folder, which background jobs aren't allowed to read.
# Run this (or ask Claude to) after changing refresh_metrics.py or build_pub_stats.py. New papers need nothing:
# the weekly job reads them from Zotero My Publications.
set -euo pipefail
FOLDER="/Users/lara/Library/CloudStorage/OneDrive-Stanford/Scientific Visibility"
JOB="$HOME/laraweed-metrics/job"
mkdir -p "$JOB/brand-assets"
# Since Nov 5, 2026 the tracker and its script live in Upkeep/ and the site's build scripts in Website/.
cp "$FOLDER/Upkeep/refresh_metrics.py" "$FOLDER/Upkeep/tracker-data.js" "$FOLDER/Website/brand-assets/source/build_pub_stats.py" "$JOB/"
[ -f "$JOB/metrics-data.js" ] || cp "$FOLDER/Upkeep/metrics-data.js" "$JOB/"
echo "Synced job files ($(date '+%Y-%m-%d %H:%M'))."
