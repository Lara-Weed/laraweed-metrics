"""Check news.json before it's published, so a typo can't break the In the news list on Writing & Media.

Run by publish.sh whenever news.json changes. To check by hand: python3 check_news.py
"""
import json
import re
import sys
from pathlib import Path

path = Path(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).with_name("news.json"))

try:
    data = json.loads(path.read_text(encoding="utf-8"))
except json.JSONDecodeError as error:
    sys.exit(f"news.json isn't valid JSON (line {error.lineno}, column {error.colno}): {error.msg}. Not published.")

groups = data.get("groups") if isinstance(data, dict) else None
if not isinstance(groups, list) or not groups:
    sys.exit('news.json should have a "groups" list. Not published.')

problems = []
for i, group in enumerate(groups, 1):
    name = f"Group {i}" + (f" ({group.get('label')})" if isinstance(group, dict) and group.get("label") else "")
    if not isinstance(group, dict):
        problems.append(f"{name} isn't an entry in {{ }}.")
        continue
    if not isinstance(group.get("label"), str) or not group["label"].strip():
        problems.append(f"{name}: label is missing.")
    paper = group.get("paper")
    if paper is not None and not (isinstance(paper, dict) and paper.get("doi") and paper.get("journal")):
        problems.append(f"{name}: paper needs a doi and a journal.")
    stories = group.get("stories")
    if not isinstance(stories, list) or not stories:
        problems.append(f"{name}: stories should be a list with at least one story.")
        continue
    for j, story in enumerate(stories, 1):
        where = f"{name}, story {j}"
        if not isinstance(story, dict):
            problems.append(f"{where} isn't an entry in {{ }}.")
            continue
        for field in ("outlet", "title", "url"):
            if not isinstance(story.get(field), str) or not story[field].strip():
                problems.append(f"{where}: {field} is missing.")
        if not re.fullmatch(r"\d{4}-\d{2}(-\d{2})?", str(story.get("date", ""))):
            problems.append(f'{where}: date should look like "2026-07-16" or "2026-07".')

if problems:
    sys.exit("news.json has problems, so it wasn't published:\n  " + "\n  ".join(problems))

print(f"news.json OK, {sum(len(g['stories']) for g in groups)} stories in {len(groups)} groups.")
