"""Strict immutable base model for controlled engineering records."""

from pydantic import BaseModel, ConfigDict


class FrozenModel(BaseModel):
    """Reject unknown fields and mutation after validation."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        strict=True,
        validate_default=True,
    )
