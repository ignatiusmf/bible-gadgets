#!/usr/bin/env python3
"""
CLI for Bible Scraper - Scrapes verses from BibleHub using parallel requests.

Usage:
    python -m bible_scraper                    # Scrape entire Bible
    python -m bible_scraper --book genesis     # Scrape single book
    python -m bible_scraper --workers 20       # Use 20 parallel workers
"""

import argparse
import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Optional

from .scraper import scrape_verse, BIBLE_BOOKS


# =============================================================================
# Configuration
# =============================================================================

BIBLE_STRUCTURE_FILE = "bible_structure.json"
OUTPUT_DIR = "bible"
DEFAULT_WORKERS = 10


# =============================================================================
# Thread-Safe Chapter Writer
# =============================================================================

class ChapterWriter:
    """Thread-safe writer that saves verses to chapter JSON files."""

    def __init__(self, output_dir: str = OUTPUT_DIR):
        self.output_dir = Path(output_dir)
        self.locks: dict[str, threading.Lock] = {}
        self.global_lock = threading.Lock()
        self.chapter_data: dict[str, dict[int, dict]] = {}

    def _get_lock(self, file_path: str) -> threading.Lock:
        """Get or create a lock for a specific file."""
        with self.global_lock:
            if file_path not in self.locks:
                self.locks[file_path] = threading.Lock()
            return self.locks[file_path]

    def _get_chapter_path(self, book: str, chapter: int) -> Path:
        """Get the path for a chapter file."""
        return self.output_dir / book / f"{chapter}.json"

    def init_chapter(self, book: str, chapter: int, total_verses: int):
        """Initialize a chapter - load existing data if file exists."""
        chapter_path = self._get_chapter_path(book, chapter)
        lock = self._get_lock(str(chapter_path))
        key = f"{book}/{chapter}"

        with lock:
            chapter_path.parent.mkdir(parents=True, exist_ok=True)

            if key not in self.chapter_data:
                self.chapter_data[key] = {}

            if chapter_path.exists():
                try:
                    with open(chapter_path, "r", encoding="utf-8") as f:
                        existing = json.load(f)
                    for verse_dict in existing.get("verses", []):
                        verse_num = verse_dict.get("verse")
                        if verse_num:
                            self.chapter_data[key][verse_num] = verse_dict
                except (json.JSONDecodeError, KeyError):
                    pass

    def is_verse_written(self, book: str, chapter: int, verse: int) -> bool:
        """Check if a verse has already been written."""
        key = f"{book}/{chapter}"
        with self.global_lock:
            return verse in self.chapter_data.get(key, {})

    def write_verse(self, book: str, chapter: int, verse_data):
        """Add a verse and save the entire chapter to JSON."""
        chapter_path = self._get_chapter_path(book, chapter)
        lock = self._get_lock(str(chapter_path))
        key = f"{book}/{chapter}"

        with lock:
            if key not in self.chapter_data:
                self.chapter_data[key] = {}
            self.chapter_data[key][verse_data.verse] = verse_data.to_dict()

            sorted_verses = [
                self.chapter_data[key][v]
                for v in sorted(self.chapter_data[key].keys())
            ]

            chapter_json = {
                "book": book,
                "chapter": chapter,
                "verses": sorted_verses
            }

            with open(chapter_path, "w", encoding="utf-8") as f:
                json.dump(chapter_json, f, indent=2, ensure_ascii=False)


# =============================================================================
# Progress Tracking
# =============================================================================

class ProgressTracker:
    """Track and display scraping progress."""

    def __init__(self, total_verses: int):
        self.total = total_verses
        self.completed = 0
        self.failed = 0
        self.lock = threading.Lock()
        self.start_time = time.time()

    def update(self, success: bool = True):
        with self.lock:
            if success:
                self.completed += 1
            else:
                self.failed += 1

    def get_stats(self) -> dict:
        with self.lock:
            elapsed = time.time() - self.start_time
            rate = self.completed / elapsed if elapsed > 0 else 0
            remaining = (self.total - self.completed - self.failed) / rate if rate > 0 else 0
            return {
                "completed": self.completed,
                "failed": self.failed,
                "total": self.total,
                "elapsed": elapsed,
                "rate": rate,
                "remaining": remaining,
            }

    def print_progress(self, current_verse: str = ""):
        stats = self.get_stats()
        pct = (stats["completed"] + stats["failed"]) / stats["total"] * 100
        elapsed_str = time.strftime("%H:%M:%S", time.gmtime(stats["elapsed"]))
        remaining_str = time.strftime("%H:%M:%S", time.gmtime(stats["remaining"]))

        print(
            f"\r[{stats['completed']:,}/{stats['total']:,}] "
            f"{pct:.1f}% | "
            f"⏱ {elapsed_str} elapsed | "
            f"~{remaining_str} remaining | "
            f"📖 {current_verse:<30}",
            end="",
            flush=True
        )


# =============================================================================
# Scraping Logic
# =============================================================================

