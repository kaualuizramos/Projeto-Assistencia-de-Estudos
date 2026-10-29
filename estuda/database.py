"""Conexões SQLite e migrações incrementais do aplicativo."""

from __future__ import annotations

import logging
import sqlite3
import uuid
from datetime import datetime, timezone
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

logger = logging.getLogger(__name__)


class Database:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self._memory = str(path) == ":memory:"
        self._memory_uri = f"file:estuda-{uuid.uuid4().hex}?mode=memory&cache=shared" if self._memory else None
        self._keeper = sqlite3.connect(self._memory_uri, uri=True, check_same_thread=False) if self._memory else None

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        if self._memory:
            connection = sqlite3.connect(self._memory_uri, uri=True, timeout=10, check_same_thread=False)
        else:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 10000")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def initialize(self) -> None:
        with self.connection() as db:
            db.execute("PRAGMA journal_mode = WAL")
            db.executescript("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    email TEXT NOT NULL UNIQUE COLLATE NOCASE,
                    salt BLOB NOT NULL,
                    password_hash BLOB NOT NULL,
                    password_algorithm TEXT NOT NULL DEFAULT 'pbkdf2_sha256',
                    role TEXT NOT NULL DEFAULT 'student',
                    failed_attempts INTEGER NOT NULL DEFAULT 0,
                    locked_until TEXT,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL DEFAULT '',
                    deadline TEXT NOT NULL,
                    priority TEXT NOT NULL DEFAULT 'Média',
                    status TEXT NOT NULL DEFAULT 'Pendente',
                    completed_at TEXT,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS subtasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
                    title TEXT NOT NULL,
                    done INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    title TEXT NOT NULL DEFAULT 'Nova conversa',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    sent_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    conversation_id INTEGER REFERENCES conversations(id) ON DELETE CASCADE,
                    status TEXT NOT NULL DEFAULT 'Sent'
                );
                CREATE TABLE IF NOT EXISTS suggestions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    conversation_id INTEGER NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
                    task_id INTEGER REFERENCES tasks(id) ON DELETE CASCADE,
                    title TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'Proposed',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS focus_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    task_id INTEGER REFERENCES tasks(id) ON DELETE SET NULL,
                    task_title TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    ended_at TEXT,
                    duration_seconds INTEGER NOT NULL,
                    paused_seconds INTEGER NOT NULL DEFAULT 0,
                    paused_at TEXT,
                    status TEXT NOT NULL DEFAULT 'Running'
                );
                CREATE TABLE IF NOT EXISTS notifications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    message TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    read_at TEXT,
                    kind TEXT NOT NULL DEFAULT 'General'
                );
                CREATE TABLE IF NOT EXISTS reminders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    task_id INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
                    scheduled_at TEXT NOT NULL,
                    email_enabled INTEGER NOT NULL DEFAULT 0,
                    status TEXT NOT NULL DEFAULT 'Scheduled',
                    email_attempts INTEGER NOT NULL DEFAULT 0,
                    retry_at TEXT,
                    last_error TEXT,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS app_settings (
                    id INTEGER PRIMARY KEY CHECK(id = 1),
                    ai_enabled INTEGER NOT NULL DEFAULT 1,
                    daily_message_limit INTEGER NOT NULL DEFAULT 20
                );
                CREATE TABLE IF NOT EXISTS password_resets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    token_hash TEXT NOT NULL UNIQUE,
                    expires_at TEXT NOT NULL,
                    used_at TEXT
                );
                CREATE TABLE IF NOT EXISTS login_attempts (
                    email TEXT PRIMARY KEY COLLATE NOCASE,
                    attempts INTEGER NOT NULL DEFAULT 0,
                    window_started TEXT NOT NULL,
                    locked_until TEXT
                );
            """)
            self._add_column(db, "users", "password_algorithm", "TEXT NOT NULL DEFAULT 'pbkdf2_sha256'")
            self._add_column(db, "users", "role", "TEXT NOT NULL DEFAULT 'student'")
            self._add_column(db, "users", "failed_attempts", "INTEGER NOT NULL DEFAULT 0")
            self._add_column(db, "users", "locked_until", "TEXT")
            self._add_column(db, "users", "created_at", "TEXT")
            self._add_column(db, "tasks", "completed_at", "TEXT")
            self._add_column(db, "tasks", "created_at", "TEXT")
            self._add_column(db, "messages", "conversation_id", "INTEGER REFERENCES conversations(id) ON DELETE CASCADE")
            self._add_column(db, "messages", "status", "TEXT NOT NULL DEFAULT 'Sent'")
            self._migrate_legacy_deadlines(db)
            db.execute("CREATE INDEX IF NOT EXISTS idx_tasks_user_deadline ON tasks(user_id, deadline)")
            db.execute("CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id, id)")
            db.execute("CREATE INDEX IF NOT EXISTS idx_reminders_due ON reminders(status, scheduled_at, retry_at)")
            db.execute("CREATE INDEX IF NOT EXISTS idx_focus_user_date ON focus_sessions(user_id, started_at)")
            db.execute("CREATE INDEX IF NOT EXISTS idx_notifications_user_read ON notifications(user_id, read_at, created_at)")
            db.execute("INSERT OR IGNORE INTO app_settings(id) VALUES(1)")
            old_users = db.execute("SELECT id FROM users WHERE id NOT IN (SELECT user_id FROM conversations)").fetchall()
            for row in old_users:
                conversation_id = db.execute("INSERT INTO conversations(user_id,title) VALUES(?,?)", (row["id"], "Histórico anterior")).lastrowid
                db.execute("UPDATE messages SET conversation_id=? WHERE user_id=? AND conversation_id IS NULL", (conversation_id, row["id"]))
            version = db.execute("PRAGMA user_version").fetchone()[0]
            if version < 2:
                logger.info("Migrando banco Estuda+ de versão %s para 2", version)
                db.execute("PRAGMA user_version = 2")

    @staticmethod
    def _add_column(db: sqlite3.Connection, table: str, column: str, definition: str) -> None:
        columns = {row["name"] for row in db.execute(f"PRAGMA table_info({table})")}
        if column not in columns:
            db.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

    @staticmethod
    def _migrate_legacy_deadlines(db: sqlite3.Connection) -> None:
        """Converte prazos locais sem fuso do protótipo inicial para UTC ISO."""
        rows = db.execute("SELECT id,deadline FROM tasks WHERE deadline NOT LIKE '%+__:__' AND deadline NOT LIKE '%Z'").fetchall()
        for row in rows:
            try:
                local_value = datetime.fromisoformat(row["deadline"])
            except ValueError:
                continue
            if local_value.tzinfo is None:
                db.execute("UPDATE tasks SET deadline=? WHERE id=?", (local_value.astimezone(timezone.utc).isoformat(), row["id"]))

