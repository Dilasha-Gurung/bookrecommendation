# """
# Build the collaborative-filtering model: item-based CF using adjusted
# cosine similarity over the ratings table.

# Why item-based CF for this project:
#   - Explainable: "users who liked book X also liked book Y" is easy to
#     justify in a BCA report and to a non-technical reader.
#   - Item-item similarity is far cheaper to keep fresh than user-user:
#     there are 10,000 books but 50,000+ users, and the book catalog
#     changes much less often than the user base.
#   - At request time we only need the rated books of ONE user (a handful
#     of rows) plus this precomputed similarity table -- no need to hold
#     the full user-item matrix in memory in the API process.

# Method (adjusted cosine similarity):
#   1. Mean-center each book's ratings across the users who rated it
#      (removes the fact that some users rate generously and others
#      harshly -- a plain cosine would conflate "similar taste" with
#      "similar strictness").
#   2. Cosine-similarity the mean-centered item vectors.
#   3. Keep only the top-K neighbors per book (K = Config.TOP_K_NEIGHBORS)
#      so the saved model stays small and lookups stay O(K) instead of
#      O(n_books).

# Also computes a popularity ranking (Bayesian-average rating) used as the
# cold-start fallback when a user has no ratings yet.

# Run this once after import_ratings.py, and again whenever ratings change
# meaningfully:
#     cd backend/scripts
#     python build_collaborative_model.py
# """
# import pickle
# import sys
# from pathlib import Path

# import numpy as np
# import pandas as pd
# from scipy.sparse import csr_matrix

# sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
# from db import db_cursor
# from config import Config


# def main():
#     print("Loading ratings from MySQL ...")
#     with db_cursor() as cur:
#         cur.execute("SELECT user_id, book_id, rating FROM ratings")
#         ratings = pd.DataFrame(cur.fetchall())
#     print(f"  {len(ratings)} ratings, {ratings['user_id'].nunique()} users, {ratings['book_id'].nunique()} books")

#     with db_cursor() as cur:
#         cur.execute("SELECT book_id, average_rating, ratings_count FROM books ORDER BY book_id")
#         books = pd.DataFrame(cur.fetchall())

#     book_ids = books["book_id"].tolist()
#     book_idx = {bid: i for i, bid in enumerate(book_ids)}
#     user_ids = sorted(ratings["user_id"].unique().tolist())
#     user_idx = {uid: i for i, uid in enumerate(user_ids)}

#     ratings = ratings[ratings["book_id"].isin(book_idx)]
#     rows = ratings["book_id"].map(book_idx).values
#     cols = ratings["user_id"].map(user_idx).values
#     vals = ratings["rating"].values.astype(np.float32)

#     n_items, n_users = len(book_ids), len(user_ids)
#     item_user = csr_matrix((vals, (rows, cols)), shape=(n_items, n_users))
#     print(f"  item-user matrix: {item_user.shape}, nnz={item_user.nnz}")

#     # --- mean-center each item (row) over its *rated* entries only ---
#     row_sums = np.asarray(item_user.sum(axis=1)).flatten()
#     row_counts = np.diff(item_user.indptr)
#     row_counts_safe = np.where(row_counts == 0, 1, row_counts)
#     item_means = row_sums / row_counts_safe

#     centered = item_user.tocsr(copy=True).astype(np.float32)
#     for i in range(n_items):
#         start, end = centered.indptr[i], centered.indptr[i + 1]
#         centered.data[start:end] -= item_means[i]

#     row_norms = np.sqrt(np.asarray(centered.multiply(centered).sum(axis=1)).flatten())
#     row_norms_safe = np.where(row_norms == 0, 1.0, row_norms)

