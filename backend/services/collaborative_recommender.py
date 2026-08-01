"""
Collaborative recommender: item-based CF using the adjusted-cosine
item-item similarity table built by scripts/build_collaborative_model.py.

Prediction formula for a candidate book i, given a user's rated books:

    predicted(i) = mean_i + ( sum_j sim(i,j) * (r_uj - mean_j) )
                            / ( sum_j |sim(i,j)| )

summed over the user's rated books j that appear in i's neighbor list.
This is standard item-based CF with mean-centering, which keeps the
prediction from being biased by books that are just generally
rated-high/low.
"""
import pickle
from collections import defaultdict

from config import Config

_state = {"model": None}


def _ensure_loaded():
    if _state["model"] is not None:
        return
    with open(Config.MODELS_DIR / "collaborative_model.pkl", "rb") as f:
        _state["model"] = pickle.load(f)


def popularity_fallback(top_n=10, exclude=None):
    """Bayesian-average popularity ranking -- used for cold-start users."""
    _ensure_loaded()
    exclude = exclude or set()
    ranked = [bid for bid in _state["model"]["popularity_rank"] if bid not in exclude]
    return ranked[:top_n]


def recommend_for_user(rated_books: dict, top_n: int = 10):
    """
    rated_books: {book_id: rating(1-5), ...} for ONE user.
    Returns [(book_id, predicted_rating), ...], best first.
    Returns [] if the user has no ratings this model can use (caller
    should fall back to popularity_fallback / content-based cold start).
    """
    _ensure_loaded()
    model = _state["model"]
    neighbors = model["neighbors"]
    item_mean = model["item_mean_rating"]
    global_mean = model["global_mean"]

    if not rated_books:
        return []

    score = defaultdict(float)
    weight = defaultdict(float)

    for j, r_uj in rated_books.items():
        mean_j = item_mean.get(j, global_mean)
        for i, sim in neighbors.get(j, []):
            if i in rated_books:
                continue
            score[i] += sim * (r_uj - mean_j)
            weight[i] += abs(sim)

    predictions = []
    for i, w in weight.items():
        if w > 0:
            mean_i = item_mean.get(i, global_mean)
            predictions.append((i, mean_i + score[i] / w))

    predictions.sort(key=lambda x: -x[1])
    return predictions[:top_n]


def predicted_scores_for_user(rated_books: dict):
    """Same as recommend_for_user but returns ALL scored candidates as a
    dict (no top_n cutoff) -- used by the hybrid recommender to combine
    with content scores before ranking."""
    _ensure_loaded()
    model = _state["model"]
    neighbors = model["neighbors"]
    item_mean = model["item_mean_rating"]
    global_mean = model["global_mean"]

    score = defaultdict(float)
    weight = defaultdict(float)
    for j, r_uj in rated_books.items():
        mean_j = item_mean.get(j, global_mean)
        for i, sim in neighbors.get(j, []):
            if i in rated_books:
                continue
            score[i] += sim * (r_uj - mean_j)
            weight[i] += abs(sim)

    return {i: item_mean.get(i, global_mean) + score[i] / w for i, w in weight.items() if w > 0}
