"""
Hybrid recommender: blends content-based and collaborative scores.

    final_score = alpha * content_score_norm + (1 - alpha) * collaborative_score_norm

Both components are min-max normalized to [0, 1] over the current
candidate set before blending, so `alpha` behaves consistently even
though the two raw scores live on different scales (cosine similarity
in [0, 1] vs. predicted rating roughly in [1, 5]).

Cold start:
  - No ratings at all (brand new user)        -> pure popularity ranking.
  - A few "seed likes" but no formal ratings
    (e.g. an onboarding "pick books you like") -> content-based similarity
    to the seed books, blended with popularity so results aren't overly
    narrow.
  - Enough ratings for collaborative filtering -> full hybrid blend.
"""
from . import content_recommender, collaborative_recommender

MIN_RATINGS_FOR_CF = 1  # item-based CF can produce *some* signal from a single rating;
                         # raise this (e.g. to 3-5) if predictions feel noisy for very new users


def _normalize(d: dict):
    if not d:
        return {}
    values = list(d.values())
    lo, hi = min(values), max(values)
    if hi - lo < 1e-9:
        return {k: 0.0 for k in d}
    return {k: (v - lo) / (hi - lo) for k, v in d.items()}


def recommend(rated_books: dict, top_n: int = 10, alpha: float = 0.5, seed_likes=None):
    """
    rated_books: {book_id: rating(1-5), ...} — the user's real rating history.
    seed_likes:  optional list[book_id] — books the user picked as "I like this"
                 during onboarding, when they have no star ratings yet.
    """
    exclude = set(rated_books.keys()) | set(seed_likes or [])

    # --- cold start: no ratings and no seed likes -> popularity only ---
    if not rated_books and not seed_likes:
        book_ids = collaborative_recommender.popularity_fallback(top_n=top_n, exclude=exclude)
        return [{"book_id": bid, "score": None, "reason": "popular"} for bid in book_ids]

    # --- cold start: seed likes only, no formal ratings yet -> content + popularity ---
    if not rated_books and seed_likes:
        content_scores = content_recommender.user_profile_scores(seed_likes)
        content_scores = {k: v for k, v in content_scores.items() if k not in exclude}
        ranked = sorted(content_scores.items(), key=lambda x: -x[1])[:top_n]
        if len(ranked) < top_n:
            filler = collaborative_recommender.popularity_fallback(
                top_n=top_n - len(ranked), exclude=exclude | {bid for bid, _ in ranked}
            )
            ranked += [(bid, None) for bid in filler]
        return [{"book_id": bid, "score": score, "reason": "content_coldstart"} for bid, score in ranked]

    # --- enough signal for the full hybrid blend ---
    content_scores = content_recommender.user_profile_scores(list(rated_books.keys()) + list(seed_likes or []))
    collab_scores = collaborative_recommender.predicted_scores_for_user(rated_books)

    content_scores = {k: v for k, v in content_scores.items() if k not in exclude}
    collab_scores = {k: v for k, v in collab_scores.items() if k not in exclude}

    content_norm = _normalize(content_scores)
    collab_norm = _normalize(collab_scores)

    candidates = set(content_norm) | set(collab_norm)
    hybrid = {}
    for bid in candidates:
        c = content_norm.get(bid, 0.0)
        cf = collab_norm.get(bid, 0.0)
        hybrid[bid] = alpha * c + (1 - alpha) * cf

    ranked = sorted(hybrid.items(), key=lambda x: -x[1])[:top_n]
    return [
        {
            "book_id": bid,
            "score": score,
            "content_score": content_norm.get(bid, 0.0),
            "collaborative_score": collab_norm.get(bid, 0.0),
            "reason": "hybrid",
        }
        for bid, score in ranked
    ]
