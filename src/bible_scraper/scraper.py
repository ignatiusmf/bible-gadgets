"""Core scraping functionality for BibleHub."""

import re
from typing import Optional

import requests
from bs4 import BeautifulSoup

from .models import OriginalWord, Translation, CrossReference, VerseData


# =============================================================================
# Constants
# =============================================================================

TARGET_VERSIONS = {"NIV", "NLT", "ESV", "NKJV"}

BIBLE_BOOKS = [
    # Old Testament
    "genesis", "exodus", "leviticus", "numbers", "deuteronomy",
    "joshua", "judges", "ruth", "1_samuel", "2_samuel",
    "1_kings", "2_kings", "1_chronicles", "2_chronicles",
    "ezra", "nehemiah", "esther", "job", "psalms", "proverbs",
    "ecclesiastes", "songs", "isaiah", "jeremiah", "lamentations",
    "ezekiel", "daniel", "hosea", "joel", "amos", "obadiah",
    "jonah", "micah", "nahum", "habakkuk", "zephaniah",
    "haggai", "zechariah", "malachi",
    # New Testament
    "matthew", "mark", "luke", "john", "acts",
    "romans", "1_corinthians", "2_corinthians", "galatians",
    "ephesians", "philippians", "colossians",
    "1_thessalonians", "2_thessalonians",
    "1_timothy", "2_timothy", "titus", "philemon",
    "hebrews", "james", "1_peter", "2_peter",
    "1_john", "2_john", "3_john", "jude", "revelation"
]


# =============================================================================
# Extraction Functions
# =============================================================================

def extract_translations(
    soup: BeautifulSoup, target_versions: set[str] = TARGET_VERSIONS
) -> list[Translation]:
    """Extract verse translations from the page."""
    translations = []

    par_div = soup.find("div", id="par")
    if not par_div:
        return translations

    version_spans = par_div.find_all("span", class_="versiontext")

    for span in version_spans:
        link = span.find("a")
        if not link:
            continue

        version_name = link.get_text(strip=True)

        # Map full version names to abbreviations
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
            verse_parts = []
            next_sibling = span.next_sibling

            while next_sibling:
                if hasattr(next_sibling, 'name') and next_sibling.name:
                    tag_classes = next_sibling.get('class', [])

                    if next_sibling.name == 'span' and 'versiontext' in tag_classes:
                        break
                    if next_sibling.name == 'span' and 'p' in tag_classes:
                        break
                    if next_sibling.name == 'div':
                        break
                    if next_sibling.name == 'br':
                        next_sibling = next_sibling.next_sibling
                        continue
                    if next_sibling.name == 'i':
                        verse_parts.append(next_sibling.get_text())
                else:
                    text = str(next_sibling).strip()
                    if text:
                        verse_parts.append(text)

                next_sibling = next_sibling.next_sibling

            verse_text = " ".join(verse_parts).strip()
            verse_text = re.sub(r'\s+', ' ', verse_text)

            if verse_text:
                translations.append(Translation(version=version_abbrev, text=verse_text))

    return translations


def extract_original_words(soup: BeautifulSoup) -> list[OriginalWord]:
    """Extract original language (Hebrew or Greek) lexicon information from the page."""
    original_words = []

    # Find the lexicon section - could be "Hebrew" or "Greek"
    lexicon_heading = None
    language = None
    for h in soup.find_all("div", class_="vheading"):
        heading_text = h.get_text()
        if "Hebrew" in heading_text:
            lexicon_heading = h
            language = "hebrew"
            break
        elif "Greek" in heading_text:
            lexicon_heading = h
            language = "greek"
            break

    if not lexicon_heading or not language:
        return original_words

    parent = lexicon_heading.parent
    if not parent:
        return original_words

    original_class = "heb" if language == "hebrew" else "grk"
    word_spans = parent.find_all("span", class_="word")

    for word_span in word_spans:
        english_word = word_span.get_text(strip=True)

        # Find the original language word
        original_span = word_span.find_next("span", class_=original_class)
        original_word = original_span.get_text(strip=True) if original_span else ""

        # Find the transliteration
        translit_span = word_span.find_next("span", class_="translit")
        transliteration = translit_span.get_text(strip=True).strip("()") if translit_span else ""

        # Find the parse info (part of speech)
        parse_span = word_span.find_next("span", class_="parse")
        part_of_speech = parse_span.get_text(strip=True) if parse_span else ""

        # Find Strong's number
        strongs_number = ""
        str_span = word_span.find_next("span", class_="str")
        if str_span:
            link = str_span.find("a")
            if link:
                href = link.get("href", "")
                match = re.search(r"strongs_(\d+)", href)
                if match:
                    strongs_number = match.group(1)

        # Find definition
        str2_span = word_span.find_next("span", class_="str2")
        definition = str2_span.get_text(strip=True) if str2_span else ""

        if original_word:
            original_words.append(OriginalWord(
                english_word=english_word,
                word=original_word,
                transliteration=transliteration,
                strongs_number=strongs_number,
                part_of_speech=part_of_speech,
                definition=definition,
                language=language
            ))

    return original_words


