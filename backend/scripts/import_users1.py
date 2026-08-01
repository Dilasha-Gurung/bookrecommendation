"""
Import dataset users from ratings.csv into the `users` table.

- One MySQL user is created per unique ratings.csv user_id.
- Username: dataset_user_000001 (zero-padded to 6 digits).
- Password: a random 16-byte token, bcrypt-hashed before storage.
  The plaintext is NEVER stored or logged in production mode; pass
  --show-passwords only in local/dev if you want to see them printed
  to a local CSV for testing.
- dataset_user_id stores the original ratings.csv user_id so ratings
  import can map back to it.
- Safe to re-run: existing dataset_user_id rows are skipped (no dupes).

Run:
    cd backend/scripts
    python import_users.py [--csv ../../data/ratings.csv]
"""
import argparse
import csv as csv_module
import secrets
import sys
from pathlib import Path

import bcrypt
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from db import db_cursor
from config import Config

BATCH_SIZE = 1000


def make_username(dataset_user_id: int) -> str:
    return f"dataset_user_{dataset_user_id:06d}"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", default=str(Config.DATA_DIR / "ratings.csv"))
    parser.add_argument(
        "--show-passwords",
        action="store_true",
        help="Also write generated plaintext passwords to a local-only CSV "
             "(scripts/_dataset_user_passwords.LOCAL.csv). Dev/testing only -- "
             "never commit or ship this file.",
    )
    args = parser.parse_args()

    print(f"Reading {args.csv} ...")
    df = pd.read_csv(args.csv, usecols=["user_id"])
    dataset_user_ids = sorted(df["user_id"].dropna().unique().tolist())
    print(f"  {len(dataset_user_ids)} unique dataset user_id values")

    with db_cursor() as cur:
        cur.execute("SELECT dataset_user_id FROM users WHERE dataset_user_id IS NOT NULL")
        already_imported = {row["dataset_user_id"] for row in cur.fetchall()}
    print(f"  {len(already_imported)} already imported -- will skip those")

    to_import = [uid for uid in dataset_user_ids if uid not in already_imported]
    print(f"  {len(to_import)} new dataset users to create")

    plaintext_log = []
    records = []
    for uid in to_import:
        uid = int(uid)
        password = secrets.token_urlsafe(16)
        password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        records.append({
            "dataset_user_id": uid,
            "username": make_username(uid),
            "password_hash": password_hash,
        })
        if args.show_passwords:
            plaintext_log.append((uid, make_username(uid), password))

    INSERT_SQL = """
        INSERT IGNORE INTO users (dataset_user_id, username, email, password_hash, is_dataset_user)
        VALUES (%(dataset_user_id)s, %(username)s, NULL, %(password_hash)s, 1)
    """

    imported = 0
    with db_cursor(commit=True) as cur:
        for i in range(0, len(records), BATCH_SIZE):
            batch = records[i:i + BATCH_SIZE]
            cur.executemany(INSERT_SQL, batch)
            imported += len(batch)
            print(f"  inserted {imported}/{len(records)}", end="\r")

    print(f"\nDone. {imported} dataset users created.")
    print("These are NOT real people -- they exist only to supply historical "
          "ratings for collaborative filtering, and cannot log in with a "
          "known password unless you explicitly reset one.")

    if args.show_passwords and plaintext_log:
        out_path = Path(__file__).resolve().parent / "_dataset_user_passwords.LOCAL.csv"
        with open(out_path, "w", newline="") as f:
            w = csv_module.writer(f)
            w.writerow(["dataset_user_id", "username", "password"])
            w.writerows(plaintext_log)
        print(f"Plaintext passwords (LOCAL/DEV ONLY) written to {out_path}")
        print("Delete this file before deploying or sharing the project.")


if __name__ == "__main__":
    main()
