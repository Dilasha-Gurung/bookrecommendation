"""Book listing, search, and detail endpoints."""
import json

from flask import Blueprint, jsonify, request

from db import db_cursor

bp = Blueprint("books", __name__, url_prefix="/api/books")


def _serialize_book(row):
    return {
        "book_id": row["book_id"],
        "title": row["title"],
        "authors": json.loads(row["authors"]) if row["authors"] else [],
        "genres": json.loads(row["genres"]) if row["genres"] else [],
        "description": row["description"],
        "average_rating": float(row["average_rating"]) if row["average_rating"] is not None else None,
        "ratings_count": row["ratings_count"],
        "image_url": row["image_url"],
        "publication_year": row["publication_year"],
        "pdf_available": bool(row.get("pdf_available")),
    }


@bp.get("")
def list_books():
    """GET /api/books?q=hobbit&page=1&page_size=20"""
    q = (request.args.get("q") or "").strip()
    page = max(int(request.args.get("page", 1)), 1)
    page_size = min(max(int(request.args.get("page_size", 20)), 1), 100)
    offset = (page - 1) * page_size

    base = """
        SELECT b.*, (pf.pdf_id IS NOT NULL) AS pdf_available
        FROM books b
        LEFT JOIN pdf_files pf ON pf.book_id = b.book_id
    """
    params = []
    if q:
        base += " WHERE b.title LIKE %s "
        params.append(f"%{q}%")
    base += " ORDER BY b.ratings_count DESC LIMIT %s OFFSET %s"
    params += [page_size, offset]

    with db_cursor() as cur:
        cur.execute(base, params)
        rows = cur.fetchall()

    return jsonify({"page": page, "page_size": page_size, "books": [_serialize_book(r) for r in rows]})


@bp.get("/<int:book_id>")
def get_book(book_id):
    with db_cursor() as cur:
        cur.execute(
            """
            SELECT b.*, (pf.pdf_id IS NOT NULL) AS pdf_available
            FROM books b
            LEFT JOIN pdf_files pf ON pf.book_id = b.book_id
            WHERE b.book_id = %s
            """,
            (book_id,),
        )
        row = cur.fetchone()

    if not row:
        return jsonify({"error": "book not found"}), 404
    return jsonify(_serialize_book(row))
