"""Validated scalar value objects for stable identifiers and quantities."""

from datetime import datetime, timedelta, timezone
from typing import Annotated

from pydantic import (
    AfterValidator,
    AwareDatetime,
    Field,
    PlainSerializer,
    StringConstraints,
)


EngineeringId = Annotated[
    str,
    StringConstraints(
        min_length=4,
        max_length=96,
        pattern=r"^[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)+$",
        strip_whitespace=True,
    ),
]
ConfigurationId = Annotated[
    str,
    StringConstraints(
        pattern=r"^network-configuration-v\d+\.\d+$",
        strip_whitespace=True,
    ),
]
SemanticVersion = Annotated[
    str,
    StringConstraints(pattern=r"^\d+\.\d+(?:\.\d+)?$", strip_whitespace=True),
]
Sha256Digest = Annotated[
    str,
    StringConstraints(pattern=r"^[0-9a-f]{64}$", to_lower=True, strip_whitespace=True),
]
NonNegativeKilowatts = Annotated[int, Field(ge=0)]
PositiveCustomerCount = Annotated[int, Field(gt=0)]


def _validate_utc_millisecond_instant(value: datetime) -> datetime:
    if value.utcoffset() != timedelta(0):
        raise ValueError("scenario timestamps must use UTC")
    if value.microsecond % 1000:
        raise ValueError("scenario timestamps must have millisecond precision")
    return value.astimezone(timezone.utc)


UtcMillisecondInstant = Annotated[
    datetime,
    AwareDatetime,
    AfterValidator(_validate_utc_millisecond_instant),
    PlainSerializer(
        lambda value: (
            value.strftime("%Y-%m-%dT%H:%M:%S.")
            + f"{value.microsecond // 1000:03d}Z"
        ),
        return_type=str,
        when_used="json",
    ),
]
