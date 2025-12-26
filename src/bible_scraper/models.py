"""Data models for Bible scraping."""

import json
from dataclasses import dataclass, field, asdict


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


# Backward compatibility alias
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
    original_words: list[OriginalWord] = field(default_factory=list)
    cross_references: list[CrossReference] = field(default_factory=list)

    @property
    def greek_words(self) -> list[OriginalWord]:
        """Deprecated: use original_words instead."""
        return self.original_words

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)
