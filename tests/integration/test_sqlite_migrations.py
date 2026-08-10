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
        assert apply_migrations(connection, MIGRATIONS) == (1, 2, 3, 4)
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
            "scenario_runs",
            "scenario_telemetry_points",
            "scenario_alarms",
            "topology_snapshots",
            "outage_snapshots",
            "operational_events",
            "scenario_command_results",
            "restoration_assessments",
            "restoration_assessment_invalidations",
            "validation_executions",
            "validation_evidence_snapshots",
        } <= tables


@pytest.mark.i1
def test_initial_migration_is_included_in_the_python_package() -> None:
    migration = files("ot_demo.infrastructure").joinpath("migrations/001_initial.sql")
    assert migration.is_file()


@pytest.mark.i3
def test_i3_migration_is_included_in_the_python_package() -> None:
    migration = files("ot_demo.infrastructure").joinpath(
        "migrations/002_scenario_transactions.sql"
    )
    assert migration.is_file()


@pytest.mark.i4
def test_i4_migration_is_included_in_the_python_package() -> None:
    migration = files("ot_demo.infrastructure").joinpath(
        "migrations/003_restoration.sql"
    )
    assert migration.is_file()


@pytest.mark.i5
def test_i5_migration_is_included_in_the_python_package() -> None:
    migration = files("ot_demo.infrastructure").joinpath(
        "migrations/004_validation_evidence.sql"
    )
    assert migration.is_file()
