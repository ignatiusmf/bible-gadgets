"""
Bible Hub Verse Scraper

Scrapes verse data from BibleHub.com including:
- Multiple Bible translations (NIV, NLT, ESV, NKJV)
- Greek lexicon with Strong's numbers
- Cross-references with verse text
"""

import requests
from bs4 import BeautifulSoup
import json
from dataclasses import dataclass, field, asdict
from typing import Optional, Callable
import re


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class GreekWord:
    """Represents a Greek word with its Strong's number and definition."""
    english_word: str  # The English word/phrase this Greek word translates to
    word: str  # Greek word
    transliteration: str  # Romanized form
    strongs_number: str  # Strong's reference number
    part_of_speech: str  # e.g., "Noun - Nominative Masculine Singular"
    definition: str  # English definition/meaning


@dataclass
class Translation:
    """Represents a Bible translation of the verse."""
    version: str  # e.g., "ESV", "NIV"
    text: str  # The verse text in this translation


@dataclass
class CrossReference:
    """Represents a cross-reference to another Bible verse."""
    reference: str  # e.g., "Acts 2:9-11"
    text: str  # The text of the referenced verse


@dataclass
class VerseData:
    """Complete data for a Bible verse from BibleHub."""
    reference: str  # e.g., "1 Peter 1:1"
    book: str
    chapter: int
    verse: int
    translations: list[Translation] = field(default_factory=list)
    greek_words: list[GreekWord] = field(default_factory=list)
    cross_references: list[CrossReference] = field(default_factory=list)

    def to_dict(self):
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)


# =============================================================================
# Target translations to extract
# =============================================================================

TARGET_VERSIONS = {"NIV", "NLT", "ESV", "NKJV"}


# =============================================================================
# Extraction Functions
# =============================================================================

def extract_translations(soup: BeautifulSoup, target_versions: set[str] = TARGET_VERSIONS) -> list[Translation]:
    """Extract verse translations from the page."""
    translations = []

    # Find the parallel translations section (div#par)
    par_div = soup.find("div", id="par")
    if not par_div:
        return translations

    # Find all version text spans
    version_spans = par_div.find_all("span", class_="versiontext")

    for span in version_spans:
        # Get the version name from the link inside the span
        link = span.find("a")
        if not link:
            continue

        version_name = link.get_text(strip=True)

        # Check if this is one of our target versions
        version_abbrev = None
        if "New International Version" in version_name:
            version_abbrev = "NIV"
        elif "New Living Translation" in version_name:
            version_abbrev = "NLT"
        elif "English Standard Version" in version_name:
            version_abbrev = "ESV"
        elif "New King James Version" in version_name:
            version_abbrev = "NKJV"

        if version_abbrev and version_abbrev in target_versions:
            # Collect verse text from siblings until we hit the next version or paragraph break
            verse_parts = []
            next_sibling = span.next_sibling

            while next_sibling:
                if hasattr(next_sibling, 'name') and next_sibling.name:
                    # It's a tag
                    tag_classes = next_sibling.get('class', [])

                    if next_sibling.name == 'span' and 'versiontext' in tag_classes:
                        break  # Next version starts
                    if next_sibling.name == 'span' and 'p' in tag_classes:
                        break  # Paragraph marker - end of verse
                    if next_sibling.name == 'div':
                        break  # New section
                    if next_sibling.name == 'br':
                        next_sibling = next_sibling.next_sibling
                        continue
                    if next_sibling.name == 'i':
                        # Italicized text (often used for added words)
                        verse_parts.append(next_sibling.get_text())
                else:
                    # Text node
                    text = str(next_sibling).strip()
                    if text:
                        verse_parts.append(text)

                next_sibling = next_sibling.next_sibling

            verse_text = " ".join(verse_parts).strip()
            # Clean up multiple spaces
            verse_text = re.sub(r'\s+', ' ', verse_text)

            if verse_text:
                translations.append(Translation(version=version_abbrev, text=verse_text))

    return translations


def extract_greek_words(soup: BeautifulSoup) -> list[GreekWord]:
    """Extract Greek lexicon information from the page."""
    greek_words = []

    # Find the Greek section by its heading
    greek_heading = None
    for h in soup.find_all("div", class_="vheading"):
        if "Greek" in h.get_text():
            greek_heading = h
            break

    if not greek_heading:
        return greek_words

    # Get the parent container and find all Greek word entries
    # Each entry has: span.word (English), span.grk (Greek), span.translit, span.parse, span.str (Strong's), span.str2 (definition)
    parent = greek_heading.parent
    if not parent:
        return greek_words

    # Find all English word spans - these mark the start of each entry
    word_spans = parent.find_all("span", class_="word")

    for word_span in word_spans:
        english_word = word_span.get_text(strip=True)

        # Find the Greek word (next span with class 'grk')
        grk_span = word_span.find_next("span", class_="grk")
        greek_word = ""
        if grk_span:
            greek_word = grk_span.get_text(strip=True)

        # Find the transliteration
        translit_span = word_span.find_next("span", class_="translit")
        transliteration = ""
        if translit_span:
            transliteration = translit_span.get_text(strip=True).strip("()")

        # Find the parse info (part of speech)
        parse_span = word_span.find_next("span", class_="parse")
        part_of_speech = ""
        if parse_span:
            part_of_speech = parse_span.get_text(strip=True)

        # Find Strong's number
        str_span = word_span.find_next("span", class_="str")
        strongs_number = ""
        if str_span:
            link = str_span.find("a")
            if link:
                href = link.get("href", "")
                match = re.search(r"strongs_(\d+)", href)
                if match:
                    strongs_number = match.group(1)

        # Find definition
        str2_span = word_span.find_next("span", class_="str2")
        definition = ""
        if str2_span:
            definition = str2_span.get_text(strip=True)

        if greek_word:
            greek_words.append(GreekWord(
                english_word=english_word,
                word=greek_word,
                transliteration=transliteration,
                strongs_number=strongs_number,
                part_of_speech=part_of_speech,
                definition=definition
            ))

    return greek_words


