"""Weekly check for new press coverage, run by publish.sh.

Altmetric: pulls every news mention of Lara's papers from Altmetric Explorer and compares it with the ones seen
before (job/news-seen.json). When a well-known outlet covers her work, or a paper gets its first story, it lists
them in the log and sends a Mac notification. These are never added to news.json; she picks them by hand.

Google Alert: reads the RSS feed of her "Lara Weed" alert (address in ~/.config/presence-tracker/news-alert.json).
A story that names her, is in English, and comes from a Stanford news site or a well-known outlet is added to the
Features group in news.json, which publish.sh then publishes, and she gets a notification saying what went in.
Everything else is only listed in the log.

Run by hand to see what's new:  python3 news_watch.py --no-notify --dry-run
"""
import hashlib
import hmac
import html
import json
import os
import re
import subprocess
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

REPO = os.path.dirname(os.path.abspath(__file__))
SEEN_PATH = os.path.join(REPO, "job", "news-seen.json")
CRED_PATH = os.path.expanduser("~/.config/presence-tracker/altmetric.json")
ALERT_PATH = os.path.expanduser("~/.config/presence-tracker/news-alert.json")
NEWS_PATH = os.path.join(REPO, "news.json")
DEFAULT_RESEARCHER = "ur.015772061677.94"

# English-language outlets worth a look, matched case-insensitively against Altmetric's outlet names
NOTABLE = {
    "washington post", "the new york times", "new york times", "the wall street journal", "wall street journal",
    "the guardian", "bbc news", "cnn news", "npr", "time magazine", "newsweek", "the atlantic", "the economist",
    "reuters", "ap news", "associated press", "usa today", "los angeles times", "the boston globe", "bloomberg",
    "financial times", "cbs news", "nbc news", "abc news", "today", "fox news", "the hill", "axios", "vox.com",
    "wired", "stat", "scientific american", "science", "nature", "new scientist", "national geographic",
    "popular science", "discover magazine", "smithsonian magazine", "the conversation", "forbes", "healthline",
    "medical news today", "verywell health", "everyday health", "aarp", "prevention", "men's health",
    "women's health", "psychology today", "the globe and mail", "sydney morning herald", "the irish times",
    "the independent",
}


# Google Alert stories can go into Features only from these sites. Stanford sites also host profiles and
# directories, so most of them count only on their news pages.
STANFORD_NEWS = {
    "stanfordmag.org": ("Stanford Magazine", None),
    "news.stanford.edu": ("Stanford Report", None),
    "stanmed.stanford.edu": ("Stanford Medicine", None),
    "stanforddaily.com": ("The Stanford Daily", None),
    "med.stanford.edu": ("Stanford Medicine", r"^/news/"),
    "engineering.stanford.edu": ("Stanford Engineering", r"^/(news|spotlight|magazine)/"),
    "bioengineering.stanford.edu": ("Stanford Bioengineering", r"^/news/"),
    "humanperformance.stanford.edu": ("Wu Tsai Human Performance Alliance", r"^/news/"),
    "neuroscience.stanford.edu": ("Wu Tsai Neurosciences Institute", r"^/news/"),
}
PRESS = {
    "washingtonpost.com": "Washington Post", "nytimes.com": "The New York Times", "wsj.com": "The Wall Street Journal",
    "theguardian.com": "The Guardian", "bbc.com": "BBC News", "bbc.co.uk": "BBC News", "cnn.com": "CNN", "npr.org": "NPR",
    "time.com": "TIME", "newsweek.com": "Newsweek", "theatlantic.com": "The Atlantic", "reuters.com": "Reuters",
    "apnews.com": "AP News", "usatoday.com": "USA Today", "latimes.com": "Los Angeles Times",
    "bostonglobe.com": "The Boston Globe", "bloomberg.com": "Bloomberg", "cbsnews.com": "CBS News",
    "nbcnews.com": "NBC News", "abcnews.go.com": "ABC News", "today.com": "TODAY", "foxnews.com": "Fox News",
    "thehill.com": "The Hill", "axios.com": "Axios", "vox.com": "Vox", "wired.com": "Wired", "statnews.com": "STAT",
    "scientificamerican.com": "Scientific American", "newscientist.com": "New Scientist",
    "nationalgeographic.com": "National Geographic", "popsci.com": "Popular Science",
    "discovermagazine.com": "Discover", "smithsonianmag.com": "Smithsonian Magazine",
    "theconversation.com": "The Conversation", "forbes.com": "Forbes", "healthline.com": "Healthline",
    "medicalnewstoday.com": "Medical News Today", "verywellhealth.com": "Verywell Health",
    "everydayhealth.com": "Everyday Health", "aarp.org": "AARP", "theglobeandmail.com": "The Globe and Mail",
    "smh.com.au": "Sydney Morning Herald", "irishtimes.com": "The Irish Times", "independent.co.uk": "The Independent",
}
NOT_STORIES = re.compile(r"/(people|person|profiles?|directory|faculty|staff|students|events?|calendar|publications?|team)(/|$)", re.I)


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


