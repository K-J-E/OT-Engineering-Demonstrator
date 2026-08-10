"""Controlled scenario-time arithmetic for telemetry evidence."""

from datetime import datetime, timedelta, timezone

from ...domain.enums import FreshnessStatus, TelemetryQuality
from .models import TelemetryPoint, TelemetryValidity


MAXIMUM_TELEMETRY_AGE_MS = 60_000
_EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)


def instant_to_epoch_ms(value: datetime) -> int:
    delta = value - _EPOCH
    return (
        delta.days * 86_400_000
        + delta.seconds * 1_000
        + delta.microseconds // 1_000
    )


def epoch_ms_to_instant(value: int) -> datetime:
    return _EPOCH + timedelta(milliseconds=value)


class TelemetryValidityService:
    """Classify one observation without consulting the host wall clock."""

    def classify(
        self,
        point: TelemetryPoint,
        scenario_time: datetime,
    ) -> TelemetryValidity:
        age_ms = instant_to_epoch_ms(scenario_time) - instant_to_epoch_ms(
            point.last_update_scenario_time
        )
        if age_ms < 0:
            freshness = FreshnessStatus.INVALID_TIMESTAMP
        elif age_ms <= MAXIMUM_TELEMETRY_AGE_MS:
            freshness = FreshnessStatus.FRESH
        else:
            freshness = FreshnessStatus.STALE

        reasons: list[str] = []
        if freshness is FreshnessStatus.INVALID_TIMESTAMP:
            reasons.append("FUTURE_TELEMETRY_TIMESTAMP")
        elif freshness is FreshnessStatus.STALE:
            reasons.append("TELEMETRY_STALE")
        if point.quality is not TelemetryQuality.GOOD:
            reasons.append(f"QUALITY_{point.quality.value}")
        if not reasons:
            reasons.append("TELEMETRY_VALID")

        return TelemetryValidity(
            point_id=point.point_id,
            age_ms=age_ms,
            freshness=freshness,
            quality=point.quality,
            quality_valid=point.quality is TelemetryQuality.GOOD,
            timestamp_valid=freshness is not FreshnessStatus.INVALID_TIMESTAMP,
            overall_valid=(
                point.quality is TelemetryQuality.GOOD
                and freshness is FreshnessStatus.FRESH
            ),
            reason_codes=tuple(reasons),
        )
