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
        assert apply_migrations(connection, MIGRATIONS) == (
            1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13
        )
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
            "investigation_defect_records",
            "investigation_correction_records",
            "investigation_repeat_links",
            "evidence_packages",
            "composite_validation_results",
            "composite_validation_constituents",
            "composite_evidence_packages",
            "validation_target_selections",
            "validation_attempts",
            "executed_validation_results",
            "validation_suspension_records",
            "validation_suspension_evidence",
            "composite_validation_constituent_sources",
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


@pytest.mark.i7
def test_i7_migration_is_included_in_the_python_package() -> None:
    migration = files("ot_demo.infrastructure").joinpath(
        "migrations/005_investigation_correction.sql"
    )
    assert migration.is_file()


@pytest.mark.i8
def test_i8_migration_is_included_in_the_python_package() -> None:
    migration = files("ot_demo.infrastructure").joinpath(
        "migrations/006_evidence_packages.sql"
    )
    assert migration.is_file()


@pytest.mark.i8
def test_dc004_migration_is_included_in_the_python_package() -> None:
    migration = files("ot_demo.infrastructure").joinpath(
        "migrations/007_dc004_composite_validation.sql"
    )
    assert migration.is_file()


@pytest.mark.i8
def test_dc005_migration_is_included_in_the_python_package() -> None:
    migration = files("ot_demo.infrastructure").joinpath(
        "migrations/008_dc005_validation_suspension.sql"
    )
    assert migration.is_file()
    assurance_migration = files("ot_demo.infrastructure").joinpath(
        "migrations/009_dc005_composite_executed_result.sql"
    )
    assert assurance_migration.is_file()