def latin_script(title):
    # Some outlets share one name across editions (Women's Health Japan), so skip headlines in other scripts
    return not any(c.isalpha() and ord(c) > 0x24F for c in title)


def outlet_for(url):
    """The outlet name if a story at this address may go straight into Features, otherwise None."""
    parts = urllib.parse.urlparse(url)
    host = (parts.hostname or "").lower()
    host = host[4:] if host.startswith("www.") else host
    if host in STANFORD_NEWS:
        name, path_rule = STANFORD_NEWS[host]
        if NOT_STORIES.search(parts.path) or (path_rule and not re.search(path_rule, parts.path)):
            return None
        return name
    for domain, name in PRESS.items():
        if host == domain or host.endswith("." + domain):
            return name
    return None


def alert_entries(feed):
    """Entries of a Google Alerts Atom feed, as dicts with id, title, url, date and text."""
    ns = {"a": "http://www.w3.org/2005/Atom"}
    plain = lambda s: re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", s or ""))).strip()
    out = []
    for e in ET.fromstring(feed).findall("a:entry", ns):
        link = (e.find("a:link", ns).get("href") if e.find("a:link", ns) is not None else "") or ""
        # Alerts wrap each link in a google.com redirect; the story's own address is its url parameter
        real = urllib.parse.parse_qs(urllib.parse.urlparse(link).query).get("url", [link])[0]
        out.append({"id": (e.findtext("a:id", "", ns) or real).strip(), "title": plain(e.findtext("a:title", "", ns)),
                    "url": real, "date": (e.findtext("a:published", "", ns) or "")[:10],
                    "text": plain(e.findtext("a:content", "", ns))})
    return out


def write_news(news):
    """news.json in its usual layout: one line per story and per paper."""
    line = lambda d: "{ " + ", ".join(f"{json.dumps(k)}: {json.dumps(v, ensure_ascii=False)}" for k, v in d.items()) + " }"
    groups = []
    for g in news["groups"]:
        fields = []
        for k, v in g.items():
            if k == "stories":
                fields.append('      "stories": [\n' + ",\n".join("        " + line(s) for s in v) + "\n      ]")
            elif k == "paper":
                fields.append('      "paper": ' + line(v))
            else:
                fields.append(f"      {json.dumps(k)}: {json.dumps(v, ensure_ascii=False)}")
        groups.append("    {\n" + ",\n".join(fields) + "\n    }")
    with open(NEWS_PATH, "w", encoding="utf-8") as f:
        f.write('{\n  "groups": [\n' + ",\n".join(groups) + "\n  ]\n}\n")


