"""Validated scalar value objects for stable identifiers and quantities."""

from typing import Annotated

from pydantic import Field, StringConstraints


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
