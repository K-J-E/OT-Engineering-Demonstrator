"""Small inspectable SQLite migration runner for the I1 schema foundation."""

import re
import sqlite3
from pathlib import Path


_MIGRATION_NAME = re.compile(r"^(?P<version>\d{3})_(?P<name>[a-z0-9_]+)\.sql$")


def apply_migrations(connection: sqlite3.Connection, migration_directory: Path) -> tuple[int, ...]:
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            applied_at_utc TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    applied = {
        row[0] for row in connection.execute("SELECT version FROM schema_migrations")
    }
    newly_applied: list[int] = []
    for path in sorted(migration_directory.glob("*.sql")):
        match = _MIGRATION_NAME.fullmatch(path.name)
        if match is None:
            raise ValueError(f"invalid migration filename: {path.name}")
        version = int(match.group("version"))
        if version in applied:
            continue
        with connection:
            connection.executescript(path.read_text(encoding="utf-8"))
            connection.execute(
                "INSERT INTO schema_migrations(version, name) VALUES (?, ?)",
                (version, match.group("name")),
            )
        newly_applied.append(version)
    return tuple(newly_applied)
