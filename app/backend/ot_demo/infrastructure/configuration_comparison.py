"""Deterministic structural comparison for controlled configuration QA."""

from dataclasses import dataclass
from typing import Any

from ..domain.configuration import NetworkConfigurationData


@dataclass(frozen=True, slots=True)
class ConfigurationDifference:
    path: str
    before: Any
    after: Any


_KEY_FIELDS = {
    "sources": "entity_id",
    "feeders": "entity_id",
    "sections": "entity_id",
    "switching_devices": "entity_id",
    "connectivity_edges": "edge_id",
    "customer_zone_mappings": "section_id",
}


def compare_engineering_content(
    before: NetworkConfigurationData,
    after: NetworkConfigurationData,
) -> tuple[ConfigurationDifference, ...]:
    before_value = _normalize(before.model_dump(mode="json"))
    after_value = _normalize(after.model_dump(mode="json"))
    differences: list[ConfigurationDifference] = []
    _compare("", before_value, after_value, differences)
    return tuple(differences)


def _normalize(value: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(value)
    for collection, key_field in _KEY_FIELDS.items():
        normalized[collection] = {
            item[key_field]: item for item in normalized.get(collection, [])
        }
    return normalized


def _compare(
    path: str,
    before: Any,
    after: Any,
    differences: list[ConfigurationDifference],
) -> None:
    if isinstance(before, dict) and isinstance(after, dict):
        for key in sorted(set(before) | set(after)):
            child_path = f"{path}.{key}" if path else key
            if key not in before:
                differences.append(ConfigurationDifference(child_path, None, after[key]))
            elif key not in after:
                differences.append(ConfigurationDifference(child_path, before[key], None))
            else:
                _compare(child_path, before[key], after[key], differences)
        return
    if before != after:
        differences.append(ConfigurationDifference(path, before, after))