def extract_cross_references(soup: BeautifulSoup) -> list[CrossReference]:
    """Extract cross-references from the page."""
    cross_refs = []

    # Find the cross-reference section (div#crf)
    crf_div = soup.find("div", id="crf")
    if not crf_div:
        return cross_refs

    # Cross-references are in span.crossverse elements
    crossverse_spans = crf_div.find_all("span", class_="crossverse")

    for cv_span in crossverse_spans:
        # Get the reference from the link inside
        link = cv_span.find("a")
        if not link:
            continue

        ref_text = link.get_text(strip=True)
        if not ref_text:
            continue

        # The verse text comes after the span, typically after a <br> tag
        # Navigate through siblings to collect the text until the next crossverse or paragraph break
        verse_text = ""
        next_elem = cv_span.next_sibling

        while next_elem:
            # Check if it's a Tag (has .name that is not None)
            if hasattr(next_elem, 'name') and next_elem.name is not None:
                # Stop at next crossverse span or paragraph break
                if next_elem.name == 'span':
                    classes = next_elem.get('class', [])
                    if 'crossverse' in classes:
                        break  # Next cross-reference
                    if 'p' in classes:
                        break  # Paragraph break
                # Skip br tags
                if next_elem.name == 'br':
                    next_elem = next_elem.next_sibling
                    continue
            else:
                # NavigableString (text node)
                text = str(next_elem).strip()
                if text:
                    verse_text += text + " "
            next_elem = next_elem.next_sibling

        cross_refs.append(CrossReference(
            reference=ref_text,
            text=verse_text.strip()
        ))

    return cross_refs


# =============================================================================
# URL Parsing
# =============================================================================

def parse_verse_reference(url: str) -> tuple[str, str, int, int]:
    """Parse book, chapter, verse from a BibleHub URL.

    Example: https://biblehub.com/1_peter/1-1.htm -> ("1 Peter 1:1", "1 Peter", 1, 1)
    """
    # Extract book and chapter-verse from URL
    match = re.search(r'/([a-z0-9_]+)/(\d+)-(\d+)\.htm', url.lower())
    if not match:
        return ("", "", 0, 0)

    book_slug = match.group(1)
    chapter = int(match.group(2))
    verse = int(match.group(3))

    # Convert slug to proper book name
    # e.g., "1_peter" -> "1 Peter"
    book = book_slug.replace("_", " ").title()

    # Format reference
    reference = f"{book} {chapter}:{verse}"

    return (reference, book, chapter, verse)


# =============================================================================
# Bible Books (in BibleHub URL format)
# =============================================================================

BIBLE_BOOKS = [
    "genesis", "exodus", "leviticus", "numbers", "deuteronomy",
    "joshua", "judges", "ruth", "1_samuel", "2_samuel",
    "1_kings", "2_kings", "1_chronicles", "2_chronicles",
    "ezra", "nehemiah", "esther", "job", "psalms", "proverbs",
    "ecclesiastes", "songs", "isaiah", "jeremiah", "lamentations",
    "ezekiel", "daniel", "hosea", "joel", "amos", "obadiah",
    "jonah", "micah", "nahum", "habakkuk", "zephaniah",
    "haggai", "zechariah", "malachi",
    "matthew", "mark", "luke", "john", "acts",
    "romans", "1_corinthians", "2_corinthians", "galatians",
    "ephesians", "philippians", "colossians",
    "1_thessalonians", "2_thessalonians",
    "1_timothy", "2_timothy", "titus", "philemon",
    "hebrews", "james", "1_peter", "2_peter",
    "1_john", "2_john", "3_john", "jude", "revelation"
]


# =============================================================================
# Main Scraper Function
# =============================================================================

def verse_exists(book: str, chapter: int, verse: int) -> bool:
    """Check if a verse exists on BibleHub (returns False for 404)."""
    url = f"https://biblehub.com/{book}/{chapter}-{verse}.htm"
    try:
        response = requests.head(url, allow_redirects=True)
        return response.status_code == 200
    except requests.RequestException:
        return False