def add_alert_stories(seen, dry_run, quiet):
    """Add qualifying Google Alert stories to Features in news.json. Returns the stories added."""
    if not os.path.exists(ALERT_PATH):
        return []
    source = json.load(open(ALERT_PATH))["feed"]
    feed = open(source, "rb").read() if os.path.exists(source) else urllib.request.urlopen(source, timeout=60).read()
    news = json.load(open(NEWS_PATH, encoding="utf-8"))
    listed = {s["url"].rstrip("/") for g in news["groups"] for s in g["stories"]}
    seen_alerts = set(seen.get("alerts", []))
    features = next((g for g in news["groups"] if "Features" in (g.get("section"), g.get("label"))), None)
    added = []
    for e in alert_entries(feed):
        if e["id"] in seen_alerts:
            continue
        seen_alerts.add(e["id"])
        outlet = outlet_for(e["url"])
        reason = ("doesn't name Lara Weed" if "lara weed" not in (e["title"] + " " + e["text"]).lower()
                  else "not in English" if not latin_script(e["title"])
                  else "already listed" if e["url"].rstrip("/") in listed
                  else "not a Stanford news site or a well-known outlet" if not outlet
                  else None)
        if reason:
            print(f"  Alert skipped ({reason}): {e['title'][:90]}  {e['url']}")
            continue
        story = {"outlet": outlet, "title": e["title"], "date": e["date"], "url": e["url"]}
        added.append(story)
        listed.add(e["url"].rstrip("/"))
        print(f"  Alert {'would add' if dry_run else 'added'} to Features: {outlet}, {e['title']}  {e['url']}")
    if added and not dry_run:
        if features is None:
            features = {"section": "Features", "label": "Features", "stories": []}
            news["groups"].insert(1, features)
        features["stories"][0:0] = added  # newest first
        write_news(news)
    if not dry_run:
        seen["alerts"] = sorted(seen_alerts)
    if added and not dry_run and not quiet:
        first = added[0]
        notify(f"Added to In the news: {first['title'][:80]} ({first['outlet']})"
               + (f" and {len(added) - 1} more" if len(added) > 1 else "")
               + ". If it isn't right, delete it from news.json.")
    return added


def notify(message):
    subprocess.run(["osascript", "-e", "on run argv", "-e",
                    'display notification (item 1 of argv) with title "New press coverage"', "-e", "end run", message],
                   check=False)


def altmetric_watch(seen, quiet):
    """List and notify new news mentions of her papers from Altmetric. Updates seen in place."""
    creds = json.load(open(CRED_PATH))
    papers = her_papers()
    mentions = news_mentions(creds["explorer_key"], creds["explorer_secret"], creds.get("researcher_id", DEFAULT_RESEARCHER))

    first_run = not seen.get("mentions")
    seen_ids, covered = set(seen.get("mentions", [])), set(seen.get("papers", []))

    new = [m for m in mentions if m["id"] not in seen_ids]
    worth = []
    for m in new:
        mine = [p for p in m["outputs"] if p in papers]
        if not mine:
            continue
        first_story = [p for p in mine if p not in covered]
        if (m["outlet"].lower() in NOTABLE and latin_script(m["title"])) or first_story:
            worth.append((m, papers[mine[0]], bool(first_story)))
        covered.update(mine)
    seen["mentions"] = sorted(seen_ids | {m["id"] for m in mentions})
    seen["papers"] = sorted(covered)

    if first_run:
        print(f"News watch: started with {len(mentions)} stories already seen.")
        return
    print(f"News watch: {len(new)} new {'story' if len(new) == 1 else 'stories'}, {len(worth)} worth a look.")
    for m, paper, first in worth:
        print(f"  {m['date']} {m['outlet']}{' (first story for this paper)' if first else ''}: {m['title']}")
        print(f"      {paper[:90]}")
        print(f"      {m['url']}")
    if worth and not quiet:
        outlets = sorted({m["outlet"] for m, _, _ in worth})
        notify(f"{len(worth)} new {'story' if len(worth) == 1 else 'stories'} about your work, including "
               f"{', '.join(outlets[:3])}. Details in ~/Library/Logs/laraweed-metrics.log.")


def main():
    quiet, dry_run = "--no-notify" in sys.argv, "--dry-run" in sys.argv
    seen = json.load(open(SEEN_PATH)) if os.path.exists(SEEN_PATH) else {}
    for name, check in (("Altmetric", lambda: altmetric_watch(seen, quiet)),
                        ("Google Alert", lambda: add_alert_stories(seen, dry_run, quiet))):
        try:
            check()
        except Exception as error:  # one source failing shouldn't stop the other
            print(f"News watch: {name} check skipped ({error}).")
    if not dry_run:
        with open(SEEN_PATH, "w", encoding="utf-8") as f:
            json.dump(seen, f)


if __name__ == "__main__":
    main()
