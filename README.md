# laraweed-metrics

Data for the Publications page on [laraweed.com](https://www.laraweed.com/publications), served via GitHub Pages:

- `impact.json` holds the citation and attention numbers.
- `conferences.json` holds the conference presentations list.
- `news.json` holds the press highlights for In the news on Writing & Media.

Each block falls back to a built-in copy if it can't reach its file.

A weekly job on Lara Weed's Mac refreshes the numbers from her public Google Scholar profile and Altmetric, and commits only when something changed.

- `publish.sh` is the weekly job. `run_weekly.sh` runs it Mondays at 9:00, launched by `~/Library/LaunchAgents/com.laraweed.metrics.plist`. If the Mac is offline then, it runs once the connection is back (checked hourly and on each network change, Monday to Friday). If it fails while online, it retries up to 4 times that week, then sends a Mac notification. Both log to `~/Library/Logs/laraweed-metrics.log`.
- Each run, `zotero_papers.py` reads the paper list from Zotero My Publications, the library behind the website's Publications page, so new papers are picked up on their own.
- It works from `job/`, a local copy of the scripts kept outside OneDrive, which macOS doesn't let background jobs read. `sync_job.sh` refreshes that copy when the scripts change.
- `record_history.py` keeps a dated record of each run's numbers, overall and per paper, in `job/metrics-history.csv` and `job/metrics-history-papers.csv`, and copies them to the Upkeep folder. `job/` is in `.gitignore`, so the record stays on the Mac.

## Adding a conference presentation

Copy an entry in `conferences.json`, paste it first in the list and edit it. The website sorts the list by year. `format` is `"Oral"`, `"Poster"` or `""`. Lara's name is bolded wherever an author starts with `Weed L`.

- **On github.com:** edit the file there and commit. It's live in about a minute, and the weekly job pulls the change.
- **On the Mac:** edit `~/laraweed-metrics/conferences.json`. Then run `~/laraweed-metrics/publish.sh` to publish it now, or let Monday's job do it. Either way `check_conferences.py` checks the file first and holds back an edit that would break the list.

## Adding a press story

Add it to a group's `stories` in `news.json`, with `outlet`, `title`, `date` (`"2026-07-16"` or `"2026-07"`) and `url`. Optionally add `when` to show a label such as `"Winter 2026"` instead of the date. The website shows each group's stories in the order listed, so put the ones you most want seen first. It shows four, with the rest behind Show more, and adds "and N more stories" from Altmetric for groups tied to a paper. Groups appear in the order they're listed. A `section` value prints a small heading, such as "Co-authored studies", before that group, and a group can have a section instead of a label. `"column": 2` starts the right-hand column on wide screens; the groups after it go there too.

Publish it the same two ways as a conference. `check_news.py` checks the file first.

Each Monday, `news_watch.py` compares Altmetric's news mentions of the papers with the ones it has seen (`job/news-seen.json`). When a well-known English-language outlet covers a paper, or a paper gets its first story, it lists the story in the log and sends a Mac notification. It never changes `news.json`.

## Profiles and features from Google Alerts

`news_watch.py` also reads the RSS feed of Lara's "Lara Weed" Google Alert. Its address lives in `~/.config/presence-tracker/news-alert.json`, outside this public repo. A new story goes straight into the Features group of `news.json`, newest first, when it names Lara Weed, is in English, and comes from a Stanford news site or a well-known outlet (the `STANFORD_NEWS` and `PRESS` lists in the script). Profile and directory pages don't count. Everything else is only listed in the log. When a story is added, the weekly job publishes it and sends a Mac notification; to undo one, delete it from `news.json`.

To see what the feed would add without changing anything: `python3 news_watch.py --no-notify --dry-run`
