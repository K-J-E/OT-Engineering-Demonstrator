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
