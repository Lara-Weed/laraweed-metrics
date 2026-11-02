# laraweed-metrics

Citation and attention numbers for the Publications page on [laraweed.com](https://www.laraweed.com/publications), served as `impact.json` via GitHub Pages.

A weekly job on Lara Weed's Mac refreshes them from her public Google Scholar profile and Altmetric, and commits only when something changed. The page falls back to built-in numbers if this file can't be reached.

- `publish.sh` is the weekly job, run Mondays at 9:00 by `~/Library/LaunchAgents/com.laraweed.metrics.plist`. It logs to `~/Library/Logs/laraweed-metrics.log`.
- Each run, `zotero_papers.py` reads the paper list from Zotero My Publications, the library behind the website's Publications page, so new papers are picked up on their own.
- It works from `job/`, a local copy of the scripts kept outside OneDrive, which macOS doesn't let background jobs read. `sync_job.sh` refreshes that copy when the scripts change.