#     # --- top-K item-item neighbors via chunked cosine similarity ---
#     K = Config.TOP_K_NEIGHBORS
#     neighbors = {}
#     CHUNK = 500
#     print(f"Computing top-{K} item-item neighbors (adjusted cosine) ...")
#     for start in range(0, n_items, CHUNK):
#         end = min(start + CHUNK, n_items)
#         chunk = centered[start:end]                       # (chunk, n_users)
#         sims = (chunk @ centered.T).toarray()              # (chunk, n_items) dot products
#         chunk_norms = row_norms_safe[start:end][:, None]
#         sims = sims / chunk_norms / row_norms_safe[None, :]
#         for local_i in range(end - start):
#             global_i = start + local_i
#             sims[local_i, global_i] = -np.inf  # exclude self
#             top_idx = np.argpartition(-sims[local_i], K)[:K]
#             top_idx = top_idx[np.argsort(-sims[local_i][top_idx])]
#             neighbors[book_ids[global_i]] = [
#                 (book_ids[j], float(sims[local_i, j])) for j in top_idx if sims[local_i, j] > 0
#             ]
#         print(f"  {end}/{n_items}", end="\r")
#     print()

#     # --- popularity fallback (Bayesian average, for cold start) ---
#     C = books["average_rating"].mean()
#     m = books["ratings_count"].quantile(0.60)  # books need a reasonable vote count to rank highly
#     books["bayesian_score"] = (
#         (books["ratings_count"] / (books["ratings_count"] + m)) * books["average_rating"]
#         + (m / (books["ratings_count"] + m)) * C
#     )
#     popularity_rank = books.sort_values("bayesian_score", ascending=False)["book_id"].tolist()

#     item_mean_rating = {book_ids[i]: float(item_means[i]) for i in range(n_items)}

#     Config.MODELS_DIR.mkdir(parents=True, exist_ok=True)
#     with open(Config.MODELS_DIR / "collaborative_model.pkl", "wb") as f:
#         pickle.dump({
#             "book_ids": book_ids,
#             "neighbors": neighbors,               # book_id -> [(neighbor_book_id, similarity), ...]
#             "item_mean_rating": item_mean_rating,  # book_id -> mean rating among raters
#             "global_mean": float(ratings["rating"].mean()) if len(ratings) else 3.5,
#             "popularity_rank": popularity_rank,    # book_id list, most "popular/well-rated" first
#         }, f)

#     print(f"Saved collaborative_model.pkl to {Config.MODELS_DIR}")


# if __name__ == "__main__":
#     main()




"""
Build the collaborative-filtering model: item-based CF using adjusted
cosine similarity over the ratings table.

Why item-based CF for this project:
  - Explainable: "users who liked book X also liked book Y" is easy to
    justify in a BCA report and to a non-technical reader.
  - Item-item similarity is far cheaper to keep fresh than user-user:
    there are 10,000 books but 50,000+ users, and the book catalog
    changes much less often than the user base.
  - At request time we only need the rated books of ONE user plus this
    precomputed similarity table.

Method (adjusted cosine similarity):
  1. Mean-center each book's ratings across the users who rated it.
  2. Cosine-similarity the mean-centered item vectors.
  3. Keep only the top-K neighbors per book.

Also computes a popularity ranking (Bayesian-average rating) used as the
cold-start fallback when a user has no ratings yet.

Run this once after import_ratings.py, and again whenever ratings change
meaningfully.
"""

import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from db import db_cursor
from config import Config


