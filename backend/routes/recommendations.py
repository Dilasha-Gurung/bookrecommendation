"""
Recommendation endpoints:
  GET  /api/recommendations/similar/<book_id>   content-based, no login needed
  GET  /api/recommendations/for-you             hybrid, requires login
  POST /api/recommendations/cold-start          for a brand-new / logged-out
                                                 user: pass a few liked book_ids
"""
import json

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity

from db import db_cursor
from config import Config
from services import content_recommender, collaborative_recommender, hybrid_recommender

bp = Blueprint("recommendations", __name__, url_prefix="/api/recommendations")


def _hydrate(scored_items):
    """Turn [{'book_id':.., 'score':..}, ...] into full book records, preserving order."""
    book_ids = [item["book_id"] for item in scored_items]
    if not book_ids:
        return []

    placeholders = ",".join(["%s"] * len(book_ids))
    with db_cursor() as cur:
        cur.execute(
            f"""
            SELECT b.*, (pf.pdf_id IS NOT NULL) AS pdf_available
            FROM books b
            LEFT JOIN pdf_files pf ON pf.book_id = b.book_id
            WHERE b.book_id IN ({placeholders})
            """,
            book_ids,
        )
        rows = {r["book_id"]: r for r in cur.fetchall()}

    out = []
    for item in scored_items:
        row = rows.get(item["book_id"])
        if not row:
            continue
        out.append({
            "book_id": row["book_id"],
            "title": row["title"],
            "authors": json.loads(row["authors"]) if row["authors"] else [],
            "genres": json.loads(row["genres"]) if row["genres"] else [],
            "average_rating": float(row["average_rating"]) if row["average_rating"] is not None else None,
            "image_url": row["image_url"],
            "pdf_available": bool(row["pdf_available"]),
            "score": item.get("score"),
            "reason": item.get("reason"),
        })
    return out


def _get_user_ratings(user_id):
    with db_cursor() as cur:
        cur.execute("SELECT book_id, rating FROM ratings WHERE user_id=%s", (user_id,))
        return {r["book_id"]: r["rating"] for r in cur.fetchall()}


@bp.get("/similar/<int:book_id>")
def similar(book_id):
    top_n = min(int(request.args.get("top_n", 10)), 50)
    only_with_pdf = request.args.get("only_with_pdf", "false").lower() == "true"

    if not content_recommender.is_known_book(book_id):
        return jsonify({"error": "book not found in content model"}), 404

    results = content_recommender.similar_books(book_id, top_n=top_n * 3 if only_with_pdf else top_n)
    scored = [{"book_id": bid, "score": score, "reason": "content_similarity"} for bid, score in results]
    hydrated = _hydrate(scored)
    if only_with_pdf:
        hydrated = [b for b in hydrated if b["pdf_available"]]
    return jsonify({"book_id": book_id, "results": hydrated[:top_n]})


@bp.get("/for-you")
@jwt_required()
def for_you():
    user_id = int(get_jwt_identity())
    top_n = min(int(request.args.get("top_n", 10)), 50)
    alpha = float(request.args.get("alpha", Config.DEFAULT_ALPHA))
    only_with_pdf = request.args.get("only_with_pdf", "false").lower() == "true"

    rated = _get_user_ratings(user_id)
    scored = hybrid_recommender.recommend(rated, top_n=top_n * 3 if only_with_pdf else top_n, alpha=alpha)
    hydrated = _hydrate(scored)
    if only_with_pdf:
        hydrated = [b for b in hydrated if b["pdf_available"]]

    return jsonify({
        "user_id": user_id,
        "alpha": alpha,
        "is_cold_start": len(rated) == 0,
        "results": hydrated[:top_n],
    })


@bp.post("/cold-start")
def cold_start():
    """
    Body: { "liked_book_ids": [1, 12, 340], "top_n": 10 }
    Works for logged-out visitors and brand-new users: no rating history
    required, just a handful of "books you like" picks. Falls back to pure
    popularity if `liked_book_ids` is empty.
    """
    body = request.get_json(silent=True) or {}
    liked_book_ids = [int(b) for b in body.get("liked_book_ids", [])]
    top_n = min(int(body.get("top_n", 10)), 50)

    scored = hybrid_recommender.recommend({}, top_n=top_n, alpha=Config.DEFAULT_ALPHA, seed_likes=liked_book_ids)
    return jsonify({"results": _hydrate(scored)})
