"""Rebuild the job's paper list from Zotero "My Publications", the library behind the Publications page.

Rewrites the assets in job/tracker-data.js with one entry per DOI in Zotero, keeping the profile and channels
(Zotero user, ORCID and Google Scholar links) that refresh_metrics.py also reads. If Zotero can't be reached,
the existing list is left as it is.
"""
import json, os, sys, urllib.request

JOB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "job")
PATH = os.path.join(JOB, "tracker-data.js")
VAR = "window.TRACKER_DATA = "

def main():
    src = open(PATH, encoding="utf-8").read()
    data = json.loads(src[src.index(VAR) + len(VAR):].rstrip().rstrip(";"))
    uid = str((data.get("profile") or {}).get("zoteroUserId") or "21802153")
    items, start = [], 0
    try:
        while True:
            req = urllib.request.Request(
                f"https://api.zotero.org/users/{uid}/publications/items?format=json&limit=100&start={start}",
                headers={"User-Agent": "laraweed-metrics/1.0", "Zotero-API-Version": "3"})
            with urllib.request.urlopen(req, timeout=40) as r:
                total = int(r.headers.get("Total-Results", "0"))
                batch = json.load(r)
            items += [it["data"] for it in batch]
            start += len(batch)
            if not batch or start >= total:
                break
    except Exception as e:
        print(f"Zotero: couldn't read My Publications ({e}); keeping the previous paper list.")
        return
    papers = [it for it in items if it.get("itemType") not in ("attachment", "note") and it.get("DOI")]
    data["assets"] = [{"id": "zotero-" + it["key"], "title": it.get("title", ""), "kind": "paper",
                       "url": "https://doi.org/" + it["DOI"].strip()} for it in papers]
    open(PATH, "w", encoding="utf-8").write(VAR + json.dumps(data, indent=1, ensure_ascii=False) + ";\n")
    print(f"Zotero: {len(papers)} papers with DOIs from My Publications.")

if __name__ == "__main__":
    main()