def main():

    # =========================================================
    # LOAD RATINGS
    # =========================================================

    print("Loading ratings from MySQL ...")

    with db_cursor() as cur:
        cur.execute(
            "SELECT user_id, book_id, rating FROM ratings"
        )
        ratings = pd.DataFrame(cur.fetchall())

    if ratings.empty:
        raise RuntimeError(
            "No ratings found in MySQL. "
            "Run import_ratings.py first."
        )

    print(
        f"  {len(ratings)} ratings, "
        f"{ratings['user_id'].nunique()} users, "
        f"{ratings['book_id'].nunique()} books"
    )

    # Make sure ratings are numeric.
    # MySQL DECIMAL values can otherwise become Decimal objects.
    ratings["rating"] = pd.to_numeric(
        ratings["rating"],
        errors="coerce"
    ).fillna(0).astype(np.float32)

    ratings["user_id"] = pd.to_numeric(
        ratings["user_id"],
        errors="coerce"
    )

    ratings["book_id"] = pd.to_numeric(
        ratings["book_id"],
        errors="coerce"
    )

    ratings = ratings.dropna(
        subset=["user_id", "book_id"]
    )

    ratings["user_id"] = ratings["user_id"].astype(int)
    ratings["book_id"] = ratings["book_id"].astype(int)

    # =========================================================
    # LOAD BOOK INFORMATION
    # =========================================================

    print("Loading books from MySQL ...")

    with db_cursor() as cur:
        cur.execute(
            """
            SELECT book_id, average_rating, ratings_count
            FROM books
            ORDER BY book_id
            """
        )
        books = pd.DataFrame(cur.fetchall())

    if books.empty:
        raise RuntimeError(
            "No books found in MySQL. "
            "Run import_books.py first."
        )

    # ---------------------------------------------------------
    # IMPORTANT FIX:
    #
    # MySQL DECIMAL columns can be returned by mysql-connector /
    # pymysql as decimal.Decimal objects.
    #
    # Pandas cannot safely multiply Decimal and float values.
    #
    # Convert these columns explicitly to float.
    # ---------------------------------------------------------

    books["average_rating"] = pd.to_numeric(
        books["average_rating"],
        errors="coerce"
    ).fillna(0).astype(float)

    books["ratings_count"] = pd.to_numeric(
        books["ratings_count"],
        errors="coerce"
    ).fillna(0).astype(float)

    books["book_id"] = pd.to_numeric(
        books["book_id"],
        errors="coerce"
    )

    books = books.dropna(
        subset=["book_id"]
    )

    books["book_id"] = books["book_id"].astype(int)

    print(f"  {len(books)} books loaded")

    # =========================================================
    # CREATE BOOK / USER INDEXES
    # =========================================================

    book_ids = books["book_id"].tolist()

    book_idx = {
        bid: i
        for i, bid in enumerate(book_ids)
    }

    user_ids = sorted(
        ratings["user_id"].unique().tolist()
    )

    user_idx = {
        uid: i
        for i, uid in enumerate(user_ids)
    }

    # Only keep ratings for books that exist in books table.
    ratings = ratings[
        ratings["book_id"].isin(book_idx)
    ]

    # =========================================================
    # CREATE ITEM-USER SPARSE MATRIX
    # =========================================================

    rows = ratings["book_id"].map(
        book_idx
    ).values

    cols = ratings["user_id"].map(
        user_idx
    ).values

    vals = ratings["rating"].values.astype(
        np.float32
    )

    n_items = len(book_ids)
    n_users = len(user_ids)

    item_user = csr_matrix(
        (vals, (rows, cols)),
        shape=(n_items, n_users)
    )

    print(
        f"  item-user matrix: "
        f"{item_user.shape}, "
        f"nnz={item_user.nnz}"
    )

    # =========================================================
    # MEAN-CENTER EACH ITEM
    # =========================================================

    print("Mean-centering item ratings ...")

    row_sums = np.asarray(
        item_user.sum(axis=1)
    ).flatten()

    row_counts = np.diff(
        item_user.indptr
    )

    row_counts_safe = np.where(
        row_counts == 0,
        1,
        row_counts
    )

    item_means = (
        row_sums /
        row_counts_safe
    )

    centered = item_user.tocsr(
        copy=True
    ).astype(np.float32)

    for i in range(n_items):

        start = centered.indptr[i]
        end = centered.indptr[i + 1]

        centered.data[start:end] -= (
            item_means[i]
        )

    # =========================================================
    # CALCULATE ROW NORMS
    # =========================================================

    row_norms = np.sqrt(
        np.asarray(
            centered.multiply(
                centered
            ).sum(axis=1)
        ).flatten()
    )

    row_norms_safe = np.where(
        row_norms == 0,
        1.0,
        row_norms
    )

    # =========================================================
    # TOP-K ITEM-ITEM NEIGHBORS
    # =========================================================

    K = Config.TOP_K_NEIGHBORS

    neighbors = {}

    CHUNK = 500

    print(
        f"Computing top-{K} item-item "
        f"neighbors (adjusted cosine) ..."
    )

    for start in range(
        0,
        n_items,
        CHUNK
    ):

        end = min(
            start + CHUNK,
            n_items
        )

        chunk = centered[
            start:end
        ]

        # Similarity matrix for this chunk.
        sims = (
            chunk @ centered.T
        ).toarray()

        chunk_norms = (
            row_norms_safe[start:end][:, None]
        )

        sims = (
            sims /
            chunk_norms /
            row_norms_safe[None, :]
        )

        for local_i in range(
            end - start
        ):

            global_i = (
                start + local_i
            )

            # Don't recommend the book itself.
            sims[
                local_i,
                global_i
            ] = -np.inf

            # Find top-K neighbors.
            top_idx = np.argpartition(
                -sims[local_i],
                K
            )[:K]

            # Sort top-K by similarity.
            top_idx = top_idx[
                np.argsort(
                    -sims[
                        local_i
                    ][top_idx]
                )
            ]

            neighbors[
                book_ids[global_i]
            ] = [
                (
                    book_ids[j],
                    float(
                        sims[
                            local_i,
                            j
                        ]
                    )
                )
                for j in top_idx
                if sims[
                    local_i,
                    j
                ] > 0
            ]

        print(
            f"  {end}/{n_items}",
            end="\r"
        )

    print()

    # =========================================================
    # POPULARITY FALLBACK
    # =========================================================
    #
    # Used when a user has no ratings.
    #
    # Bayesian average prevents books with only a few ratings
    # from automatically becoming the most popular.
    # =========================================================

    print(
        "Computing popularity ranking ..."
    )

    # These are now guaranteed to be normal floats,
    # not Decimal objects.

    C = float(
        books["average_rating"].mean()
    )

    m = float(
        books["ratings_count"].quantile(
            0.60
        )
    )

    # Prevent division by zero in case the dataset
    # somehow contains no rating counts.
    denominator = (
        books["ratings_count"] + m
    )

    denominator = denominator.replace(
        0,
        1
    )

    books["bayesian_score"] = (
        (
            books["ratings_count"] /
            denominator
        )
        *
        books["average_rating"]
    ) + (
        (
            m /
            denominator
        )
        *
        C
    )

    popularity_rank = (
        books
        .sort_values(
            "bayesian_score",
            ascending=False
        )["book_id"]
        .tolist()
    )

    # =========================================================
    # ITEM MEAN RATINGS
    # =========================================================

    item_mean_rating = {
        book_ids[i]: float(
            item_means[i]
        )
        for i in range(n_items)
    }

    # =========================================================
    # SAVE MODEL
    # =========================================================

    Config.MODELS_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    model_path = (
        Config.MODELS_DIR /
        "collaborative_model.pkl"
    )

    print(
        f"Saving collaborative model to:"
    )

    print(model_path)

    with open(
        model_path,
        "wb"
    ) as f:

        pickle.dump(
            {
                "book_ids": book_ids,

                # book_id ->
                # [(neighbor_book_id, similarity), ...]
                "neighbors": neighbors,

                # book_id ->
                # mean rating among raters
                "item_mean_rating":
                    item_mean_rating,

                # Overall mean rating.
                "global_mean":
                    float(
                        ratings["rating"].mean()
                    )
                    if len(ratings)
                    else 3.5,

                # Books sorted by Bayesian score.
                "popularity_rank":
                    popularity_rank,
            },
            f
        )

    print()
    print(
        "SUCCESS!"
    )

    print(
        f"Saved collaborative_model.pkl "
        f"to {model_path}"
    )


if __name__ == "__main__":
    main()
