"""Controlled enum values established by the accepted engineering baseline."""

from enum import StrEnum


class ConfigurationStatus(StrEnum):
    DEFECTIVE_TEST_INPUT = "DEFECTIVE_TEST_INPUT"
    CORRECTED_BASELINE = "CORRECTED_BASELINE"


class SourceAvailability(StrEnum):
    AVAILABLE = "AVAILABLE"
    UNAVAILABLE = "UNAVAILABLE"


class SwitchState(StrEnum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"


class SwitchingDeviceType(StrEnum):
    FEEDER_SOURCE_BREAKER = "FEEDER_SOURCE_BREAKER"
    SECTIONALISING_SWITCH = "SECTIONALISING_SWITCH"
    TIE_SWITCH = "TIE_SWITCH"


class EdgeSemantics(StrEnum):
    SWITCHABLE_DEVICE_CONNECTION = "SWITCHABLE_DEVICE_CONNECTION"


class TelemetryQuality(StrEnum):
    GOOD = "GOOD"
    UNCERTAIN = "UNCERTAIN"
    BAD = "BAD"


class FreshnessStatus(StrEnum):
    FRESH = "FRESH"
    STALE = "STALE"
    INVALID_TIMESTAMP = "INVALID_TIMESTAMP"


class BoundaryEvidenceCondition(StrEnum):
    TRUSTWORTHY_OPEN = "A_TRUSTWORTHY_OPEN"
    TRUSTWORTHY_CLOSED = "B_TRUSTWORTHY_CLOSED"
    UNTRUSTWORTHY_OR_ABSENT = "C_UNTRUSTWORTHY_OR_ABSENT"


class BoundaryProofStatus(StrEnum):
    PROVEN_OPEN = "PROVEN_OPEN"
    PROVEN_CLOSED = "PROVEN_CLOSED"
    UNPROVEN = "UNPROVEN"


class BoundaryOperationNeed(StrEnum):
    NONE_SATISFIED = "NONE_SATISFIED"
    OPEN_REQUIRED = "OPEN_REQUIRED"
    EVIDENCE_REQUIRED = "EVIDENCE_REQUIRED"


class RadialityStatus(StrEnum):
    RADIAL = "RADIAL"
    UNINTENDED_LOOP = "UNINTENDED_LOOP"
