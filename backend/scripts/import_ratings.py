"""
Import ratings.csv into the `ratings` table.

- Maps ratings.csv `user_id` -> users.dataset_user_id -> users.id
  (does NOT assume ratings.user_id is already a MySQL users.id).
- Maps ratings.csv `book_id` -> books.book_id (already the same ID space).
- Skips/logs rows whose user_id or book_id isn't found (run import_users.py
  and import_books.py first).
- Prevents duplicate (user_id, book_id) via INSERT IGNORE + the table's
  UNIQUE KEY uq_user_book, so it's safe to re-run.
- Streams the CSV in chunks (ratings.csv can be several million rows) and
  commits per chunk so a failure partway through doesn't lose everything.

Run:
    cd backend/scripts
    python import_ratings.py [--csv ../../data/ratings.csv] [--chunksize 20000]

Note on performance: for a one-time bulk load of millions of rows, MySQL's
`LOAD DATA INFILE` is meaningfully faster than executemany() over the wire.
If import feels slow, pre-map user_id -> users.id in pandas, write a
cleaned CSV, and LOAD DATA INFILE it -- ask and this can be scripted too.
"""
import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from db import db_cursor
from config import Config

INSERT_SQL = """
    INSERT IGNORE INTO ratings (user_id, book_id, rating)
    VALUES (%(user_id)s, %(book_id)s, %(rating)s)
"""


def load_lookup_maps():
    with db_cursor() as cur:
        cur.execute("SELECT id, dataset_user_id FROM users WHERE dataset_user_id IS NOT NULL")
        user_map = {row["dataset_user_id"]: row["id"] for row in cur.fetchall()}

        cur.execute("SELECT book_id FROM books")
        valid_books = {row["book_id"] for row in cur.fetchall()}
    return user_map, valid_books


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", default=str(Config.DATA_DIR / "ratings.csv"))
    parser.add_argument("--chunksize", type=int, default=20000)
    args = parser.parse_args()

    print("Loading user_id / book_id lookup maps from MySQL ...")
    user_map, valid_books = load_lookup_maps()
    print(f"  {len(user_map)} dataset users, {len(valid_books)} books known to MySQL")
    if not user_map:
        print("  ERROR: no dataset users found -- run import_users.py first.")
        sys.exit(1)
    if not valid_books:
        print("  ERROR: no books found -- run import_books.py first.")
        sys.exit(1)

    total_seen = 0
    total_inserted = 0
    total_bad_user = 0
    total_bad_book = 0
    total_bad_rating = 0
    seen_pairs = set()
    total_dupe_in_file = 0

    reader = pd.read_csv(args.csv, chunksize=args.chunksize)
    for chunk_num, chunk in enumerate(reader, start=1):
        total_seen += len(chunk)
        records = []
        for row in chunk.itertuples(index=False):
            uid = user_map.get(row.user_id)
            if uid is None:
                total_bad_user += 1
                continue
            if row.book_id not in valid_books:
                total_bad_book += 1
                continue
            try:
                rating = int(row.rating)
            except (ValueError, TypeError):
                total_bad_rating += 1
                continue
            if not (1 <= rating <= 5):
                total_bad_rating += 1
                continue

            pair = (uid, int(row.book_id))
            if pair in seen_pairs:
                total_dupe_in_file += 1
                continue
            seen_pairs.add(pair)

            records.append({"user_id": uid, "book_id": int(row.book_id), "rating": rating})

        if records:
            with db_cursor(commit=True) as cur:
                cur.executemany(INSERT_SQL, records)
                total_inserted += cur.rowcount if cur.rowcount and cur.rowcount > 0 else len(records)

        print(f"  chunk {chunk_num}: seen={total_seen} inserted~={total_inserted} "
              f"bad_user={total_bad_user} bad_book={total_bad_book} bad_rating={total_bad_rating} "
              f"dupes_in_file={total_dupe_in_file}", end="\r")

    print()
    print("Import summary")
    print("---------------")
    print(f"rows seen:            {total_seen}")
    print(f"rows inserted:        ~{total_inserted} (INSERT IGNORE also silently skips pre-existing pairs)")
    print(f"skipped - bad user:   {total_bad_user}")
    print(f"skipped - bad book:   {total_bad_book}")
    print(f"skipped - bad rating: {total_bad_rating}")
    print(f"skipped - dup in CSV: {total_dupe_in_file}")


if __name__ == "__main__":
    main()
