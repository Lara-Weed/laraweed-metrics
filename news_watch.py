"""Weekly check for new press coverage of Lara's papers, run by publish.sh.

Pulls every news mention of her papers from Altmetric Explorer and compares it with the ones seen before
(job/news-seen.json). When a well-known outlet covers her work, or a paper gets its first story, it lists
them in the log and sends a Mac notification. Nothing is published: picks go into news.json by hand.

Run by hand to see what's new:  python3 news_watch.py --no-notify
"""
import hashlib
import hmac
import json
import os
import subprocess
import sys
import time
import urllib.parse
import urllib.request

REPO = os.path.dirname(os.path.abspath(__file__))
SEEN_PATH = os.path.join(REPO, "job", "news-seen.json")
CRED_PATH = os.path.expanduser("~/.config/presence-tracker/altmetric.json")
DEFAULT_RESEARCHER = "ur.015772061677.94"

# Outlets worth a look, matched case-insensitively against Altmetric's outlet names
NOTABLE = {
    "washington post", "the new york times", "new york times", "the wall street journal", "wall street journal",
    "the guardian", "bbc news", "cnn news", "npr", "time magazine", "newsweek", "the atlantic", "the economist",
    "reuters", "ap news", "associated press", "usa today", "los angeles times", "the boston globe", "bloomberg",
    "financial times", "cbs news", "nbc news", "abc news", "today", "fox news", "the hill", "axios", "vox.com",
    "wired", "stat", "scientific american", "science", "nature", "new scientist", "national geographic",
    "popular science", "discover magazine", "smithsonian magazine", "the conversation", "forbes", "healthline",
    "medical news today", "verywell health", "everyday health", "aarp", "prevention", "men's health",
    "women's health", "psychology today", "deutsche welle", "tagesschau", "spektrum", "el país", "le monde",
    "the globe and mail", "ici.radio-canada.ca", "sydney morning herald", "the irish times", "the independent",
}


def get(path, filters, extra, key, secret):
    # Explorer signs each request with an HMAC-SHA1 of the filters, sorted by name and joined by "|"
    parts, query = [], []
    for name in sorted(filters):
        values = filters[name] if isinstance(filters[name], list) else [filters[name]]
        parts.append(name)
        parts.extend(values)
        if isinstance(filters[name], list):
            query += [(f"filter[{name}][]", v) for v in values]
        else:
            query.append((f"filter[{name}]", filters[name]))
    digest = hmac.new(secret.encode(), "|".join(parts).encode(), hashlib.sha1).hexdigest()
    url = ("https://www.altmetric.com/explorer/api/" + path + "?" +
           urllib.parse.urlencode([("digest", digest)] + query + [("key", key)] + extra))
    with urllib.request.urlopen(urllib.request.Request(url, headers={"Accept": "application/json"}), timeout=60) as r:
        return json.load(r)


def news_mentions(key, secret, researcher):
    """Every news mention of the researcher's outputs, as dicts with id, outlet, title, url, date and outputs."""
    filters = {"researcher_id": [researcher], "timeframe": "at", "mention_types": ["msm"]}
    data, included, page = [], {}, 1
    while True:
        d = get("research_outputs/mentions", filters, [("page[number]", str(page)), ("page[size]", "100")], key, secret)
        data += d.get("data") or []
        for inc in d.get("included") or []:
            included[(inc.get("type"), str(inc.get("id")))] = inc
        if len(d.get("data") or []) < 100 or page >= 30:
            break
        page += 1
        time.sleep(1)
    out = []
    for m in data:
        a, rel = m.get("attributes") or {}, m.get("relationships") or {}
        author = ((rel.get("author") or {}).get("data")) or {}
        outlet = (((included.get(("profile", str(author.get("id")))) or {}).get("attributes")) or {}).get("name", "")
        outputs = [str(((r or {}).get("data") or {}).get("id")) for r in rel.get("research-outputs") or []]
        out.append({"id": str(m.get("id")), "outlet": outlet.strip(), "title": a.get("title") or "",
                    "url": a.get("url") or "", "date": (a.get("posted-on") or "")[:10], "outputs": outputs})
    return out


def her_papers():
    """Altmetric output id -> title, for the papers in her tracker, from the metrics the job just refreshed."""
    s = open(os.path.join(REPO, "job", "metrics-data.js"), encoding="utf-8").read()
    metrics = json.loads(s[s.index("= ") + 2:].rstrip().rstrip(";"))
    papers = {}
    for rec in (metrics.get("altmetric") or {}).values():
        if rec.get("url"):
            papers[rec["url"].rsplit("/", 1)[-1]] = rec.get("title", "")
    return papers


def notify(message):
    subprocess.run(["osascript", "-e", "on run argv", "-e",
                    'display notification (item 1 of argv) with title "New press coverage"', "-e", "end run", message],
                   check=False)


def main():
    creds = json.load(open(CRED_PATH))
    papers = her_papers()
    mentions = news_mentions(creds["explorer_key"], creds["explorer_secret"], creds.get("researcher_id", DEFAULT_RESEARCHER))

    first_run = not os.path.exists(SEEN_PATH)
    seen = {"mentions": [], "papers": []} if first_run else json.load(open(SEEN_PATH))
    seen_ids, covered = set(seen["mentions"]), set(seen["papers"])

    new = [m for m in mentions if m["id"] not in seen_ids]
    worth = []
    for m in new:
        mine = [p for p in m["outputs"] if p in papers]
        if not mine:
            continue
        first_story = [p for p in mine if p not in covered]
        if m["outlet"].lower() in NOTABLE or first_story:
            worth.append((m, papers[mine[0]], bool(first_story)))
        covered.update(mine)

    seen = {"mentions": sorted(seen_ids | {m["id"] for m in mentions}), "papers": sorted(covered)}
    with open(SEEN_PATH, "w", encoding="utf-8") as f:
        json.dump(seen, f)

    if first_run:
        print(f"News watch: started with {len(mentions)} stories already seen.")
        return
    print(f"News watch: {len(new)} new {'story' if len(new) == 1 else 'stories'}, {len(worth)} worth a look.")
    for m, paper, first in worth:
        print(f"  {m['date']} {m['outlet']}{' (first story for this paper)' if first else ''}: {m['title']}")
        print(f"      {paper[:90]}")
        print(f"      {m['url']}")
    if worth and "--no-notify" not in sys.argv:
        outlets = sorted({m["outlet"] for m, _, _ in worth})
        notify(f"{len(worth)} new {'story' if len(worth) == 1 else 'stories'} about your work, including "
               f"{', '.join(outlets[:3])}. Details in ~/Library/Logs/laraweed-metrics.log.")


if __name__ == "__main__":
    main()
