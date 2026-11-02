# laraweed-metrics

Citation and attention numbers for the Publications page on [laraweed.com](https://www.laraweed.com/publications), served as `impact.json` via GitHub Pages.

A weekly job on Lara Weed's Mac refreshes them from her public Google Scholar profile and Altmetric, and commits only when something changed. The page falls back to built-in numbers if this file can't be reached.

- `publish.sh` is the weekly job, run Mondays at 9:00 by `~/Library/LaunchAgents/com.laraweed.metrics.plist`. It logs to `~/Library/Logs/laraweed-metrics.log`.
- It works from `job/`, a local copy kept outside OneDrive, which macOS doesn't let background jobs read. `sync_job.sh` refreshes that copy after papers are added to the tracker or the scripts change.
