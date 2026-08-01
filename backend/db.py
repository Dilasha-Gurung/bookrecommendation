"""
Thin MySQL connection helper built on PyMySQL.
Uses DictCursor everywhere so query results are JSON-serializable dicts.
"""
import pymysql
import pymysql.cursors
from contextlib import contextmanager
from config import Config


def get_connection():
    return pymysql.connect(
        host=Config.DB_HOST,
        port=Config.DB_PORT,
        user=Config.DB_USER,
        password=Config.DB_PASSWORD,
        database=Config.DB_NAME,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False,
    )


@contextmanager
def db_cursor(commit=False):
    """
    Usage:
        with db_cursor() as cur:
            cur.execute("SELECT * FROM books WHERE book_id=%s", (1,))
            row = cur.fetchone()

        with db_cursor(commit=True) as cur:
            cur.execute("INSERT INTO ...")
    """
    conn = get_connection()
    try:
        cur = conn.cursor()
        yield cur
        if commit:
            conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
