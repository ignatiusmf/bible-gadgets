# Bible Scraper

Scrape Bible verses from BibleHub with:
- Multiple translations (ESV, NIV, NLT, NKJV)
- Original language lexicon (Hebrew for OT, Greek for NT) with Strong's numbers
- Cross-references with verse text

## Installation

```bash
pip install -e .
```

## Usage

### As a library

```python
from bible_scraper import scrape_verse, scrape_chapter

# Scrape a single verse
verse = scrape_verse("genesis", 1, 1)
print(verse.to_json())

# Access translations
for t in verse.translations:
    print(f"{t.version}: {t.text}")

# Access original language words (Hebrew/Greek)
for word in verse.original_words:
    print(f"{word.english_word} -> {word.word} ({word.language})")
    print(f"  Strong's: {word.strongs_number}")
    print(f"  Definition: {word.definition}")

# Access cross-references
for ref in verse.cross_references:
    print(f"{ref.reference}: {ref.text}")
```

### As a CLI

```bash
# Scrape entire Bible (takes hours)
bible-scraper

# Scrape a single book
bible-scraper --workers 20 --book genesis

# Custom output directory
bible-scraper --output my_bible_data
```

Or run as a module:

```bash
python -m bible_scraper --book philemon
```

## Output Format

Output is saved as JSON files in `bible/{book}/{chapter}.json`:

```json
{
  "book": "genesis",
  "chapter": 1,
  "verses": [
    {
      "reference": "Genesis 1:1",
      "book": "Genesis",
      "chapter": 1,
      "verse": 1,
      "translations": [
        {"version": "ESV", "text": "In the beginning, God created..."},
        {"version": "NIV", "text": "In the beginning God created..."}
      ],
      "original_words": [
        {
          "english_word": "In the beginning",
          "word": "בְּרֵאשִׁית",
          "transliteration": "bə·rê·šîṯ",
          "strongs_number": "7225",
          "part_of_speech": "Preposition-b | Noun - feminine singular",
          "definition": "beginning, chief",
          "language": "hebrew"
        }
      ],
      "cross_references": [
        {"reference": "John 1:1-3", "text": "In the beginning was the Word..."}
      ]
    }
  ]
}
```

## Project Structure

```
bible-gadgets/
├── src/
│   └── bible_scraper/
│       ├── __init__.py      # Package exports
│       ├── __main__.py      # python -m support
│       ├── models.py        # Data classes
│       ├── scraper.py       # Core scraping logic
│       └── cli.py           # CLI tool
├── bible/                   # Output directory
├── bible_structure.json     # Verse counts per chapter
├── pyproject.toml
└── README.md
```

## Ideas

Elastic search kan dalk super useful hier wees. Of iets wat n powerful search offer. Note: Hoe werk obsidian se graphing? My hunch is daar is iets wat ek daar kan leer wat hier implemented kan word.