def load_bible_structure(path: str = BIBLE_STRUCTURE_FILE) -> dict[str, list[int]]:
    """Load the Bible structure (book -> list of verse counts per chapter)."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def generate_verse_tasks(
    structure: dict[str, list[int]],
    books: Optional[list[str]] = None
) -> list[tuple[str, int, int]]:
    """Generate list of (book, chapter, verse) tuples to scrape."""
    tasks = []

    for book, chapters in structure.items():
        if books and book not in books:
            continue

        for chapter_idx, verse_count in enumerate(chapters):
            chapter = chapter_idx + 1
            for verse in range(1, verse_count + 1):
                tasks.append((book, chapter, verse))

    return tasks


def scrape_verse_task(
    book: str,
    chapter: int,
    verse: int,
    writer: ChapterWriter,
    progress: ProgressTracker,
) -> bool:
    """Scrape a single verse and write to file. Returns success status."""
    try:
        verse_data = scrape_verse(book, chapter, verse)

        if verse_data:
            writer.write_verse(book, chapter, verse_data)
            progress.update(success=True)
            progress.print_progress(f"{book.replace('_', ' ').title()} {chapter}:{verse}")
            return True
        else:
            progress.update(success=False)
            return False

    except Exception as e:
        progress.update(success=False)
        print(f"\n❌ Error scraping {book} {chapter}:{verse}: {e}")
        return False


def scrape_bible(
    books: Optional[list[str]] = None,
    max_workers: int = DEFAULT_WORKERS,
    output_dir: str = OUTPUT_DIR,
):
    """
    Scrape the Bible using parallel requests.

    Args:
        books: List of books to scrape (None = all)
        max_workers: Number of parallel workers
        output_dir: Output directory for JSON files
    """
    print("📖 Bible Scraper")
    print("=" * 60)

    print("Loading Bible structure...")
    structure = load_bible_structure()

    all_tasks = generate_verse_tasks(structure, books)
    total_verses = len(all_tasks)

    print(f"Total verses to scrape: {total_verses:,}")
    print(f"Workers: {max_workers}")
    print(f"Output: {output_dir}/")
    print("=" * 60)

    writer = ChapterWriter(output_dir)
    progress = ProgressTracker(total_verses)

    print("Initializing chapter files...")
    for book, chapters in structure.items():
        if books and book not in books:
            continue
        for chapter_idx, verse_count in enumerate(chapters):
            writer.init_chapter(book, chapter_idx + 1, verse_count)

    tasks_to_run = [
        (book, chapter, verse)
        for book, chapter, verse in all_tasks
        if not writer.is_verse_written(book, chapter, verse)
    ]

    skipped = total_verses - len(tasks_to_run)
    if skipped > 0:
        print(f"Skipping {skipped:,} already-scraped verses")
        progress.completed = skipped

    print(f"Verses remaining: {len(tasks_to_run):,}")
    print("=" * 60)
    print("Starting scrape...\n")

    start_time = time.time()

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(
                scrape_verse_task,
                book, chapter, verse,
                writer, progress
            ): (book, chapter, verse)
            for book, chapter, verse in tasks_to_run
        }

        for future in as_completed(futures):
            try:
                future.result()
            except Exception as e:
                book, chapter, verse = futures[future]
                print(f"\n❌ Exception for {book} {chapter}:{verse}: {e}")

    elapsed = time.time() - start_time
    stats = progress.get_stats()

    print("\n")
    print("=" * 60)
    print("✅ Scraping complete!")
    print(f"   Verses scraped: {stats['completed']:,}")
    print(f"   Failed: {stats['failed']:,}")
    print(f"   Time: {time.strftime('%H:%M:%S', time.gmtime(elapsed))}")
    print(f"   Rate: {stats['rate']:.1f} verses/sec")
    print(f"   Output: {output_dir}/")
    print("=" * 60)


# =============================================================================
# CLI Entry Point
# =============================================================================

def main():
    print("YEET")
    parser = argparse.ArgumentParser(
        description="Scrape Bible verses from BibleHub to JSON files."
    )
    parser.add_argument(
        "--book", "-b",
        type=str,
        help="Scrape only this book (e.g., 'genesis', '1_peter')"
    )
    parser.add_argument(
        "--workers", "-w",
        type=int,
        default=DEFAULT_WORKERS,
        help=f"Number of parallel workers (default: {DEFAULT_WORKERS})"
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        default=OUTPUT_DIR,
        help=f"Output directory (default: {OUTPUT_DIR})"
    )

    args = parser.parse_args()

    books = [args.book] if args.book else None

    if args.book and args.book not in BIBLE_BOOKS:
        print(f"❌ Unknown book: {args.book}")
        print(f"   Valid books: {', '.join(BIBLE_BOOKS[:5])}...")
        return 1

    scrape_bible(
        books=books,
        max_workers=args.workers,
        output_dir=args.output,
    )

    return 0


if __name__ == "__main__":
    exit(main())
