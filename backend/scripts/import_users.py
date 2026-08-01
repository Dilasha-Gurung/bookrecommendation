
"""
Import dataset users from ratings.csv into the users table.

Each unique user_id in ratings.csv becomes a dataset-only
MySQL user for collaborative filtering.

These are NOT real website users.

Run from backend:

    python scripts/import_users.py

Or:

    python scripts/import_users.py --csv ../data/ratings.csv
"""

import argparse
import sys
from pathlib import Path

import bcrypt
import pandas as pd


# Add backend directory to Python path
sys.path.insert(
    0,
    str(Path(__file__).resolve().parent.parent)
)

from db import db_cursor
from config import Config


BATCH_SIZE = 1000


def make_username(dataset_user_id: int) -> str:
    """Create username from dataset user ID."""
    return f"dataset_user_{dataset_user_id:06d}"


def main():

    # ---------------------------------------------------------
    # Read command-line arguments
    # ---------------------------------------------------------

    parser = argparse.ArgumentParser(
        description="Import dataset users from ratings.csv"
    )

    parser.add_argument(
        "--csv",
        default=str(Config.DATA_DIR / "ratings.csv"),
        help="Path to ratings.csv"
    )

    args = parser.parse_args()

    # ---------------------------------------------------------
    # Load user IDs from ratings.csv
    # ---------------------------------------------------------

    print(f"Reading {args.csv} ...")

    df = pd.read_csv(
        args.csv,
        usecols=["user_id"]
    )

    dataset_user_ids = sorted(
        df["user_id"]
        .dropna()
        .unique()
        .tolist()
    )

    print(
        f"  {len(dataset_user_ids)} "
        f"unique dataset user_id values"
    )

    # ---------------------------------------------------------
    # Check users already in MySQL
    # ---------------------------------------------------------

    print("Checking existing dataset users in MySQL ...")

    with db_cursor() as cur:

        cur.execute(
            """
            SELECT dataset_user_id
            FROM users
            WHERE dataset_user_id IS NOT NULL
            """
        )

        already_imported = {
            row["dataset_user_id"]
            for row in cur.fetchall()
        }

    print(
        f"  {len(already_imported)} "
        f"already imported -- will skip those"
    )

    # ---------------------------------------------------------
    # Find users that need to be imported
    # ---------------------------------------------------------

    to_import = [
        uid
        for uid in dataset_user_ids
        if uid not in already_imported
    ]

    print(
        f"  {len(to_import)} "
        f"new dataset users to create"
    )

    if not to_import:
        print("No new users to import.")
        return

    # ---------------------------------------------------------
    # Generate ONE bcrypt hash
    # ---------------------------------------------------------
    #
    # These are dataset-only users.
    #
    # We do NOT need to generate 53,424 different bcrypt
    # hashes because these accounts are not real users.
    #
    # One hash makes the import much faster.
    # ---------------------------------------------------------

    print("Generating dataset-user password hash ...")

    password_hash = bcrypt.hashpw(
        b"dataset-user-not-for-login",
        bcrypt.gensalt()
    ).decode("utf-8")

    print("Password hash generated.")

    # ---------------------------------------------------------
    # Prepare records
    # ---------------------------------------------------------

    print("Preparing user records ...")

    records = []

    for uid in to_import:

        uid = int(uid)

        records.append(
            {
                "dataset_user_id": uid,
                "username": make_username(uid),
                "password_hash": password_hash,
            }
        )

    print(
        f"Prepared {len(records)} user records."
    )

    # ---------------------------------------------------------
    # SQL
    # ---------------------------------------------------------

    INSERT_SQL = """
        INSERT IGNORE INTO users
        (
            dataset_user_id,
            username,
            email,
            password_hash,
            is_dataset_user
        )
        VALUES
        (
            %(dataset_user_id)s,
            %(username)s,
            NULL,
            %(password_hash)s,
            1
        )
    """

    # ---------------------------------------------------------
    # Insert into MySQL
    # ---------------------------------------------------------

    print("Importing users into MySQL ...")

    imported = 0

    with db_cursor(commit=True) as cur:

        for i in range(
            0,
            len(records),
            BATCH_SIZE
        ):

            batch = records[
                i:i + BATCH_SIZE
            ]

            cur.executemany(
                INSERT_SQL,
                batch
            )

            imported += len(batch)

            print(
                f"  inserted {imported}/{len(records)}",
                end="\r"
            )

    print()

    # ---------------------------------------------------------
    # Done
    # ---------------------------------------------------------

    print(
        f"Done. {imported} dataset users created."
    )

    print(
        "These users exist only to provide historical "
        "ratings for collaborative filtering."
    )


if __name__ == "__main__":
    main()
