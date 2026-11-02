#!/bin/bash
# Copy what the weekly job needs out of the OneDrive folder, which background jobs aren't allowed to read.
# Run this (or ask Claude to) after adding papers to the tracker or changing the scripts.
set -euo pipefail
FOLDER="/Users/lara/Library/CloudStorage/OneDrive-Stanford/Scientific Visibility"
JOB="$HOME/laraweed-metrics/job"
mkdir -p "$JOB/brand-assets"
cp "$FOLDER/refresh_metrics.py" "$FOLDER/tracker-data.js" "$FOLDER/brand-assets/source/build_pub_stats.py" "$JOB/"
[ -f "$JOB/metrics-data.js" ] || cp "$FOLDER/metrics-data.js" "$JOB/"
echo "Synced job files ($(date '+%Y-%m-%d %H:%M'))."
