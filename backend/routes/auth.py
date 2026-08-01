"""
Registration / login for real users. Dataset users (imported from
ratings.csv) are not meant to log in through this flow -- they exist only
to supply historical ratings for collaborative filtering.
"""
import re

import bcrypt
from flask import Blueprint, jsonify, request
from flask_jwt_extended import create_access_token

from db import db_cursor

bp = Blueprint("auth", __name__, url_prefix="/api/auth")

USERNAME_RE = re.compile(r"^[a-zA-Z0-9_]{3,64}$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@bp.post("/register")
def register():
    body = request.get_json(silent=True) or {}
    username = (body.get("username") or "").strip()
    email = (body.get("email") or "").strip().lower()
    password = body.get("password") or ""

    if not USERNAME_RE.match(username):
        return jsonify({"error": "username must be 3-64 characters: letters, numbers, underscore"}), 400
    if not EMAIL_RE.match(email):
        return jsonify({"error": "a valid email is required"}), 400
    if len(password) < 8:
        return jsonify({"error": "password must be at least 8 characters"}), 400

    with db_cursor() as cur:
        cur.execute("SELECT id FROM users WHERE username=%s OR email=%s", (username, email))
        if cur.fetchone():
            return jsonify({"error": "username or email already in use"}), 409

    password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    with db_cursor(commit=True) as cur:
        cur.execute(
            "INSERT INTO users (dataset_user_id, username, email, password_hash, is_dataset_user) "
            "VALUES (NULL, %s, %s, %s, 0)",
            (username, email, password_hash),
        )
        user_id = cur.lastrowid

    token = create_access_token(identity=str(user_id))
    return jsonify({"token": token, "user": {"id": user_id, "username": username, "email": email}}), 201


@bp.post("/login")
def login():
    body = request.get_json(silent=True) or {}
    identifier = (body.get("username") or body.get("email") or "").strip()
    password = body.get("password") or ""

    with db_cursor() as cur:
        cur.execute(
            "SELECT id, username, email, password_hash FROM users WHERE username=%s OR email=%s",
            (identifier, identifier.lower()),
        )
        user = cur.fetchone()

    if not user or not bcrypt.checkpw(password.encode("utf-8"), user["password_hash"].encode("utf-8")):
        return jsonify({"error": "invalid credentials"}), 401

    token = create_access_token(identity=str(user["id"]))
    return jsonify({
        "token": token,
        "user": {"id": user["id"], "username": user["username"], "email": user["email"]},
    })


@bp.get("/me")
def me():
    # kept simple/unauthenticated-safe: real "who am I" lives behind
    # @jwt_required() in practice; see recommendations.py for the pattern.
    return jsonify({"message": "use Authorization: Bearer <token> on protected endpoints"})
