"""I3 telemetry validity and operational-event catalogue conformance."""

from datetime import datetime, timedelta, timezone

import pytest

from ot_demo.domain.enums import (
    FreshnessStatus,
    OperationalEventType,
    SwitchState,
    TelemetryQuality,
)
from ot_demo.modules.telemetry import TelemetryPoint, TelemetryValidityService


T0 = datetime(2030, 1, 1, tzinfo=timezone.utc)


def point(*, age_ms: int, quality: TelemetryQuality) -> TelemetryPoint:
    return TelemetryPoint(
        point_id="BRK-A",
        entity_id="BRK-A",
        value=SwitchState.OPEN,
        quality=quality,
        last_update_scenario_time=T0 - timedelta(milliseconds=age_ms),
        revision=1,
    )


@pytest.mark.i3
@pytest.mark.parametrize(
    ("age_ms", "expected"),
    [
        (0, FreshnessStatus.FRESH),
        (59_999, FreshnessStatus.FRESH),
        (60_000, FreshnessStatus.FRESH),
        (60_001, FreshnessStatus.STALE),
        (-1, FreshnessStatus.INVALID_TIMESTAMP),
    ],
)
def test_controlled_freshness_boundaries(
    age_ms: int,
    expected: FreshnessStatus,
) -> None:
    result = TelemetryValidityService().classify(
        point(age_ms=age_ms, quality=TelemetryQuality.GOOD),
        T0,
    )

    assert result.age_ms == age_ms
    assert result.freshness is expected
    assert result.overall_valid is (expected is FreshnessStatus.FRESH)


@pytest.mark.i3
@pytest.mark.parametrize("quality", [TelemetryQuality.UNCERTAIN, TelemetryQuality.BAD])
def test_quality_remains_independent_from_freshness(
    quality: TelemetryQuality,
) -> None:
    result = TelemetryValidityService().classify(
        point(age_ms=0, quality=quality),
        T0,
    )

    assert result.freshness is FreshnessStatus.FRESH
    assert result.quality is quality
    assert result.quality_valid is False
    assert result.timestamp_valid is True
    assert result.overall_valid is False
    assert result.reason_codes == (f"QUALITY_{quality.value}",)


@pytest.mark.i3
def test_operational_event_catalogue_is_exactly_the_approved_fifteen_types() -> None:
    assert tuple(item.value for item in OperationalEventType) == (
        "SCENARIO_INITIALISED",
        "CONFIGURATION_SELECTED",
        "FAULT_INITIATED",
        "TELEMETRY_UPDATED",
        "DEVICE_STATE_CHANGE",
        "ALARM_GENERATED",
        "ALARM_ACKNOWLEDGED",
        "SWITCHING_ACTION",
        "TOPOLOGY_RECALCULATED",
        "OUTAGE_UPDATED",
        "RESTORATION_CANDIDATE_IDENTIFIED",
        "RESTORATION_NO_CANDIDATE",
        "RESTORATION_ASSESSED",
        "RESTORATION_ASSESSMENT_INVALIDATED",
        "SCENARIO_RESET",
    )
    assert all(
        token not in item.value
        for item in OperationalEventType
        for token in ("PASS", "FAIL", "DEFECT", "CORRECTION", "REVIEW")
    )


@pytest.mark.i3
def test_scenario_timestamp_serializes_as_utc_with_exact_milliseconds() -> None:
    payload = point(age_ms=0, quality=TelemetryQuality.GOOD).model_dump_json()

    assert '"last_update_scenario_time":"2030-01-01T00:00:00.000Z"' in payload
