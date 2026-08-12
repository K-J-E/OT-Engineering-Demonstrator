"""Definition-owned DC-006 value normalisation executed before operators."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import re
from typing import Any


class NormalisationError(ValueError):
    """Raised for an unsupported profile or a value incompatible with its profile."""


SUPPORTED_NORMALISATION_PROFILES = frozenset(
    {
        "exact canonical representation", "no exclusions", "exclude no fields",
        "empty", "empty; stable event-ID sort", "empty; stable identity sort",
        "empty; stable record-name sort", "stable Demonstrator Design view-register order",
        "stable record-name and owner order", "controlled exclusion profile",
        "ms integer", "60001 ms", "-1 ms", "1500 kW integer", "4500 kW integer",
        "4501 kW integer", "6000 kW integer", "kW integer; complete attribution required",
        "kW integer; percent one decimal", "kW integer; percentage one decimal",
        "kW integer; percent one decimal; explicit null", "MW two decimals; percent one decimal",
        "true", "false", "PASS", "FAIL", "BLOCKED", "REJECTED", "AVAILABLE",
        "RADIAL", "SATISFIED",
    }
)

_NUMBER = re.compile(r"(?<![A-Za-z0-9])[-−]?\d[\d,]*(?:\.\d+)?")
_GENERATED_ID_FIELDS = frozenset(
    {
        "scenario_run_id", "validation_execution_id", "evidence_snapshot_id",
        "run_id", "execution_id", "repeat_of_execution_id", "immutable_result_identity",
        "criterion_finding_id", "executed_result_id", "command_id", "event_id",
        "alarm_id", "assessment_id", "created_at", "captured_at", "finalised_at",
    }
)


def normalise(profile: str, value: Any, *, expected: bool) -> Any:
    if profile not in SUPPORTED_NORMALISATION_PROFILES:
        raise NormalisationError(f"unsupported controlled normalisation profile: {profile}")
    if profile in {"exact canonical representation", "no exclusions", "exclude no fields"}:
        return _canonical(value)
    if profile.startswith("empty"):
        if expected and isinstance(value, str):
            return ()
        return tuple(sorted((_canonical(item) for item in (value or ())), key=repr))
    if profile == "stable Demonstrator Design view-register order":
        return tuple(_canonical(item) for item in value) if not isinstance(value, str) else value
    if profile in {"stable record-name and owner order"}:
        if isinstance(value, str):
            return value
        if isinstance(value, dict):
            return tuple(sorted((str(key), _canonical(item)) for key, item in value.items()))
        return tuple(sorted((_canonical(item) for item in value), key=repr))
    if profile == "controlled exclusion profile":
        if expected and isinstance(value, str):
            return "CONTROLLED_OUTPUTS_EQUAL"
        if not isinstance(value, dict) or set(value) < {"left", "right"}:
            raise NormalisationError(
                "controlled exclusion profile requires left/right preserved outputs"
            )
        excluded = set(value.get("excluded_fields", _GENERATED_ID_FIELDS))
        left = _without_fields(value["left"], excluded)
        right = _without_fields(value["right"], excluded)
        return "CONTROLLED_OUTPUTS_EQUAL" if left == right else {
            "left": left,
            "right": right,
        }
    if profile in {"true", "false"}:
        if expected:
            return profile == "true"
        if not isinstance(value, bool):
            raise NormalisationError("boolean profile requires a boolean observation")
        return value
    if profile in {"PASS", "FAIL", "BLOCKED", "REJECTED", "AVAILABLE", "RADIAL", "SATISFIED"}:
        return profile if expected else _scalar(value)
    if profile == "kW integer; percent one decimal; explicit null":
        if isinstance(value, str) and "None, None, None" in value and "None%" in value:
            return (None, None, None, None)
        if isinstance(value, dict):
            fields = (
                "transferable_load_kw", "resulting_load_kw",
                "feeder_capacity_kw", "resulting_loading_percent",
            )
            if all(value.get(field) is None for field in fields):
                return (None, None, None, None)
    if "integer" in profile or "decimal" in profile or "ms" in profile:
        numbers = _numbers(value)
        if not numbers:
            raise NormalisationError("numeric profile did not resolve a numeric value")
        decimals = 2 if "MW two decimals" in profile else 1 if (
            "percent one decimal" in profile or "percentage one decimal" in profile
        ) else 0
        quantum = Decimal(1).scaleb(-decimals)
        quantised = tuple(item.quantize(quantum, rounding=ROUND_HALF_UP) for item in numbers)
        converted = tuple(
            int(item) if item == item.to_integral_value() else float(item)
            for item in quantised
        )
        return converted[0] if len(converted) == 1 else converted
    raise NormalisationError(f"profile has no executable treatment: {profile}")


def _scalar(value: Any) -> Any:
    return value.value if hasattr(value, "value") else value


def _canonical(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="json")
    if isinstance(value, dict):
        return {str(key): _canonical(item) for key, item in sorted(value.items())}
    if isinstance(value, (list, tuple)):
        return tuple(_canonical(item) for item in value)
    if isinstance(value, set):
        return tuple(sorted((_canonical(item) for item in value), key=repr))
    return _scalar(value)


def _numbers(value: Any) -> tuple[Decimal, ...]:
    if isinstance(value, bool):
        return ()
    if isinstance(value, (int, float, Decimal)):
        return (Decimal(str(value)),)
    if isinstance(value, str):
        result: list[Decimal] = []
        for match in _NUMBER.findall(value.replace("−", "-")):
            try:
                result.append(Decimal(match.replace(",", "")))
            except InvalidOperation as error:
                raise NormalisationError("invalid controlled numeric value") from error
        return tuple(result)
    if isinstance(value, dict):
        result: list[Decimal] = []
        for key, item in value.items():
            if item is None or key.endswith("_complete"):
                continue
            result.extend(_numbers(item))
        return tuple(result)
    if isinstance(value, (list, tuple)):
        return tuple(item for value_item in value for item in _numbers(value_item))
    return ()


def _without_fields(value: Any, excluded: set[str]) -> Any:
    value = _canonical(value)
    if isinstance(value, dict):
        return {
            key: _without_fields(item, excluded)
            for key, item in value.items()
            if key not in excluded
        }
    if isinstance(value, tuple):
        return tuple(_without_fields(item, excluded) for item in value)
    return value