def scrape_verse_safe(book: str, chapter: int, verse: int) -> Optional[VerseData]:
    """Scrape a verse, returning None if it doesn't exist (404)."""
    url = f"https://biblehub.com/{book}/{chapter}-{verse}.htm"
    try:
        response = requests.get(url)
        if response.status_code == 404:
            return None
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        # Parse the reference
        reference, book_name, _, _ = parse_verse_reference(url)

        # Extract all the data
        translations = extract_translations(soup)
        greek_words = extract_greek_words(soup)
        cross_refs = extract_cross_references(soup)

        return VerseData(
            reference=reference,
            book=book_name,
            chapter=chapter,
            verse=verse,
            translations=translations,
            greek_words=greek_words,
            cross_references=cross_refs
        )
    except requests.RequestException:
        return None


def scrape_chapter(book: str, chapter: int, callback=None) -> list[VerseData]:
    """Scrape all verses in a chapter.
    
    Args:
        book: Book name in BibleHub format (e.g., "1_peter")
        chapter: Chapter number
        callback: Optional function called with (verse_data) after each verse
        
    Returns:
        List of VerseData for all verses in the chapter
    """
    verses = []
    verse_num = 1
    
    while True:
        verse_data = scrape_verse_safe(book, chapter, verse_num)
        if verse_data is None:
            break
        
        verses.append(verse_data)
        if callback:
            callback(verse_data)
        verse_num += 1
    
    return verses


def scrape_book(book: str, callback=None) -> list[VerseData]:
    """Scrape all verses in a book.
    
    Args:
        book: Book name in BibleHub format (e.g., "1_peter")
        callback: Optional function called with (verse_data) after each verse
        
    Returns:
        List of VerseData for all verses in the book
    """
    all_verses = []
    chapter_num = 1
    
    while True:
        chapter_verses = scrape_chapter(book, chapter_num, callback)
        if not chapter_verses:
            break
        
        all_verses.extend(chapter_verses)
        chapter_num += 1
    
    return all_verses


def scrape_bible(books: Optional[list[str]] = None, callback=None, progress_callback=None) -> dict[str, list[VerseData]]:
    """Scrape the entire Bible or a subset of books.
    
    Args:
        books: List of book names in BibleHub format. If None, scrapes all 66 books.
        callback: Optional function called with (verse_data) after each verse
        progress_callback: Optional function called with (book, chapter, verse, total_verses) for progress
        
    Returns:
        Dictionary mapping book names to lists of VerseData
    """
    if books is None:
        books = BIBLE_BOOKS
    
    bible_data = {}
    total_verses = 0
    
    for book in books:
        if progress_callback:
            progress_callback(book, 0, 0, total_verses)
        
        book_verses = scrape_book(book, callback)
        bible_data[book] = book_verses
        total_verses += len(book_verses)
        
        if progress_callback:
            progress_callback(book, -1, -1, total_verses)  # -1 signals book complete
    
    return bible_data


def scrape_verse(url: str) -> VerseData:
    """Scrape all data for a Bible verse from BibleHub.

    Args:
        url: BibleHub verse URL (e.g., "https://biblehub.com/1_peter/1-1.htm")

    Returns:
        VerseData object containing translations, Greek words, and cross-references
    """
    # Fetch the page
    response = requests.get(url)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    # Parse the reference
    reference, book, chapter, verse = parse_verse_reference(url)

    # Extract all the data
    translations = extract_translations(soup)
    greek_words = extract_greek_words(soup)
    cross_refs = extract_cross_references(soup)

    return VerseData(
        reference=reference,
        book=book,
        chapter=chapter,
        verse=verse,
        translations=translations,
        greek_words=greek_words,
        cross_references=cross_refs
    )


# =============================================================================
# CLI Entry Point
# =============================================================================

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        url = sys.argv[1]
    else:
        url = "https://biblehub.com/1_peter/1-1.htm"

    print(f"Scraping: {url}\n")

    verse_data = scrape_verse(url)

    print(f"Reference: {verse_data.reference}")
    print(f"Book: {verse_data.book}, Chapter: {verse_data.chapter}, Verse: {verse_data.verse}")
    print()

    print("=" * 60)
    print("TRANSLATIONS")
    print("=" * 60)
    for t in verse_data.translations:
        print(f"\n[{t.version}]")
        print(t.text)

    print()
    print("=" * 60)
    print("GREEK WORDS")
    print("=" * 60)
    for g in verse_data.greek_words:
        print(f"\n'{g.english_word}' -> {g.word} ({g.transliteration}) - Strong's {g.strongs_number}")
        if g.part_of_speech:
            print(f"  Part of Speech: {g.part_of_speech}")
        if g.definition:
            print(f"  Definition: {g.definition}")

    print()
    print("=" * 60)
    print(f"CROSS REFERENCES ({len(verse_data.cross_references)} total)")
    print("=" * 60)
    for cr in verse_data.cross_references:
        print(f"\n{cr.reference}")
        if cr.text:
            print(f"  {cr.text}")
