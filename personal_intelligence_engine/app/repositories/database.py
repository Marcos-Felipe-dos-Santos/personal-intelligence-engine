"""SQLite database management for PIE.

This module owns all direct sqlite3 interaction.
Services MUST NOT import sqlite3 directly — they use repositories instead.
"""

from __future__ import annotations

import logging
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from personal_intelligence_engine.app.config import Config

logger = logging.getLogger(__name__)


class Database:
    """Manages the SQLite connection and schema migrations."""

    def __init__(self, config: Config) -> None:
        self._config = config
        self._db_path = config.database_path
        self._conn: sqlite3.Connection | None = None
        self._transaction_depth = 0

    @property
    def connection(self) -> sqlite3.Connection:
        """Return the current connection, opening one if needed."""
        if self._conn is None:
            if self._db_path.parent != self._db_path:
                self._db_path.parent.mkdir(parents=True, exist_ok=True)
            self._conn = sqlite3.connect(str(self._db_path))
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL;")
            self._conn.execute("PRAGMA foreign_keys=ON;")
        return self._conn

    def close(self) -> None:
        """Close the database connection."""
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def run_migrations(self) -> None:
        """Apply all pending SQL migrations from the migrations directory."""
        conn = self.connection

        # Ensure schema_migrations table exists
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version TEXT PRIMARY KEY,
                applied_at TEXT NOT NULL DEFAULT (datetime('now'))
            );
            """
        )
        conn.commit()

        # Find applied versions
        cursor = conn.execute("SELECT version FROM schema_migrations ORDER BY version;")
        applied = {row["version"] for row in cursor.fetchall()}

        # Find migration files
        migrations_dir = self._config.migrations_dir
        if not migrations_dir.exists():
            return

        migration_files = sorted(migrations_dir.glob("*.sql"))

        for migration_file in migration_files:
            version = migration_file.stem  # e.g. "001_initial_schema"
            if version in applied:
                continue

            logger.info("Applying migration: %s", version)

            sql = migration_file.read_text(encoding="utf-8")
            conn.executescript(sql)
            conn.execute(
                "INSERT INTO schema_migrations (version) VALUES (?);",
                (version,),
            )
            conn.commit()

            # Verify the migration was recorded
            self._verify_migration(version)

            logger.info("Migration applied successfully: %s", version)

    def pending_migrations(self) -> list[str]:
        """Return a list of migration versions that have not been applied yet."""
        conn = self.connection

        # Ensure schema_migrations table exists
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version TEXT PRIMARY KEY,
                applied_at TEXT NOT NULL DEFAULT (datetime('now'))
            );
            """
        )

        cursor = conn.execute("SELECT version FROM schema_migrations ORDER BY version;")
        applied = {row["version"] for row in cursor.fetchall()}

        migrations_dir = self._config.migrations_dir
        if not migrations_dir.exists():
            return []

        migration_files = sorted(migrations_dir.glob("*.sql"))
        return [f.stem for f in migration_files if f.stem not in applied]

    def applied_migrations(self) -> list[tuple[str, str]]:
        """Return a list of (version, applied_at) for all applied migrations."""
        conn = self.connection

        # Ensure schema_migrations table exists
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version TEXT PRIMARY KEY,
                applied_at TEXT NOT NULL DEFAULT (datetime('now'))
            );
            """
        )

        cursor = conn.execute(
            "SELECT version, applied_at FROM schema_migrations ORDER BY version;"
        )
        return [(row["version"], row["applied_at"]) for row in cursor.fetchall()]

    def _verify_migration(self, version: str) -> None:
        """Verify the migration was recorded in schema_migrations."""
        row = self.fetchone(
            "SELECT version FROM schema_migrations WHERE version = ?;",
            (version,),
        )
        if row is None:
            raise RuntimeError(
                f"Migration '{version}' was not recorded after execution."
            )

    def backup_to(self, destination: str | Path) -> None:
        """Copy the SQLite database to destination using SQLite's backup API."""
        source = sqlite3.connect(str(self._db_path))
        target = sqlite3.connect(str(destination))
        try:
            source.backup(target)
        finally:
            target.close()
            source.close()

    @contextmanager
    def transaction(self) -> Iterator[None]:
        """Run multiple repository writes inside one SQLite transaction."""
        conn = self.connection
        if self._transaction_depth > 0:
            self._transaction_depth += 1
            try:
                yield
            finally:
                self._transaction_depth -= 1
            return

        conn.execute("BEGIN;")
        self._transaction_depth = 1
        try:
            yield
        except Exception:
            conn.rollback()
            raise
        else:
            conn.commit()
        finally:
            self._transaction_depth = 0

    def execute(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        """Execute a SQL statement and return the cursor."""
        return self.connection.execute(sql, params)

    def executemany(self, sql: str, params_seq: list[tuple]) -> sqlite3.Cursor:
        """Execute a SQL statement with many parameter sets."""
        return self.connection.executemany(sql, params_seq)

    def commit(self) -> None:
        """Commit the current transaction."""
        if self._transaction_depth > 0:
            return
        self.connection.commit()

    def fetchone(self, sql: str, params: tuple = ()) -> sqlite3.Row | None:
        """Execute and fetch a single row."""
        cursor = self.execute(sql, params)
        return cursor.fetchone()

    def fetchall(self, sql: str, params: tuple = ()) -> list[sqlite3.Row]:
        """Execute and fetch all rows."""
        cursor = self.execute(sql, params)
        return cursor.fetchall()
