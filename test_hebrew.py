#!/usr/bin/env python3
"""
Test script to verify Hebrew and Greek extraction works.
"""

import json
from verse_scraper import scrape_verse_safe, extract_original_words
import requests
from bs4 import BeautifulSoup


def test_hebrew_verse():
    """Test scraping an Old Testament verse (Hebrew)."""
    print("\n" + "="*60)
    print("Testing OT verse: Genesis 1:1 (Hebrew)")
    print("="*60)
    
    verse = scrape_verse_safe("genesis", 1, 1)
    
    if verse:
        print(f"Reference: {verse.reference}")
        print(f"Translations: {len(verse.translations)}")
        print(f"Original words: {len(verse.original_words)}")
        print(f"Cross references: {len(verse.cross_references)}")
        
        if verse.original_words:
            print("\nFirst 3 original words:")
            for word in verse.original_words[:3]:
                print(f"  {word.english_word}: {word.word} ({word.transliteration})")
                print(f"    Strong's: {word.strongs_number}, Language: {word.language}")
                print(f"    Definition: {word.definition[:50]}...")
        
        return verse
    else:
        print("ERROR: Failed to scrape verse")
        return None


def test_greek_verse():
    """Test scraping a New Testament verse (Greek)."""
    print("\n" + "="*60)
    print("Testing NT verse: John 1:1 (Greek)")
    print("="*60)
    
    verse = scrape_verse_safe("john", 1, 1)
    
    if verse:
        print(f"Reference: {verse.reference}")
        print(f"Translations: {len(verse.translations)}")
        print(f"Original words: {len(verse.original_words)}")
        print(f"Cross references: {len(verse.cross_references)}")
        
        if verse.original_words:
            print("\nFirst 3 original words:")
            for word in verse.original_words[:3]:
                print(f"  {word.english_word}: {word.word} ({word.transliteration})")
                print(f"    Strong's: {word.strongs_number}, Language: {word.language}")
                print(f"    Definition: {word.definition[:50]}...")
        
        return verse
    else:
        print("ERROR: Failed to scrape verse")
        return None


def test_json_output(verse):
    """Test JSON output format."""
    if not verse:
        return
    
    print("\n" + "="*60)
    print("JSON Output Sample")
    print("="*60)
    
    data = verse.to_dict()
    # Just show first original word
    if data.get('original_words'):
        data['original_words'] = data['original_words'][:1]
    data['translations'] = data['translations'][:1]
    data['cross_references'] = data['cross_references'][:1] if data.get('cross_references') else []
    
    print(json.dumps(data, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    # Test Hebrew (OT)
    hebrew_verse = test_hebrew_verse()
    test_json_output(hebrew_verse)
    
    # Test Greek (NT)
    greek_verse = test_greek_verse()
    test_json_output(greek_verse)
    
    print("\n" + "="*60)
    print("✅ Tests complete!")
    print("="*60)
