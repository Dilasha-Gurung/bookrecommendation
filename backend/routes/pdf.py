"""
Secure PDF serving.

Rules enforced here:
  - The only input from the client is a numeric book_id -- never a raw
    file path, so a user can never request an arbitrary server file.
  - file_path is looked up from pdf_files (trusted, server-controlled
    data), then resolved against PDF_DIR and checked to make sure it
    didn't escape that directory (defends against a malicious/bugged
    file_path value ever reaching this far).
  - If there's no pdf_files row, or the file is missing on disk, respond
    with a clear "unavailable" message instead of a raw 404/500.
"""
from pathlib import Path

from flask import Blueprint, jsonify, send_file
from flask_jwt_extended import jwt_required

from db import db_cursor
from config import Config

bp = Blueprint("pdf", __name__, url_prefix="/api/pdf")


@bp.get("/<int:book_id>")
@jwt_required(optional=True)  # flip to jwt_required() if PDFs should require login
def get_pdf(book_id):
    with db_cursor() as cur:
        cur.execute("SELECT file_path FROM pdf_files WHERE book_id=%s", (book_id,))
        row = cur.fetchone()

    if not row:
        return jsonify({"available": False, "message": "No PDF is available for this book."}), 404

    candidate = (Config.PDF_DIR / row["file_path"]).resolve()
    try:
        candidate.relative_to(Config.PDF_DIR.resolve())
    except ValueError:
        # file_path somehow points outside pdfs/ -- refuse rather than trust it
        return jsonify({"available": False, "message": "PDF path is invalid."}), 500

    if not candidate.is_file():
        return jsonify({"available": False, "message": "PDF file is missing on the server."}), 404

    return send_file(candidate, mimetype="application/pdf", as_attachment=False)


@bp.get("/<int:book_id>/status")
def pdf_status(book_id):
    with db_cursor() as cur:
        cur.execute("SELECT file_path FROM pdf_files WHERE book_id=%s", (book_id,))
        row = cur.fetchone()
    if not row:
        return jsonify({"available": False})
    exists = (Config.PDF_DIR / row["file_path"]).resolve().is_file()
    return jsonify({"available": exists})
