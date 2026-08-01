"""
Build the content-based model: TF-IDF over title+authors+genres+description
for every book in MySQL, saved to backend/models/ for the API to load.

Run this once after import_books.py, and again whenever `books` changes:
    cd backend/scripts
    python build_content_model.py
"""
import json
import pickle
import re
import sys
from pathlib import Path

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from db import db_cursor
from config import Config


def parse_json_list(val):
    if not val:
        return []
    try:
        return json.loads(val)
    except (ValueError, TypeError):
        return []


def build_content_field(row):
    authors = " ".join(parse_json_list(row["authors"]))
    genres = " ".join(parse_json_list(row["genres"]))
    description = row["description"] or ""
    title = row["title"] or ""
    # authors + genres weighted x2: they're short, high-signal fields that
    # would otherwise be drowned out by the much longer description text.
    return f"{title} {authors} {authors} {genres} {genres} {description}"


def main():
    print("Loading books from MySQL ...")
    with db_cursor() as cur:
        cur.execute("SELECT book_id, title, authors, genres, description FROM books ORDER BY book_id")
        rows = cur.fetchall()
    print(f"  {len(rows)} books")

    book_ids = [r["book_id"] for r in rows]
    content = [build_content_field(r) for r in rows]

    print("Fitting TF-IDF vectorizer ...")
    vectorizer = TfidfVectorizer(
        lowercase=True,
        stop_words="english",
        token_pattern=r"[a-zA-Z0-9]{2,}",
        max_features=30000,
        min_df=2,
    )
    tfidf_matrix = vectorizer.fit_transform(content)
    print(f"  TF-IDF matrix: {tfidf_matrix.shape}, nnz={tfidf_matrix.nnz}")

    Config.MODELS_DIR.mkdir(parents=True, exist_ok=True)
    with open(Config.MODELS_DIR / "tfidf_vectorizer.pkl", "wb") as f:
        pickle.dump(vectorizer, f)
    with open(Config.MODELS_DIR / "content_matrix.pkl", "wb") as f:
        pickle.dump({"book_ids": book_ids, "matrix": tfidf_matrix}, f)

    print(f"Saved tfidf_vectorizer.pkl and content_matrix.pkl to {Config.MODELS_DIR}")


if __name__ == "__main__":
    main()
