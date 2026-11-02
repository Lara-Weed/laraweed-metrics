"""Check conferences.json before it's published, so a typo can't break the website's conference list.

Run by publish.sh whenever conferences.json changes. To check by hand: python3 check_conferences.py
"""
import json
import sys
from pathlib import Path

path = Path(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).with_name("conferences.json"))

try:
    items = json.loads(path.read_text(encoding="utf-8"))
except json.JSONDecodeError as error:
    sys.exit(f"conferences.json isn't valid JSON (line {error.lineno}, column {error.colno}): {error.msg}. Not published.")

if not isinstance(items, list) or not items:
    sys.exit("conferences.json should be a list of entries in [ ]. Not published.")

problems = []
for i, item in enumerate(items, 1):
    name = f"Entry {i}" + (f" ({item.get('meeting')})" if isinstance(item, dict) and item.get("meeting") else "")
    if not isinstance(item, dict):
        problems.append(f"{name} isn't an entry in {{ }}.")
        continue
    if not isinstance(item.get("year"), int) or not 1990 <= item["year"] <= 2100:
        problems.append(f"{name}: year should be a number like 2026, without quotes.")
    for field in ("title", "authors", "meeting"):
        if not isinstance(item.get(field), str) or not item[field].strip():
            problems.append(f"{name}: {field} is missing.")
    if not isinstance(item.get("place", ""), str):
        problems.append(f"{name}: place should be text in quotes.")
    if item.get("format", "") not in ("Oral", "Poster", ""):
        problems.append(f'{name}: format should be "Oral", "Poster" or "".')

if problems:
    sys.exit("conferences.json has problems, so it wasn't published:\n  " + "\n  ".join(problems))

print(f"conferences.json OK, {len(items)} entries.")
