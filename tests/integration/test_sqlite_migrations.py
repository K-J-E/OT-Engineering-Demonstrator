"""I1 SQLite migration foundation: Demonstrator Design Sections 9 and 31."""

import sqlite3
from importlib.resources import files
from pathlib import Path

import pytest

from ot_demo.infrastructure.sqlite_migrations import apply_migrations


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
MIGRATIONS = REPOSITORY_ROOT / "app/backend/ot_demo/infrastructure/migrations"


@pytest.mark.i1
def test_initial_migration_applies_once_and_is_repeatable(tmp_path: Path) -> None:
    database_path = tmp_path / "i1.sqlite3"
    with sqlite3.connect(database_path) as connection:
        assert apply_migrations(connection, MIGRATIONS) == (1,)
        assert apply_migrations(connection, MIGRATIONS) == ()
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        assert {
            "schema_migrations",
            "configuration_catalog",
            "application_builds",
        } <= tables


@pytest.mark.i1
def test_initial_migration_is_included_in_the_python_package() -> None:
    migration = files("ot_demo.infrastructure").joinpath("migrations/001_initial.sql")
    assert migration.is_file()
