"""Typed domain contracts shared by the backend ownership modules."""

from .configuration import (
    ConnectivityEdge,
    CustomerZoneMapping,
    DistributionSection,
    Feeder,
    NetworkConfigurationData,
    SwitchingDevice,
    ZoneSubstation,
)
from .enums import (
    ConfigurationStatus,
    EdgeSemantics,
    SourceAvailability,
    SwitchState,
    SwitchingDeviceType,
)

__all__ = [
    "ConfigurationStatus",
    "ConnectivityEdge",
    "CustomerZoneMapping",
    "DistributionSection",
    "EdgeSemantics",
    "Feeder",
    "NetworkConfigurationData",
    "SourceAvailability",
    "SwitchState",
    "SwitchingDevice",
    "SwitchingDeviceType",
    "ZoneSubstation",
]
