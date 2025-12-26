"""
Bible Scraper - Scrapes verses from BibleHub with translations, original languages, and cross-references.
"""

from .models import OriginalWord, Translation, CrossReference, VerseData
from .scraper import scrape_verse, scrape_chapter, scrape_book, TARGET_VERSIONS, BIBLE_BOOKS

# Backward compatibility
GreekWord = OriginalWord

__all__ = [
    "OriginalWord",
    "GreekWord",
    "Translation",
    "CrossReference",
    "VerseData",
    "scrape_verse",
    "scrape_chapter",
    "scrape_book",
    "TARGET_VERSIONS",
    "BIBLE_BOOKS",
]

__version__ = "0.1.0"
