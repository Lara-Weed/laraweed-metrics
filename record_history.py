"""Keep a dated record of the numbers each run collects, for Lara's own use (never pushed).

Writes these in job/ (which .gitignore keeps out of the repo) and copies them to Upkeep/ in her
Scientific Visibility folder:
  metrics-history.csv         one row per run date: the overall numbers the website shows, and a few more
  metrics-history-papers.csv  one row per paper per run date: citations and attention for each paper
  metrics-history.js          both, for the "Numbers over time" chart in presence-tracker.html
It also copies the run's metrics-data.js to Upkeep/, so the tracker's other panels match the chart.
A second run on the same day replaces that day's rows. Scholar columns are left blank on a day Scholar
couldn't be reached, so a stale number isn't recorded as a new one.
"""
import csv, json, os, re, shutil
from datetime import datetime

REPO = os.path.dirname(os.path.abspath(__file__))
JOB = os.path.join(REPO, "job")
FOLDER = "/Users/lara/Library/CloudStorage/OneDrive-Stanford/Scientific Visibility/Upkeep"

SUMMARY = ["date", "citations", "citations_this_year", "h_index", "i10_index", "papers", "presentations",
           "news_stories", "altmetric_score_sum", "papers_with_attention", "mendeley_readers", "x_posts"]
PAPERS = ["date", "doi", "title", "scholar_cites", "openalex_cites", "altmetric_score", "news_stories",
          "x_posts", "mendeley_readers"]


def load_js(path, var):
    src = open(path, encoding="utf-8").read()
    src = src[src.index(var) + len(var):] if var in src else src[src.index("{"):]
    return json.loads(src.rstrip().rstrip(";"))


def local_day(stamp):
    return datetime.fromisoformat(stamp).astimezone().date().isoformat() if stamp else ""


def norm(title):
    return re.sub(r"[^a-z0-9]", "", (title or "").lower())


def upsert(path, fields, rows, day):
    old = []
    if os.path.exists(path):
        with open(path, newline="", encoding="utf-8") as f:
            old = [r for r in csv.DictReader(f) if r.get("date") != day]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(sorted(old + rows, key=lambda r: r["date"]))


def main():
    m = load_js(os.path.join(JOB, "metrics-data.js"), "window.METRICS = ")
    tracker = load_js(os.path.join(JOB, "tracker-data.js"), "window.TRACKER_DATA = ")
    impact = json.load(open(os.path.join(REPO, "impact.json"), encoding="utf-8"))
    day = local_day(m["fetchedAt"])
    year = int(day[:4])
    sc = m.get("scholar") or {}
    fresh = local_day(sc.get("fetchedAt")) == day
    alt = m.get("altmetric") or {}
    total = lambda key: int(sum(v.get(key) or 0 for v in alt.values()))

    summary = {
        "date": day,
        "citations": sc.get("citations") if fresh else "",
        "citations_this_year": next((y["cites"] for y in sc.get("byYear", []) if y["year"] == year), "") if fresh else "",
        "h_index": sc.get("h") if fresh else "",
        "i10_index": sc.get("i10") if fresh else "",
        "papers": impact.get("papers", ""),
        "presentations": impact.get("conferences", ""),
        "news_stories": impact.get("news", ""),
        "altmetric_score_sum": impact.get("altmetric", ""),
        "papers_with_attention": impact.get("attentionPapers", ""),
        "mendeley_readers": total("mendeley"),
        "x_posts": total("x"),
    }

    scholar_cites = {norm(w["title"]): w.get("cites") for w in sc.get("works", [])} if fresh else {}
    titles = {}
    for a in tracker.get("assets", []):
        doi = re.sub(r"^https?://(dx\.)?doi\.org/", "", a.get("url") or "", flags=re.I).lower()
        if doi:
            titles[doi] = a.get("title", "")
    papers = []
    for doi in sorted(set(titles) | set(m.get("openalex") or {}) | set(alt)):
        a, oa = alt.get(doi) or {}, (m.get("openalex") or {}).get(doi) or {}
        title = titles.get(doi) or a.get("title", "")
        papers.append({"date": day, "doi": doi, "title": title, "scholar_cites": scholar_cites.get(norm(title), ""),
                       "openalex_cites": oa.get("cites", ""), "altmetric_score": a.get("score", ""),
                       "news_stories": a.get("news", ""), "x_posts": a.get("x", ""),
                       "mendeley_readers": a.get("mendeley", "")})

    upsert(os.path.join(JOB, "metrics-history.csv"), SUMMARY, [summary], day)
    upsert(os.path.join(JOB, "metrics-history-papers.csv"), PAPERS, papers, day)
    history = {"updated": m["fetchedAt"], "summary": read_rows("metrics-history.csv"),
               "papers": read_rows("metrics-history-papers.csv")}
    with open(os.path.join(JOB, "metrics-history.js"), "w", encoding="utf-8") as f:
        f.write("/* Numbers over time, written by record_history.py in ~/laraweed-metrics. */\n"
                "window.METRICS_HISTORY = " + json.dumps(history, indent=1, ensure_ascii=False) + ";\n")
    for name in ("metrics-history.csv", "metrics-history-papers.csv", "metrics-history.js", "metrics-data.js"):
        try:
            shutil.copyfile(os.path.join(JOB, name), os.path.join(FOLDER, name))
        except OSError as e:
            print(f"History: couldn't copy {name} to Upkeep ({e}); it's in job/.")
    print(f"History: recorded {day} ({len(papers)} papers).")


def read_rows(name):
    """A history CSV as a list of dicts, with numbers as numbers and blanks as null."""
    def val(v):
        if v in ("", None):
            return None
        try:
            f = float(v)
            return int(f) if f.is_integer() else f
        except ValueError:
            return v
    with open(os.path.join(JOB, name), newline="", encoding="utf-8") as f:
        return [{k: (v if k in ("date", "doi", "title") else val(v)) for k, v in r.items()} for r in csv.DictReader(f)]


if __name__ == "__main__":
    main()
