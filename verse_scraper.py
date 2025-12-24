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
class OriginalWord:
    """Represents an original language word (Hebrew or Greek) with its Strong's number and definition."""
    english_word: str  # The English word/phrase this word translates to
    word: str  # Hebrew or Greek word
    transliteration: str  # Romanized form
    strongs_number: str  # Strong's reference number
    part_of_speech: str  # e.g., "Noun - Nominative Masculine Singular"
    definition: str  # English definition/meaning
    language: str  # "hebrew" or "greek"


# Keep GreekWord as alias for backward compatibility
GreekWord = OriginalWord


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
    original_words: list[OriginalWord] = field(default_factory=list)  # Hebrew (OT) or Greek (NT)
    cross_references: list[CrossReference] = field(default_factory=list)

    # Backward compatibility property
    @property
    def greek_words(self) -> list[OriginalWord]:
        """Deprecated: use original_words instead."""
        return self.original_words

    def to_dict(self):
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)


# =============================================================================
# Target translations to extract
# =============================================================================

TARGET_VERSIONS = {"NIV", "NLT", "ESV", "NKJV"}
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


def extract_original_words(soup: BeautifulSoup) -> list[OriginalWord]:
    """Extract original language (Hebrew or Greek) lexicon information from the page."""
    original_words = []

    # Find the lexicon section by its heading - could be "Hebrew" or "Greek"
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

    # Get the parent container and find all word entries
    # Each entry has: span.word (English), span.heb/grk (original), span.translit, span.parse, span.str (Strong's), span.str2 (definition)
    parent = lexicon_heading.parent
    if not parent:
        return original_words

    # Determine the class for original language text
    original_class = "heb" if language == "hebrew" else "grk"

    # Find all English word spans - these mark the start of each entry
    word_spans = parent.find_all("span", class_="word")

    for word_span in word_spans:
        english_word = word_span.get_text(strip=True)

        # Find the original language word (next span with class 'heb' or 'grk')
        original_span = word_span.find_next("span", class_=original_class)
        original_word = ""
        if original_span:
            original_word = original_span.get_text(strip=True)

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


# Keep old function name for backward compatibility
def extract_greek_words(soup: BeautifulSoup) -> list[OriginalWord]:
    """Extract Greek lexicon information from the page. Deprecated: use extract_original_words instead."""
    return extract_original_words(soup)

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
    match = re.search(r'/([a-z0-9_]+)/(\d+)-(\d+)\.htm', url.lower())
    if not match:
        return ("", "", 0, 0)

    book_slug = match.group(1)

    chapter = int(match.group(2))
    verse = int(match.group(3))
    book = book_slug.replace("_", " ").title()

    reference = f"{book} {chapter}:{verse}"

    return (reference, book, chapter, verse)

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
        original_words = extract_original_words(soup)
        cross_refs = extract_cross_references(soup)

        return VerseData(
            reference=reference,
            book=book_name,
            chapter=chapter,
            verse=verse,
            translations=translations,
            original_words=original_words,
            cross_references=cross_refs
        )
    except requests.RequestException:
        return None


def scrape_chapter(book: str, chapter: int, callback=None) -> list[VerseData]:
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
    all_verses = []
    chapter_num = 1
    
    while True:
        chapter_verses = scrape_chapter(book, chapter_num, callback)
        if not chapter_verses:
            break
        
        all_verses.extend(chapter_verses)
        chapter_num += 1
    
    return all_verses

