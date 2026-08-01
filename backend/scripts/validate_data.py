"""
Pre-import validation. Run this before import_books.py / import_ratings.py
to sanity-check the raw CSVs and print a clear summary.

Run:
    cd backend/scripts
    python validate_data.py
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import Config


def main():
    books_csv = Config.DATA_DIR / "books_enriched.csv"
    ratings_csv = Config.DATA_DIR / "ratings.csv"

    print(f"Loading {books_csv} ...")
    books = pd.read_csv(books_csv)
    print(f"Loading {ratings_csv} ...")
    ratings = pd.read_csv(ratings_csv)

    print("\n=== BOOKS ===")
    print("rows:                  ", len(books))
    print("unique book_id:        ", books['book_id'].nunique())
    print("duplicate book_id rows:", books['book_id'].duplicated().sum())
    print("missing title:         ", books['title'].isna().sum())
    print("missing description:   ", books['description'].isna().sum() if 'description' in books else "column missing")
    print("missing genres:        ", books['genres'].isna().sum() if 'genres' in books else "column missing")
    print("missing authors:       ", books['authors'].isna().sum() if 'authors' in books else "column missing")

    print("\n=== RATINGS ===")
    print("rows:                       ", len(ratings))
    print("unique user_id:             ", ratings['user_id'].nunique())
    print("unique book_id:             ", ratings['book_id'].nunique())
    print("missing user_id:            ", ratings['user_id'].isna().sum())
    print("missing book_id:            ", ratings['book_id'].isna().sum())
    print("missing rating:             ", ratings['rating'].isna().sum())
    print("invalid rating (not 1-5):   ", (~ratings['rating'].between(1, 5)).sum())
    print("duplicate (user_id,book_id):", ratings.duplicated(subset=['user_id', 'book_id']).sum())

    print("\n=== CROSS-CHECK ===")
    match_rate = ratings['book_id'].isin(books['book_id']).mean()
    print(f"ratings.book_id found in books.book_id: {match_rate:.4f}")
    if match_rate < 1.0:
        missing_ids = sorted(set(ratings['book_id']) - set(books['book_id']))[:20]
        print(f"  sample of unmatched book_id values: {missing_ids}")
    else:
        print("  100% match -- every rating references a real book.")

    print("\nValidation complete. Review any non-zero counts above before importing.")


if __name__ == "__main__":
    main()
