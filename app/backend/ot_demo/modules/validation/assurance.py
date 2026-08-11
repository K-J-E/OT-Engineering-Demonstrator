"""Backend-owned DC-005 assurance authorities and controlled-record resolution."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

from pydantic import Field, model_validator
from typing_extensions import Self

from ...domain.base import FrozenModel
from ...domain.enums import RequiredInputRole, SuspensionLifecyclePosition
from ...infrastructure.hashing import canonical_json_bytes, sha256_bytes, sha256_file
from .models import ValidationTargetSelection


class AssuranceAuthorityError(ValueError):
    """Raised when a requested assurance condition is not established."""


class ControlledSourceAssertion(FrozenModel):
    assertion_id: str = Field(min_length=1)
    source_id: str = Field(min_length=1)
    path: str = Field(min_length=1)
    version: str = Field(min_length=1)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    location: str = Field(min_length=1)
    assertion_text: str = Field(min_length=1)
    assertion_text_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    assertion_record_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_fingerprints(self) -> Self:
        text_hash = _text_sha256(self.assertion_text)
        record_hash = sha256_bytes(canonical_json_bytes({
            "assertion_id": self.assertion_id, "source_id": self.source_id,
            "path": self.path, "version": self.version, "sha256": self.sha256,
            "location": self.location, "assertion_text_sha256": text_hash,
        }))
        if self.assertion_text_sha256 != text_hash or self.assertion_record_sha256 != record_hash:
            raise ValueError("controlled assertion text/location fingerprint is invalid")
        return self


class ControlledDesignQuestion(FrozenModel):
    record_id: str = Field(pattern=r"^DQ-[0-9A-Z-]+$")
    status: Literal["OPEN", "CLOSED", "RESOLVED"]
    test_id: str
    case_id: str | None = None
    field_id: str
    source_assertion_ids: tuple[str, ...] = Field(min_length=1)
    review_record_id: str


class ControlledConflictReview(FrozenModel):
    record_id: str = Field(pattern=r"^(?:CR|QA)-[0-9A-Z-]+$")
    status: Literal["UNRESOLVED", "RESOLVED", "CLOSED"]
    test_id: str
    case_id: str | None = None
    field_id: str
    source_assertion_ids: tuple[str, ...] = Field(min_length=2)
    review_record_id: str


class ControlledTimeReview(FrozenModel):
    record_id: str = Field(pattern=r"^TR-[0-9A-Z-]+$")
    status: Literal["OPEN", "RESOLVED", "CLOSED"]
    test_id: str
    case_id: str | None = None
    step_reference: str
    step_text: str = Field(min_length=1)
    step_text_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    step_record_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_assertion_ids: tuple[str, ...] = Field(min_length=1)
    review_record_id: str

    @model_validator(mode="after")
    def validate_step_fingerprint(self) -> Self:
        text_hash = _text_sha256(self.step_text)
        record_hash = sha256_bytes(canonical_json_bytes({
            "record_id": self.record_id, "test_id": self.test_id,
            "case_id": self.case_id, "step_reference": self.step_reference,
            "step_text_sha256": text_hash,
            "source_assertion_ids": list(self.source_assertion_ids),
        }))
        if self.step_text_sha256 != text_hash or self.step_record_sha256 != record_hash:
            raise ValueError("controlled step text/reference fingerprint is invalid")
        return self


class EngineeringAssuranceRegistryData(FrozenModel):
    schema_version: str = "1.0"
    authority: str
    source_assertions: tuple[ControlledSourceAssertion, ...]
    design_questions: tuple[ControlledDesignQuestion, ...]
    conflict_reviews: tuple[ControlledConflictReview, ...]
    time_reviews: tuple[ControlledTimeReview, ...] = ()


class ControlledEngineeringRegistry:
    def __init__(self, data: EngineeringAssuranceRegistryData, repository_root: Path) -> None:
        self.data = data
        self.repository_root = repository_root.resolve()

    @classmethod
    def load(cls, path: Path, repository_root: Path) -> "ControlledEngineeringRegistry":
        return cls(
            EngineeringAssuranceRegistryData.model_validate_json(
                path.read_text(encoding="utf-8"), strict=True
            ),
            repository_root,
        )

    def _assertions(self, identifiers: tuple[str, ...]) -> tuple[ControlledSourceAssertion, ...]:
        indexed = {item.assertion_id: item for item in self.data.source_assertions}
        if len(set(identifiers)) != len(identifiers):
            raise AssuranceAuthorityError("controlled source assertion IDs must be unique")
        try:
            records = tuple(indexed[item] for item in identifiers)
        except KeyError as error:
            raise AssuranceAuthorityError("controlled source assertion does not exist") from error
        for item in records:
            source = (self.repository_root / item.path).resolve()
            if not source.is_relative_to(self.repository_root) or not source.is_file():
                raise AssuranceAuthorityError("controlled source artefact is unavailable")
            if sha256_file(source) != item.sha256:
                raise AssuranceAuthorityError("controlled source hash does not match the registry")
        return records

    def has_design_question(self, record_id: str) -> bool:
        return any(item.record_id == record_id for item in self.data.design_questions)

    def has_conflict(self, record_id: str) -> bool:
        return any(item.record_id == record_id for item in self.data.conflict_reviews)

    def has_time_review(self, record_id: str) -> bool:
        return any(item.record_id == record_id for item in self.data.time_reviews)

    @staticmethod
    def _binds(record: Any, target: ValidationTargetSelection, field_id: str) -> bool:
        return (
            record.test_id == target.test_id
            and record.case_id == target.case_id
            and record.field_id == field_id
        )

    def verify_design_question(
        self,
        target: ValidationTargetSelection,
        record_id: str,
        field_id: str,
        source_assertion_ids: tuple[str, ...],
    ) -> dict[str, Any]:
        record = next((item for item in self.data.design_questions if item.record_id == record_id), None)
        if record is None:
            raise AssuranceAuthorityError("registered design question does not exist")
        if record.status != "OPEN" or not self._binds(record, target, field_id):
            raise AssuranceAuthorityError("design question is not open for the bound test/case/field")
        if tuple(source_assertion_ids) != record.source_assertion_ids:
            raise AssuranceAuthorityError("design-question source assertions do not match its record")
        sources = self._assertions(source_assertion_ids)
        return {
            "open_design_question_id": record.record_id,
            "missing_field_or_step": field_id,
            "review_record_id": record.review_record_id,
            "authoritative_sources_checked": [item.model_dump(mode="json") for item in sources],
        }

    def verify_conflict(
        self,
        target: ValidationTargetSelection,
        record_id: str,
        field_id: str,
        source_assertion_ids: tuple[str, ...],
    ) -> dict[str, Any]:
        record = next((item for item in self.data.conflict_reviews if item.record_id == record_id), None)
        if record is None:
            raise AssuranceAuthorityError("controlled conflict-review item does not exist")
        if record.status != "UNRESOLVED" or not self._binds(record, target, field_id):
            raise AssuranceAuthorityError("conflict-review item is not unresolved for the bound test/case/field")
        if tuple(source_assertion_ids) != record.source_assertion_ids:
            raise AssuranceAuthorityError("conflict source assertions do not match its record")
        sources = self._assertions(source_assertion_ids)
        if len(sources) < 2:
            raise AssuranceAuthorityError("baseline conflict requires two controlled source assertions")
        return {
            "conflict_review_item": record.record_id,
            "review_disposition": "UNRESOLVED_BY_INDEPENDENT_ENGINEERING_REVIEW",
            "trusted_source_assertions": [item.model_dump(mode="json") for item in sources],
        }

    def verify_preentry_time(
        self,
        target: ValidationTargetSelection,
        record_id: str,
        step_reference: str,
        source_assertion_ids: tuple[str, ...],
    ) -> dict[str, Any]:
        record = next((item for item in self.data.time_reviews if item.record_id == record_id), None)
        if record is None or record.status != "OPEN":
            raise AssuranceAuthorityError("open controlled time-review record does not exist")
        if (
            record.test_id != target.test_id
            or record.case_id != target.case_id
            or record.step_reference != step_reference
            or record.source_assertion_ids != tuple(source_assertion_ids)
        ):
            raise AssuranceAuthorityError("time-review record is unrelated to the target/step")
        sources = self._assertions(source_assertion_ids)
        return {
            "dependency_name": step_reference,
            "wall_clock_reference": record.record_id,
            "controlled_replacement_unavailable": True,
            "review_record_id": record.review_record_id,
            "authoritative_sources_checked": [item.model_dump(mode="json") for item in sources],
            "controlled_step_text": record.step_text,
            "controlled_step_text_sha256": record.step_text_sha256,
            "controlled_step_record_sha256": record.step_record_sha256,
        }


class IdentityResolutionAuthority:
    def __init__(self, fixture_identities: tuple[str, ...] = ("network-one-line.v1",)) -> None:
        self.fixture_identities = fixture_identities

    def evaluate(self, target: ValidationTargetSelection, required_input_role: str) -> tuple[str, dict[str, Any]] | None:
        try:
            role = RequiredInputRole(required_input_role)
        except ValueError as error:
            raise AssuranceAuthorityError("required input role is outside the controlled resolver registry") from error
        requested = target.requested_identity_evidence.get(role.value, {})
        intended = target.intended_identity_evidence.get(role.value, {})
        return self.evaluate_evidence(role, requested, intended)

    def evaluate_evidence(
        self,
        role: RequiredInputRole,
        requested: dict[str, Any],
        intended: dict[str, Any],
    ) -> tuple[str, dict[str, Any]] | None:
        if role is RequiredInputRole.CONTROLLED_FIXTURE:
            requested_identity = requested.get("fixture_id")
            matches = [item for item in self.fixture_identities if item == requested_identity]
        else:
            matches = [intended] if requested == intended and requested else []
        evidence = {"input_name": role.value, "presented_identity_evidence": requested}
        if not requested or all(item is None or item == "" for item in requested.values()):
            return "MISSING_IDENTITY", {**evidence, "resolution_failure": "Required identity is absent from the trusted target selection."}
        if len(matches) == 0:
            return "UNKNOWN_IDENTITY", {**evidence, "resolution_failure": "No controlled identity matched the trusted target request."}
        if len(matches) > 1:
            return "AMBIGUOUS_IDENTITY", {**evidence, "resolution_failure": "More than one controlled identity matched the trusted target request."}
        return None

    def ambiguity_possible(self, role: RequiredInputRole) -> bool:
        return role is RequiredInputRole.CONTROLLED_FIXTURE and len(self.fixture_identities) != len(set(self.fixture_identities))


def _text_sha256(text: str) -> str:
    normalised = " ".join(text.split())
    return sha256_bytes(normalised.encode("utf-8"))


class ControlledArtifact(FrozenModel):
    artifact_reference: str
    path: Path
    expected_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    content_type: Literal["JSON", "BYTES"] = "JSON"
    expected_canonical_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")


class IntegrityVerificationAuthority:
    def __init__(self, artifacts: tuple[ControlledArtifact, ...]) -> None:
        self._artifacts = {item.artifact_reference: item for item in artifacts}

    def evaluate(self, artifact_reference: str) -> tuple[str, dict[str, Any]] | None:
        artifact = self._artifacts.get(artifact_reference)
        if artifact is None:
            raise AssuranceAuthorityError("controlled artefact reference is not registered")
        try:
            content = artifact.path.read_bytes()
        except OSError:
            return "UNREADABLE", {"examined_source": artifact_reference, "expected_integrity": artifact.expected_sha256, "observed_failure": "UNREADABLE", "quarantine_record": f"BACKEND:{artifact_reference}:UNREADABLE"}
        observed = sha256_bytes(content)
        if observed != artifact.expected_sha256:
            return "HASH_MISMATCH", {"examined_source": artifact_reference, "expected_integrity": artifact.expected_sha256, "observed_failure": observed, "quarantine_record": f"BACKEND:{artifact_reference}:HASH_MISMATCH"}
        if artifact.content_type == "JSON":
            try:
                payload = json.loads(content)
            except (UnicodeDecodeError, json.JSONDecodeError):
                return "SCHEMA_INVALID", {"examined_source": artifact_reference, "expected_integrity": artifact.expected_sha256, "observed_failure": "SCHEMA_INVALID", "quarantine_record": f"BACKEND:{artifact_reference}:SCHEMA_INVALID"}
            canonical = sha256_bytes(canonical_json_bytes(payload))
            if artifact.expected_canonical_sha256 and canonical != artifact.expected_canonical_sha256:
                return "CANONICAL_PAYLOAD_MISMATCH", {"examined_source": artifact_reference, "expected_integrity": artifact.expected_canonical_sha256, "observed_failure": canonical, "quarantine_record": f"BACKEND:{artifact_reference}:CANONICAL_PAYLOAD_MISMATCH"}
        return None

    def has_reference(self, artifact_reference: str) -> bool:
        return artifact_reference in self._artifacts


class RuntimeTimeAuthority:
    def __init__(self, controlled_failures: dict[str, dict[str, Any]] | None = None) -> None:
        self._controlled_failures = controlled_failures or {}

    def evaluate(
        self,
        lifecycle: SuspensionLifecyclePosition,
        step_reference: str,
        execution_id: str | None,
    ) -> tuple[str, dict[str, Any]] | None:
        if lifecycle is SuspensionLifecyclePosition.PRE_EXECUTION_ENTRY:
            raise AssuranceAuthorityError("pre-entry time review requires engineering-review authority")
        failure = self._controlled_failures.get(step_reference)
        if failure is None:
            return None
        failure_code = failure.get("failure_code", "WALL_CLOCK_SOURCE_DETECTED")
        if failure_code not in {
            "MISSING_CONTROLLED_TIME",
            "WALL_CLOCK_SOURCE_DETECTED",
            "NONDETERMINISTIC_DELAY_DEPENDENCY",
        }:
            raise AssuranceAuthorityError("runtime time authority returned an uncontrolled failure code")
        return failure_code, {
            "dependency_name": step_reference,
            "wall_clock_reference": failure["wall_clock_reference"],
            "controlled_replacement_unavailable": True,
            "backend_execution_id": execution_id,
            "backend_verifier": "RuntimeTimeAuthority",
        }

    def has_failure(self, step_reference: str) -> bool:
        return step_reference in self._controlled_failures