def extract_cross_references(soup: BeautifulSoup) -> list[CrossReference]:
    """Extract cross-references from the page."""
    cross_refs = []

    crf_div = soup.find("div", id="crf")
    if not crf_div:
        return cross_refs

    crossverse_spans = crf_div.find_all("span", class_="crossverse")

    for cv_span in crossverse_spans:
        link = cv_span.find("a")
        if not link:
            continue

        ref_text = link.get_text(strip=True)
        if not ref_text:
            continue

        # Collect verse text from siblings
        verse_text = ""
        next_elem = cv_span.next_sibling

        while next_elem:
            if hasattr(next_elem, 'name') and next_elem.name is not None:
                if next_elem.name == 'span':
                    classes = next_elem.get('class', [])
                    if 'crossverse' in classes or 'p' in classes:
                        break
                if next_elem.name == 'br':
                    next_elem = next_elem.next_sibling
                    continue
            else:
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
    """Parse a BibleHub URL to extract reference, book, chapter, and verse."""
    match = re.search(r'/([a-z0-9_]+)/(\d+)-(\d+)\.htm', url.lower())
    if not match:
        return ("", "", 0, 0)

    book_slug = match.group(1)
    chapter = int(match.group(2))
    verse = int(match.group(3))
    book = book_slug.replace("_", " ").title()
    reference = f"{book} {chapter}:{verse}"

    return (reference, book, chapter, verse)


# =============================================================================
# Public API
# =============================================================================

def scrape_verse(book: str, chapter: int, verse: int) -> Optional[VerseData]:
    """
    Scrape a single verse from BibleHub.
    
    Args:
        book: Book name (e.g., 'genesis', '1_peter')
        chapter: Chapter number
        verse: Verse number
    
    Returns:
        VerseData if successful, None if verse doesn't exist (404)
    """
    url = f"https://biblehub.com/{book}/{chapter}-{verse}.htm"
    try:
        response = requests.get(url)
        if response.status_code == 404:
            return None
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        reference, book_name, _, _ = parse_verse_reference(url)

        return VerseData(
            reference=reference,
            book=book_name,
            chapter=chapter,
            verse=verse,
            translations=extract_translations(soup),
            original_words=extract_original_words(soup),
            cross_references=extract_cross_references(soup)
        )
    except requests.RequestException:
        return None


def scrape_chapter(book: str, chapter: int, callback=None) -> list[VerseData]:
    """
    Scrape all verses in a chapter.
    
    Args:
        book: Book name
        chapter: Chapter number
        callback: Optional function called with each VerseData
    
    Returns:
        List of VerseData for all verses in the chapter
    """
    verses = []
    verse_num = 1

    while True:
        verse_data = scrape_verse(book, chapter, verse_num)
        if verse_data is None:
            break

        verses.append(verse_data)
        if callback:
            callback(verse_data)
        verse_num += 1

    return verses


def scrape_book(book: str, callback=None) -> list[VerseData]:
    """
    Scrape all verses in a book.
    
    Args:
        book: Book name
        callback: Optional function called with each VerseData
    
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
