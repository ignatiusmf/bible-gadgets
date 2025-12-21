# Reload module to pick up changes
import importlib
import verse_scraper
importlib.reload(verse_scraper)

from verse_scraper import scrape_verse, VerseData
import json

from verse_scraper import BIBLE_BOOKS, scrape_chapter, scrape_book, scrape_bible, scrape_verse_safe
import time



import json
import time
from pathlib import Path

def scrape_with_persistence(output_dir: str = "bible_data"):
    """Scrape the Bible with progress saving to disk."""
    Path(output_dir).mkdir(exist_ok=True)
    
    for book in BIBLE_BOOKS:
        output_file = Path(output_dir) / f"{book}.json"
        
        # Skip if already scraped
        if output_file.exists():
            print(f"Skipping {book} (already exists)")
            continue
        
        print(f"\n📖 Scraping {book}...")
        start = time.time()
        
        verses = scrape_book(book, callback=lambda v: print(f"  {v.reference}"))
        
        # Save to JSON
        with open(output_file, 'w') as f:
            json.dump([v.to_dict() for v in verses], f, indent=2, ensure_ascii=False)
        
        elapsed = time.time() - start
        print(f"✅ {book}: {len(verses)} verses in {elapsed:.1f}s")

# Uncomment to start scraping (this will take HOURS):
scrape_with_persistence()