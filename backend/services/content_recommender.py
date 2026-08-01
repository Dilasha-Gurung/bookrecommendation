"""
Content-based recommender: TF-IDF over title + authors + genres +
description, compared with cosine similarity.

Loads the model built by scripts/build_content_model.py once per process
and reuses it for every request.
"""
import pickle
import numpy as np
from sklearn.metrics.pairwise import linear_kernel

from config import Config

_state = {"book_ids": None, "matrix": None, "idx_of": None}


def _ensure_loaded():
    if _state["matrix"] is not None:
        return
    with open(Config.MODELS_DIR / "content_matrix.pkl", "rb") as f:
        data = pickle.load(f)
    _state["book_ids"] = data["book_ids"]
    _state["matrix"] = data["matrix"]  # TF-IDF rows are already L2-normalized by TfidfVectorizer
    _state["idx_of"] = {bid: i for i, bid in enumerate(data["book_ids"])}


def is_known_book(book_id: int) -> bool:
    _ensure_loaded()
    return book_id in _state["idx_of"]


def similar_books(book_id: int, top_n: int = 10, exclude=None):
    """Return [(book_id, similarity_score), ...] most similar to `book_id`."""
    _ensure_loaded()
    idx = _state["idx_of"].get(book_id)
    if idx is None:
        return []

    matrix = _state["matrix"]
    # linear_kernel of two L2-normalized TF-IDF rows == cosine similarity
    scores = linear_kernel(matrix[idx], matrix).flatten()
    scores[idx] = -np.inf
    exclude = exclude or set()
    for bid in exclude:
        j = _state["idx_of"].get(bid)
        if j is not None:
            scores[j] = -np.inf

    k = min(top_n, len(scores) - 1)
    top_idx = np.argpartition(-scores, k)[:k]
    top_idx = top_idx[np.argsort(-scores[top_idx])]
    return [(_state["book_ids"][i], float(scores[i])) for i in top_idx if scores[i] > -np.inf]


def user_profile_scores(liked_book_ids):
    """
    Average cosine similarity, across all books, to a set of book_ids the
    user likes. Returns a dict book_id -> score covering every book in the
    catalog (used by the hybrid recommender to score candidates).
    """
    _ensure_loaded()
    matrix = _state["matrix"]
    idxs = [_state["idx_of"][bid] for bid in liked_book_ids if bid in _state["idx_of"]]
    if not idxs:
        return {}

    sims = linear_kernel(matrix[idxs], matrix)  # (n_liked, n_books)
    avg = sims.mean(axis=0)
    return {bid: float(avg[i]) for i, bid in enumerate(_state["book_ids"])}
