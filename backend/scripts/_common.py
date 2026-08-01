"""Shared helpers for the import scripts."""
import ast
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # allow `import config`, `import db`


def list_field_to_json(val):
    """
    books_enriched.csv stores authors/genres as python-list-looking strings,
    e.g. "['Suzanne Collins']" or "['fantasy', 'fiction']". Convert to a
    clean JSON array string for storage, so any frontend can `JSON.parse`
    it directly. Falls back to a single-element array on parse failure.
    """
    if val is None:
        return json.dumps([])
    val = str(val).strip()
    if not val or val.lower() == "nan":
        return json.dumps([])
    try:
        parsed = ast.literal_eval(val)
        if isinstance(parsed, list):
            return json.dumps([str(x) for x in parsed])
    except (ValueError, SyntaxError):
        pass
    return json.dumps([val])


def clean_int(val):
    try:
        if val is None or str(val).strip() == "" or str(val).lower() == "nan":
            return None
        return int(float(val))
    except (ValueError, TypeError):
        return None


def clean_float(val):
    try:
        if val is None or str(val).strip() == "" or str(val).lower() == "nan":
            return None
        return float(val)
    except (ValueError, TypeError):
        return None


def clean_str(val, max_len=None):
    if val is None:
        return None
    s = str(val).strip()
    if not s or s.lower() == "nan":
        return None
    if max_len:
        s = s[:max_len]
    return s
