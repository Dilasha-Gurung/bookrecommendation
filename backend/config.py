"""
Central configuration. All values can be overridden with environment
variables (see .env.example) -- defaults match a fresh XAMPP install.
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent  # project/

class Config:
    # --- MySQL (XAMPP defaults: root user, empty password, port 3306) ---
    DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
    DB_PORT = int(os.getenv("DB_PORT", "3306"))
    DB_USER = os.getenv("DB_USER", "root")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")
    DB_NAME = os.getenv("DB_NAME", "book_recommender")

    # --- Auth ---
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "change-this-in-production")
    JWT_ACCESS_TOKEN_EXPIRES_HOURS = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRES_HOURS", "24"))

    # --- File storage ---
    DATA_DIR = Path(os.getenv("DATA_DIR", BASE_DIR / "data"))
    PDF_DIR = Path(os.getenv("PDF_DIR", BASE_DIR / "pdfs"))
    MODELS_DIR = Path(os.getenv("MODELS_DIR", Path(__file__).resolve().parent / "models"))

    # --- Recommender ---
    DEFAULT_ALPHA = float(os.getenv("DEFAULT_ALPHA", "0.5"))   # content vs collaborative weight
    TOP_K_NEIGHBORS = int(os.getenv("TOP_K_NEIGHBORS", "50"))  # item-item neighbors kept per book

    # --- CORS (frontend dev server) ---
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
