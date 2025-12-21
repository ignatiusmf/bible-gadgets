import json
import re
import requests
from collections import defaultdict
from pathlib import Path

KJV_URL = "https://openbible.com/textfiles/kjv.txt"
TXT_PATH = Path("kjv.txt")
OUT_PATH = Path("bible_structure.json")

LINE_RE = re.compile(r"^(.+?) (\d+):(\d+)\s")

# -------------------------------------------------------------------
# Step 1: download KJV text if not already present
# -------------------------------------------------------------------
if not TXT_PATH.exists():
    print("Downloading kjv.txt...")
    r = requests.get(KJV_URL, timeout=30)
    r.raise_for_status()
    TXT_PATH.write_text(r.text, encoding="utf-8")
else:
    print("kjv.txt already present, skipping download")

# -------------------------------------------------------------------
# Step 2: parse structure
# -------------------------------------------------------------------
structure = defaultdict(lambda: defaultdict(int))

with TXT_PATH.open(encoding="utf-8") as f:
    for line in f:
        m = LINE_RE.match(line)
        if not m:
            continue

        book, chapter, verse = m.groups()
        chapter = int(chapter)
        verse = int(verse)

        structure[book][chapter] = max(structure[book][chapter], verse)

# -------------------------------------------------------------------
# Step 3: normalize names + emit JSON
# -------------------------------------------------------------------
final = {}

for book, chapters in structure.items():
    key = (
        book.lower()
        .replace(" ", "_")
        .replace("song_of_solomon", "songs")
    )

    final[key] = [
        chapters[c] for c in sorted(chapters)
    ]

OUT_PATH.write_text(
    json.dumps(final, indent=2),
    encoding="utf-8"
)

print(f"Wrote {OUT_PATH} ({len(final)} books)")
