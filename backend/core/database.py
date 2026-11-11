"""SQLite persistence for the hackathon MVP; supports file-backed local development."""
from __future__ import annotations
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from backend.core.config import settings


def _db_path() -> str:
    url = settings.database_url
    if not url.startswith("sqlite:///"):
        raise RuntimeError("This MVP currently supports SQLite. PostgreSQL adapter is a planned deployment task.")
    path = url.removeprefix("sqlite:///")
    Path(path).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)
    return path

@contextmanager
def connection():
    conn = sqlite3.connect(_db_path(), timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def init_db() -> None:
    with connection() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
          id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT NOT NULL UNIQUE,
          password_hash TEXT NOT NULL, email_verified INTEGER NOT NULL DEFAULT 1, token_version INTEGER NOT NULL DEFAULT 0,
          created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS trips (
          id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL REFERENCES users(id),
          origin TEXT NOT NULL, destination TEXT NOT NULL, start_date TEXT NOT NULL,
          end_date TEXT NOT NULL, travelers INTEGER NOT NULL CHECK(travelers > 0),
          budget_amount TEXT, budget_currency TEXT, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS payment_orders (
          id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL REFERENCES users(id),
          trip_id INTEGER REFERENCES trips(id), paypal_order_id TEXT NOT NULL UNIQUE,
          amount_minor INTEGER NOT NULL CHECK(amount_minor > 0), currency TEXT NOT NULL,
          status TEXT NOT NULL, request_id TEXT NOT NULL UNIQUE,
          created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS transactions (
          id INTEGER PRIMARY KEY AUTOINCREMENT, order_id INTEGER NOT NULL UNIQUE REFERENCES payment_orders(id),
          paypal_capture_id TEXT UNIQUE, amount_minor INTEGER NOT NULL, currency TEXT NOT NULL,
          status TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS email_action_tokens (
          id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          token_hash TEXT NOT NULL UNIQUE, purpose TEXT NOT NULL CHECK(purpose IN ('verify_email','reset_password')),
          expires_at INTEGER NOT NULL, used_at TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_email_action_tokens_user ON email_action_tokens(user_id, purpose);
        CREATE TABLE IF NOT EXISTS revoked_tokens (
          token_hash TEXT PRIMARY KEY, expires_at INTEGER NOT NULL,
          revoked_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS webhook_events (
          id INTEGER PRIMARY KEY AUTOINCREMENT, event_id TEXT NOT NULL UNIQUE,
          event_type TEXT NOT NULL, received_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS audit_logs (
          id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, action TEXT NOT NULL,
          details TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_trips_user ON trips(user_id);
        CREATE INDEX IF NOT EXISTS idx_orders_user ON payment_orders(user_id);
        """)
        # Upgrade databases created by earlier MVP versions without destructive changes.
        columns = {row[1] for row in db.execute("PRAGMA table_info(users)").fetchall()}
        if "email_verified" not in columns:
            db.execute("ALTER TABLE users ADD COLUMN email_verified INTEGER NOT NULL DEFAULT 1")
        if "token_version" not in columns:
            db.execute("ALTER TABLE users ADD COLUMN token_version INTEGER NOT NULL DEFAULT 0")
