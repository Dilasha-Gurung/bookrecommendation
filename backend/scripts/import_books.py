"""
Import books_enriched.csv into the `books` table.

- Preserves book_id exactly (primary key, not re-generated).
- Handles missing values safely.
- Converts authors/genres list-strings -> clean JSON arrays.
- Safe to re-run: uses INSERT ... ON DUPLICATE KEY UPDATE, so re-running
  updates existing rows instead of creating duplicates.

Run:
    cd backend/scripts
    python import_books.py [--csv ../../data/books_enriched.csv]
"""
import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from db import db_cursor
from config import Config
from _common import list_field_to_json, clean_int, clean_float, clean_str

BATCH_SIZE = 1000

UPSERT_SQL = """
INSERT INTO books (
    book_id, isbn, isbn13, title, original_title, authors, authors_2,
    description, genres, publication_year, pages, language_code,
    average_rating, ratings_count, image_url
) VALUES (
    %(book_id)s, %(isbn)s, %(isbn13)s, %(title)s, %(original_title)s,
    %(authors)s, %(authors_2)s, %(description)s, %(genres)s,
    %(publication_year)s, %(pages)s, %(language_code)s,
    %(average_rating)s, %(ratings_count)s, %(image_url)s
)
ON DUPLICATE KEY UPDATE
    isbn = VALUES(isbn), isbn13 = VALUES(isbn13), title = VALUES(title),
    original_title = VALUES(original_title), authors = VALUES(authors),
    authors_2 = VALUES(authors_2), description = VALUES(description),
    genres = VALUES(genres), publication_year = VALUES(publication_year),
    pages = VALUES(pages), language_code = VALUES(language_code),
    average_rating = VALUES(average_rating), ratings_count = VALUES(ratings_count),
    image_url = VALUES(image_url);
"""


def row_to_params(row):
    book_id = clean_int(row.get("book_id"))
    title = clean_str(row.get("title"), 500)
    if book_id is None or not title:
        return None  # skip rows we cannot safely import

    return {
        "book_id": book_id,
        "isbn": clean_str(row.get("isbn"), 20),
        "isbn13": clean_str(row.get("isbn13"), 20),
        "title": title,
        "original_title": clean_str(row.get("original_title"), 500),
        "authors": list_field_to_json(row.get("authors")),
        "authors_2": list_field_to_json(row.get("authors_2")),
        "description": clean_str(row.get("description")),
        "genres": list_field_to_json(row.get("genres")),
        "publication_year": clean_int(row.get("original_publication_year")),
        "pages": clean_int(row.get("pages")),
        "language_code": clean_str(row.get("language_code"), 10),
        "average_rating": clean_float(row.get("average_rating")),
        "ratings_count": clean_int(row.get("ratings_count")),
        "image_url": clean_str(row.get("image_url"), 500),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", default=str(Config.DATA_DIR / "books_enriched.csv"))
    args = parser.parse_args()

    print(f"Reading {args.csv} ...")
    df = pd.read_csv(args.csv)
    print(f"  {len(df)} rows, {df['book_id'].nunique()} unique book_id")

    dup = df['book_id'].duplicated().sum()
    if dup:
        print(f"  WARNING: {dup} duplicate book_id rows in the CSV -- last one wins.")

    missing_title = df['title'].isna().sum()
    missing_desc = df['description'].isna().sum() if 'description' in df else len(df)
    missing_genres = df['genres'].isna().sum() if 'genres' in df else len(df)
    print(f"  missing title: {missing_title}, missing description: {missing_desc}, missing genres: {missing_genres}")

    records = [p for p in (row_to_params(r) for _, r in df.iterrows()) if p is not None]
    skipped = len(df) - len(records)
    print(f"  {len(records)} importable rows ({skipped} skipped: no book_id/title)")

    imported = 0
    with db_cursor(commit=True) as cur:
        for i in range(0, len(records), BATCH_SIZE):
            batch = records[i:i + BATCH_SIZE]
            cur.executemany(UPSERT_SQL, batch)
            imported += len(batch)
            print(f"  upserted {imported}/{len(records)}", end="\r")

    print(f"\nDone. {imported} books imported/updated into `books`.")


if __name__ == "__main__":
    main()
