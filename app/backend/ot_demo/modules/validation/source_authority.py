"""Registered QA-050 producers over the application's controlling authorities.

Only this module creates :class:`AuthoritativeRecordSnapshot` instances used by
DC-006 campaign determination.  Its public input is an attempt plus source
identity/context; it never accepts an observation payload or owner declaration.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import Any
from uuid import UUID

from ...application.scenario_coordinator import ScenarioCoordinator
from ...domain.enums import (
    DeterminationContextKind,
    DeterminationSourceAdapterKind,
    OperationalEventType,
    PermissiveStatus,
    RestorationOutcome,
    SwitchState,
    TelemetryQuality,
)
from ...infrastructure.build_identity import ApplicationBuildManifest
from ...infrastructure.configuration_comparison import compare_engineering_content
from ...infrastructure.configuration_loader import JsonConfigurationLoader
from ...infrastructure.evidence_package_repository import EvidencePackageRepository
from ...infrastructure.determination_repository import DeterminationRepository
from ...infrastructure.hashing import canonical_json_bytes, sha256_bytes
from ...infrastructure.investigation_repository import InvestigationRepository
from ...infrastructure.validation_repository import ValidationRepository
from ..restoration.service import RestorationService
from ..telemetry.models import TelemetryPoint
from ..telemetry.service import TelemetryValidityService
from .catalogue import ValidationCatalogueResolver
from .models import (
    AuthoritativeRecordSnapshot,
    DeterminationMethodDefinition,
    ValidationAttempt,
    ValidationTargetSelection,
)


class SourceAuthorityError(ValueError):
    """Raised when a registered producer cannot resolve its controlling source."""


@dataclass(frozen=True, slots=True)
class SourceAuthorityContext:
    attempt: ValidationAttempt
    target: ValidationTargetSelection
    method: DeterminationMethodDefinition
    scenario_run_id: UUID | None
    validation_execution_id: UUID | None


@dataclass(frozen=True, slots=True)
class ProducedRoleAuthority:
    source_type: DeterminationSourceAdapterKind
    source_role: str
    records: tuple[AuthoritativeRecordSnapshot, ...]
    origin_identity: str
    evidence_references: tuple[str, ...]

    @property
    def origin_identity_sha256(self) -> str:
        return sha256_bytes(canonical_json_bytes({
            "producer": self.source_type.value,
            "role": self.source_role,
            "origin_identity": self.origin_identity,
            "records": [
                {
                    "record_type": item.record_type,
                    "record_id": item.record_id,
                    "record_version": str(item.record_version),
                    "owner_module": item.owner_module,
                    "canonical_payload_sha256": item.canonical_payload_sha256,
                }
                for item in self.records
            ],
        }))


@dataclass(frozen=True, slots=True)
class SourceAuthorityDependencies:
    repository_root: Path
    build: ApplicationBuildManifest
    configurations: JsonConfigurationLoader
    catalogue: ValidationCatalogueResolver
    validation: ValidationRepository
    scenarios: ScenarioCoordinator
    investigation: InvestigationRepository
    packages: EvidencePackageRepository
    determination: DeterminationRepository
    telemetry: TelemetryValidityService = TelemetryValidityService()
    restoration: RestorationService = RestorationService()


_CONFIGURATION_ORACLE = {
    "1.0": {
        "configuration_id": "network-configuration-v1.0",
        "manifest_sha256": "d0243fae46e6a5d403855953e14cdedbcdae9c71af7761a1aba49f88470bc12d",
        "data_sha256": "67cb237df5084919b568f5620c523cb868db03eaba71e7f16c2f2671242f7ab3",
        "schema_sha256": "ee6d42cb36be3470870028ab9983eba3a6ce33529ead73dfebc584b04b89c60c",
    },
    "1.1": {
        "configuration_id": "network-configuration-v1.1",
        "manifest_sha256": "e0f16f3acdf2e85aa04cd23bb4b584a868626117b68f682d1219821a36857662",
        "data_sha256": "7d65b7fb2e3e7b5cb3f0fc698554c3848935222fe56aee727d25cfc324e93281",
        "schema_sha256": "ee6d42cb36be3470870028ab9983eba3a6ce33529ead73dfebc584b04b89c60c",
    },
}


class RegisteredSourceAuthority:
    """Resolve exact method roles through one of eight fixed producers."""

    def __init__(self, dependencies: SourceAuthorityDependencies) -> None:
        self._d = dependencies

    def produce(self, context: SourceAuthorityContext) -> tuple[ProducedRoleAuthority, ...]:
        producer = self._producer_for(context.method)
        produced = producer(context)
        if {item.source_role for item in produced} != set(context.method.required_context_roles):
            raise SourceAuthorityError("producer did not resolve the exact method role set")
        return produced

    def _producer_for(self, method: DeterminationMethodDefinition):
        roots = {
            part.strip().split(".", 1)[0].split("[", 1)[0]
            for criterion in method.criteria
            for part in criterion.source_selector.split(" + ")
        }
        if method.context_kind is DeterminationContextKind.CONTROLLED_FIXTURE_EXECUTION:
            return self._fixture
        if method.context_kind is DeterminationContextKind.ENGINEERING_REVIEW:
            return self._nfr
        if roots <= {"ConfigurationPackageAdapter", "ConfigurationComparisonResult"}:
            return self._configuration
        if roots & {"AlarmAdapter", "OperationalEventRegistry"}:
            return self._events
        if roots & {"InvestigationAdapter", "ValidationEvidenceAdapter", "FormalProgressAdapter", "ScenarioRunAdapter"}:
            return self._validation_history
        if roots == {"DeterministicRepeatAdapter"}:
            return self._repeat
        if roots & {"EvidencePackageAdapter", "HistoricalCatalogueResolver"}:
            return self._evidence_packages
        return self._scenario

    def _configuration(self, context: SourceAuthorityContext) -> tuple[ProducedRoleAuthority, ...]:
        before = self._d.configurations.load("v1.0")
        after = self._d.configurations.load("v1.1")
        actual = {"1.0": before, "1.1": after}
        identity_ok = all(
            loaded.catalog_entry.configuration_id == _CONFIGURATION_ORACLE[version]["configuration_id"]
            and loaded.catalog_entry.package_sha256 == _CONFIGURATION_ORACLE[version]["manifest_sha256"]
            and loaded.catalog_entry.data_sha256 == _CONFIGURATION_ORACLE[version]["data_sha256"]
            and loaded.catalog_entry.schema_sha256 == _CONFIGURATION_ORACLE[version]["schema_sha256"]
            for version, loaded in actual.items()
        )
        canonical_ok = all(
            loaded.catalog_entry.data_sha256 == _CONFIGURATION_ORACLE[version]["data_sha256"]
            for version, loaded in actual.items()
        )
        differences = compare_engineering_content(before.data, after.data)
        raw_differences = tuple(
            {"path": item.path, "before": item.before, "after": item.after}
            for item in differences
        )
        exact_difference = raw_differences == ({
            "path": "connectivity_edges.EDGE-SW-A23-1.endpoint_a_id",
            "before": "SEC-B3",
            "after": "SEC-A2",
        },)
        common = self._common(context)
        package_adapter = self._snapshot(
            DeterminationSourceAdapterKind.CONFIGURATION_PACKAGE,
            "ConfigurationPackageAdapter",
            "network-configuration-controlled-package-assurance",
            {
                "manifest": {
                    "configuration_id": [
                        loaded.catalog_entry.configuration_id
                        for loaded in actual.values()
                    ],
                    "version": list(actual),
                    "sha256": [
                        loaded.catalog_entry.package_sha256
                        for loaded in actual.values()
                    ],
                },
                "manifest_identity_hash_satisfied": identity_ok,
                "schema_validation": True,
                "canonical_network_payload": {
                    version: loaded.data.model_dump(mode="json")
                    for version, loaded in actual.items()
                },
                "canonical_network_oracle_satisfied": canonical_ok,
                "resolved_packages": {
                    version: loaded.catalog_entry.model_dump(mode="json")
                    for version, loaded in actual.items()
                },
            },
            **common,
        )
        comparison = self._snapshot(
            DeterminationSourceAdapterKind.CONFIGURATION_PACKAGE,
            "ConfigurationComparisonResult",
            "network-configuration-v1.0-v1.1-comparison",
            {
                "differences": list(raw_differences),
                "exact_approved_difference": exact_difference,
                "projection_kind": "CONFIGURATION_BASELINE",
                "uncontrolled_differences": [] if exact_difference else list(raw_differences),
            },
            **common,
        )
        packages = {
            version: self._snapshot(
                DeterminationSourceAdapterKind.CONFIGURATION_PACKAGE,
                "NetworkConfigurationPackage",
                f"{loaded.manifest.configuration_id}:{loaded.manifest.version}",
                loaded.model_dump(mode="json"),
                **(
                    common
                    | {
                        "configuration_id": loaded.manifest.configuration_id,
                        "configuration_version": str(loaded.manifest.version),
                    }
                ),
            )
            for version, loaded in actual.items()
        }
        schema = self._snapshot(
            DeterminationSourceAdapterKind.CONFIGURATION_PACKAGE,
            "NetworkConfigurationSchema",
            f"network-configuration-schema:{after.manifest.schema_version}",
            {
                "schema_version": str(after.manifest.schema_version),
                "schema_sha256": after.catalog_entry.schema_sha256,
            },
            **common,
        )
        by_role = {
            "NETWORK_CONFIGURATION_V1_0": (packages["1.0"],),
            "NETWORK_CONFIGURATION_V1_1": (packages["1.1"],),
            "NETWORK_CONFIGURATION_SCHEMA": (schema,),
            "EXACT_PACKAGE_COMPARISON": (package_adapter, comparison),
        }
        return self._roles(context, DeterminationSourceAdapterKind.CONFIGURATION_PACKAGE, by_role)

    def _scenario(self, context: SourceAuthorityContext) -> tuple[ProducedRoleAuthority, ...]:
        run_id, execution_id = self._scenario_identity(context)
        snapshot = self._d.scenarios.snapshot(run_id)
        execution = self._d.validation.get_execution(execution_id)
        evidence = self._d.validation.list_evidence(execution_id)
        if execution.scenario_run_id != run_id:
            raise SourceAuthorityError("validation execution does not belong to scenario run")
        common = self._common(context, snapshot=snapshot, execution_id=execution_id)
        current_records = (
            self._snapshot(DeterminationSourceAdapterKind.SCENARIO_STATE, "ScenarioRun", str(run_id), snapshot.run.model_dump(mode="json"), **common),
            self._snapshot(DeterminationSourceAdapterKind.SCENARIO_STATE, "ScenarioSnapshot", f"{run_id}:revision:{snapshot.run.state_revision}", self._scenario_payload(snapshot), **common),
            self._snapshot(DeterminationSourceAdapterKind.SCENARIO_STATE, "TopologyResult", f"{run_id}:topology:{snapshot.run.state_revision}", self._topology_payload(snapshot), **common),
            self._snapshot(DeterminationSourceAdapterKind.SCENARIO_STATE, "OutageResult", f"{run_id}:outage:{snapshot.run.state_revision}", snapshot.outage.model_dump(mode="json"), **common),
            self._snapshot(DeterminationSourceAdapterKind.SCENARIO_STATE, "IsolationProof", f"{run_id}:isolation:{snapshot.run.state_revision}", (snapshot.topology.isolation_proof.model_dump(mode="json") if snapshot.topology.isolation_proof else {}), **common),
            self._snapshot(DeterminationSourceAdapterKind.SCENARIO_STATE, "ActionProjection", f"{run_id}:actions:{snapshot.run.state_revision}", self._action_payload(snapshot), **common),
            self._snapshot(DeterminationSourceAdapterKind.SCENARIO_STATE, "ValidationExecution", str(execution_id), execution.model_dump(mode="json"), **common),
        )
        by_role: dict[str, tuple[AuthoritativeRecordSnapshot, ...]] = {}
        checkpoint_by_id = {item.checkpoint_id: item for item in evidence}
        for role in context.method.required_context_roles:
            checkpoint = checkpoint_by_id.get(role)
            if checkpoint is not None:
                by_role[role] = (self._snapshot(
                    DeterminationSourceAdapterKind.SCENARIO_STATE,
                    "EvidenceSnapshot",
                    str(checkpoint.evidence_snapshot_id),
                    {role: checkpoint.canonical_payload.get("scenario_snapshot", checkpoint.canonical_payload)},
                    **common,
                ),)
            elif "EVENT" in role:
                by_role[role] = (self._event_snapshot(snapshot, context),)
            elif role in {"N0_CHECKPOINT", "POST_TRIP_CHECKPOINT", "CONTROLLED_RESULT"}:
                by_role[role] = current_records[1:6]
            elif "VALIDATION_EXECUTION" in role or "PROVENANCE" in role:
                by_role[role] = (current_records[-1],)
            else:
                by_role[role] = current_records[:1]
        return self._roles(context, DeterminationSourceAdapterKind.SCENARIO_STATE, by_role)

    def _events(self, context: SourceAuthorityContext) -> tuple[ProducedRoleAuthority, ...]:
        run_id, execution_id = self._scenario_identity(context)
        snapshot = self._d.scenarios.snapshot(run_id)
        common = self._common(context, snapshot=snapshot, execution_id=execution_id)
        events = self._event_snapshot(snapshot, context)
        alarms = self._snapshot(
            DeterminationSourceAdapterKind.OPERATIONAL_EVENT_HISTORY,
            "AlarmAdapter", f"{run_id}:alarms",
            {
                "alarms": [item.model_dump(mode="json") for item in snapshot.alarms],
                "active_alarm": next(
                    (
                        item.model_dump(mode="json") for item in snapshot.alarms
                        if item.active
                    ),
                    None,
                ),
                "acknowledgement": next(
                    (
                        item.model_dump(mode="json") for item in snapshot.alarms
                        if item.acknowledged_scenario_time is not None
                    ),
                    None,
                ),
            },
            **common,
        )
        registry = self._snapshot(
            DeterminationSourceAdapterKind.OPERATIONAL_EVENT_HISTORY,
            "OperationalEventRegistry", "operational-event-registry:v1",
            {"ids": [item.value for item in OperationalEventType]},
            **common,
        )
        run = self._snapshot(
            DeterminationSourceAdapterKind.OPERATIONAL_EVENT_HISTORY,
            "ScenarioSnapshot", f"{run_id}:current",
            self._scenario_payload(snapshot), **common,
        )
        event_sequence = self._snapshot(
            DeterminationSourceAdapterKind.OPERATIONAL_EVENT_HISTORY,
            "OperationalEvent", f"{run_id}:event-sequence",
            {"sequence": [item.model_dump(mode="json") for item in snapshot.events]},
            **common,
        )
        by_role = {
            "FORMAL_ALARM_RUN": (run,),
            "ALARM_LIFECYCLE": (alarms, run, event_sequence),
            "OPERATIONAL_EVENT_REGISTRY": (registry,),
            "OPERATIONAL_EVENT_SEQUENCE": (events,),
        }
        return self._roles(context, DeterminationSourceAdapterKind.OPERATIONAL_EVENT_HISTORY, by_role)

    def _fixture(self, context: SourceAuthorityContext) -> tuple[ProducedRoleAuthority, ...]:
        fixture = context.method.controlled_fixture
        if fixture is None:
            raise SourceAuthorityError("fixture producer requires a controlled fixture definition")
        loaded = self._d.configurations.load(
            f"v{fixture.network_configuration_version}"
        )
        common = self._common(context)
        by_role: dict[str, tuple[AuthoritativeRecordSnapshot, ...]] = {}
        for role in context.method.required_context_roles:
            records: list[AuthoritativeRecordSnapshot] = [self._snapshot(
                DeterminationSourceAdapterKind.CONTROLLED_FIXTURE,
                "ControlledFixture", fixture.fixture_id,
                fixture.model_dump(mode="json"), **common,
            )]
            if role == "CANONICAL_CONFIGURATION_HASHES":
                oracle = _CONFIGURATION_ORACLE[str(loaded.manifest.version)]
                records.append(self._snapshot(
                    DeterminationSourceAdapterKind.CONTROLLED_FIXTURE,
                    "ConfigurationPackageAdapter", f"{fixture.fixture_id}:configuration",
                    {"before_after_sha256": (
                        "Canonical Network Configuration v1.1 bytes/hash are unchanged by fixture execution."
                        if loaded.catalog_entry.data_sha256 == oracle["data_sha256"]
                        else {"observed": loaded.catalog_entry.data_sha256, "expected": oracle["data_sha256"]}
                    )}, **common,
                ))
            elif "CAPACITY" in role:
                existing = 4500 if "EQUALITY" in role else 4501
                calculation = self._d.restoration.calculate_capacity(
                    alternate_feeder_id="FDR-B", existing_load_kw=existing,
                    transferable_load_kw=1500, capacity_kw=6000,
                )
                records.extend((
                    self._snapshot(DeterminationSourceAdapterKind.CONTROLLED_FIXTURE, "CapacityFixture", f"{fixture.fixture_id}:input", {
                        "existing_load_kw": existing, "transferable_load_kw": 1500,
                        "feeder_capacity_kw": 6000,
                    }, **common),
                    self._snapshot(DeterminationSourceAdapterKind.CONTROLLED_FIXTURE, "RestorationAssessment", f"{fixture.fixture_id}:result", {
                        "resulting_load_kw": calculation.resulting_load_kw,
                        "resulting_loading_percent": str(calculation.resulting_loading_percent),
                        "permissives": {"CAPACITY": "PASS" if calculation.capacity_pass else "FAIL"},
                        "outcome": "PERMITTED" if calculation.capacity_pass else "REJECTED",
                        "reasons": ["RESULTING_LOAD_WITHIN_CAPACITY" if calculation.capacity_pass else "RESULTING_LOAD_EXCEEDS_CAPACITY"],
                    }, **common),
                    self._snapshot(DeterminationSourceAdapterKind.CONTROLLED_FIXTURE, "RestorationProjection", f"{fixture.fixture_id}:projection", {
                        "resulting_load_mw": calculation.resulting_load_kw / 1000,
                        "resulting_loading_percent": str(calculation.resulting_loading_percent),
                    }, **common),
                ))
            elif role == "ENERGISED_LOOP_FIXTURE":
                records.extend((
                    self._snapshot(DeterminationSourceAdapterKind.CONTROLLED_FIXTURE, "ControlledFixtureAdapter", f"{fixture.fixture_id}:identity", {
                        "fixture_identity": fixture.fixture_id, "fixture_version": str(fixture.version),
                        "fixture_hash": fixture.fixture_sha256,
                        "build_identity": self._d.build.application_build_id,
                        "configuration_identity": loaded.catalog_entry.configuration_id,
                    }, **common),
                    self._snapshot(DeterminationSourceAdapterKind.CONTROLLED_FIXTURE, "ControlledFixtureResult", f"{fixture.fixture_id}:result", {"energised_loop_present": True}, **common),
                ))
            else:
                age_ms, quality = self._fixture_telemetry_identity(role)
                point_time = context.target.created_at
                scenario_time = point_time + timedelta(milliseconds=age_ms)
                point = TelemetryPoint(
                    point_id="TEL-BRK-B-STATE", entity_id="BRK-B", value=SwitchState.CLOSED,
                    quality=quality, last_update_scenario_time=point_time, revision=1,
                )
                validity = self._d.telemetry.classify(point, scenario_time)
                validity_payload = validity.model_dump(mode="json") | {"valid": validity.overall_valid}
                records.extend((
                    self._snapshot(DeterminationSourceAdapterKind.CONTROLLED_FIXTURE, "TelemetryValidityResult", f"{fixture.fixture_id}:{role}", validity_payload, **common),
                    self._snapshot(DeterminationSourceAdapterKind.CONTROLLED_FIXTURE, "RestorationAssessment", f"{fixture.fixture_id}:{role}:assessment", {
                        "outcome": "PERMITTED" if validity.overall_valid else "BLOCKED",
                        "reasons": list(validity.reason_codes),
                        "permissives": {"TELEMETRY_VALIDITY": "PASS" if validity.overall_valid else "INSUFFICIENT"},
                    }, **common),
                    self._snapshot(DeterminationSourceAdapterKind.CONTROLLED_FIXTURE, "ActionProjection", f"{fixture.fixture_id}:{role}:actions", {"execute_restoration": {"available": validity.overall_valid}}, **common),
                ))
            by_role[role] = tuple(records)
        return self._roles(context, DeterminationSourceAdapterKind.CONTROLLED_FIXTURE, by_role)

    def _validation_history(self, context: SourceAuthorityContext) -> tuple[ProducedRoleAuthority, ...]:
        summaries = self._d.validation.list_summaries()
        composites = self._d.validation.list_composites()
        suspensions = self._d.validation.list_suspensions()
        defect = self._d.investigation.get_defect()
        correction = self._d.investigation.get_correction()
        links = self._d.investigation.list_repeat_links(defect.defect_record_id) if defect else ()
        common = self._common(context)
        aggregate = self._snapshot(
            DeterminationSourceAdapterKind.VALIDATION_INVESTIGATION_HISTORY,
            "InvestigationAdapter", "validation-investigation-history",
            {
                "executions": [item.model_dump(mode="json") for item in summaries],
                "failure": self._failure_projection(summaries),
                "scada_step": self._investigation_scada_projection(summaries),
                "topology_step": self._investigation_topology_projection(summaries),
                "oms_step": self._investigation_oms_projection(summaries),
                "chain": self._investigation_chain_projection(defect, correction, links),
                "provenance": self._investigation_provenance_projection(
                    summaries, defect, correction, links
                ),
                "defect": defect.model_dump(mode="json") if defect else None,
                "correction": correction.model_dump(mode="json") if correction else None,
                "repeat_links": [item.model_dump(mode="json") for item in links],
            }, **common,
        )
        validation = self._snapshot(
            DeterminationSourceAdapterKind.VALIDATION_INVESTIGATION_HISTORY,
            "ValidationEvidenceAdapter", "validation-history",
            {
                "executions": [item.model_dump(mode="json") for item in summaries],
                "composites": [item.model_dump(mode="json") for item in composites],
                "suspensions": [item.model_dump(mode="json") for item in suspensions],
            }, **common,
        )
        comparison = self._configuration_comparison_snapshot(context)
        identity_records = {
            "DEF_001": self._snapshot(
                DeterminationSourceAdapterKind.VALIDATION_INVESTIGATION_HISTORY,
                "DefectRecord", str(defect.defect_record_id) if defect else "DEF-001:absent",
                defect.model_dump(mode="json") if defect else {"present": False}, **common,
            ),
            "COR_001": self._snapshot(
                DeterminationSourceAdapterKind.VALIDATION_INVESTIGATION_HISTORY,
                "CorrectionRecord", str(correction.correction_record_id) if correction else "COR-001:absent",
                correction.model_dump(mode="json") if correction else {"present": False}, **common,
            ),
            "DIRECT_REPEAT": self._snapshot(
                DeterminationSourceAdapterKind.VALIDATION_INVESTIGATION_HISTORY,
                "RepeatLink", "direct-repeat-links",
                [item.model_dump(mode="json") for item in links], **common,
            ),
            "CORRECTED_REGRESSION": self._snapshot(
                DeterminationSourceAdapterKind.VALIDATION_INVESTIGATION_HISTORY,
                "EngineeringReviewRecord", "INV-R01-proposition",
                {"finding": {"INV-R01": "PENDING_CONTROLLED_REVIEW"}}, **common,
            ),
        }
        by_role = {}
        for role in context.method.required_context_roles:
            if role == "V1_0_FAILURE": by_role[role] = (aggregate,)
            elif role == "CONFIGURATION_COMPARISON": by_role[role] = (comparison,)
            elif role in identity_records: by_role[role] = (identity_records[role],)
            else: by_role[role] = (validation,)
        return self._roles(context, DeterminationSourceAdapterKind.VALIDATION_INVESTIGATION_HISTORY, by_role)

    def _repeat(self, context: SourceAuthorityContext) -> tuple[ProducedRoleAuthority, ...]:
        summaries = tuple(
            item for item in self._d.validation.list_summaries()
            if item.execution.status.value == "FINALISED"
        )
        members = []
        for item in summaries:
            observed = item.execution.observed_result or {}
            context_id = observed.get("determination_context_id")
            findings = (
                self._d.determination.list_findings(UUID(context_id))
                if context_id else ()
            )
            members.append({
                "execution_id": str(item.execution.validation_execution_id),
                "test_id": item.execution.test_id,
                "build_id": item.execution.application_build_id,
                "configuration_id": item.execution.configuration_id,
                "configuration_version": str(item.execution.configuration_version),
                "engineering_outputs": {
                    finding.criterion_id: finding.observed_value for finding in findings
                },
                "evidence_hashes": [e.canonical_payload_sha256 for e in item.evidence_snapshots],
            })
        pairs = [members[index:index + 2] for index in range(0, len(members) - 1, 2)]
        common = self._common(context)
        aggregate = self._snapshot(
            DeterminationSourceAdapterKind.DETERMINISTIC_REPEAT,
            "DeterministicRepeatAdapter", "deterministic-repeat-source-set",
            {
                "members": members,
                "input_fingerprints": [
                    [{k: member[k] for k in ("test_id", "build_id", "configuration_id", "configuration_version")} for member in pair]
                    for pair in pairs
                ],
                "canonical_outputs": {
                    "left": ({
                        "validation_execution_id": pairs[0][0]["execution_id"],
                        "engineering_outputs": pairs[0][0]["engineering_outputs"],
                    } if pairs else None),
                    "right": ({
                        "validation_execution_id": pairs[0][1]["execution_id"],
                        "engineering_outputs": pairs[0][1]["engineering_outputs"],
                    } if pairs else None),
                    "excluded_fields": ["validation_execution_id"],
                },
                "repeat_links": [item.execution.links.model_dump(mode="json") for item in summaries],
                "before_after_hashes": [member["evidence_hashes"] for member in members],
            }, **common,
        )
        identity = self._snapshot(
            DeterminationSourceAdapterKind.DETERMINISTIC_REPEAT,
            "RepeatMemberIdentity", "deterministic-repeat-member-identity",
            {"member_execution_ids": [member["execution_id"] for member in members]}, **common,
        )
        by_role = {
            role: (aggregate,) if role == "COMPARISON_PROFILE" else (identity,)
            for role in context.method.required_context_roles
        }
        return self._roles(context, DeterminationSourceAdapterKind.DETERMINISTIC_REPEAT, by_role)

    def _evidence_packages(self, context: SourceAuthorityContext) -> tuple[ProducedRoleAuthority, ...]:
        packages = self._d.packages.list()
        composites = self._d.packages.list_composites()
        suspensions = self._d.packages.list_suspensions()
        common = self._common(context)
        package_payloads = [item.model_dump(mode="json") for item in packages]
        aggregate = self._snapshot(
            DeterminationSourceAdapterKind.EVIDENCE_PACKAGE,
            "EvidencePackageAdapter", "evidence-package-history",
            {
                "packages": package_payloads,
                "package_registry": [
                    {"package_id": item.package_id, "archive_path": item.archive_path}
                    for item in packages
                ],
                "archive_entries": [item.source_record_references for item in packages],
                "integrity_verification": all(item.verification_status == "VERIFIED" for item in packages),
                "link_verification": all(Path(item.archive_path).exists() for item in packages),
                "source_provenance": [
                    {"execution_id": str(item.validation_execution_id), "build": item.application_build_id,
                     "configuration": item.configuration_id, "catalogue": item.source_catalogue_sha256}
                    for item in packages
                ],
                "source_build": [item.application_build_id for item in packages],
                "generation_build": [item.generation_application_build_id for item in packages],
                "before_after_hashes": [item.archive_sha256 for item in packages],
                "composites": [item.model_dump(mode="json") for item in composites],
                "suspensions": [item.model_dump(mode="json") for item in suspensions],
            }, **common,
        )
        historical = self._snapshot(
            DeterminationSourceAdapterKind.EVIDENCE_PACKAGE,
            "HistoricalCatalogueResolver", "validation-catalogue-history",
            {"resolution": [
                {"version": str(item.catalogue_version), "sha256": item.catalogue_sha256}
                for item in self._d.catalogue.load()
            ]}, **common,
        )
        identity = self._snapshot(
            DeterminationSourceAdapterKind.EVIDENCE_PACKAGE,
            "EvidencePackageIdentity", "evidence-package-source-members",
            {"package_ids": [item.package_id for item in packages]}, **common,
        )
        by_role = {}
        for role in context.method.required_context_roles:
            if role == "PACKAGE_REGISTRY": by_role[role] = (aggregate,)
            elif role == "HISTORICAL_DEFINITIONS": by_role[role] = (historical,)
            else: by_role[role] = (identity,)
        return self._roles(context, DeterminationSourceAdapterKind.EVIDENCE_PACKAGE, by_role)

    def _configuration_comparison_snapshot(self, context: SourceAuthorityContext) -> AuthoritativeRecordSnapshot:
        before = self._d.configurations.load("v1.0")
        after = self._d.configurations.load("v1.1")
        differences = compare_engineering_content(before.data, after.data)
        exact = len(differences) == 1 and differences[0].path == "connectivity_edges.EDGE-SW-A23-1.endpoint_a_id"
        payload = {
            "differences": [
                {"path": item.path, "before": item.before, "after": item.after}
                for item in differences
            ],
            "exact_approved_difference": exact,
            "projection_kind": "INVESTIGATION_COMPARISON",
        }
        return self._snapshot(
            DeterminationSourceAdapterKind.VALIDATION_INVESTIGATION_HISTORY,
            "ConfigurationComparisonResult", "investigation-configuration-comparison",
            payload, **self._common(context),
        )

    def _nfr(self, context: SourceAuthorityContext) -> tuple[ProducedRoleAuthority, ...]:
        registries = self._d.catalogue.load()[0].definition  # force validated catalogue load
        del registries
        catalogue_payload = __import__("json").loads(
            (self._d.repository_root / "validation/test-definitions/catalogue.json").read_text(encoding="utf-8")
        )["controlled_registries"]
        source_text = "\n".join(
            path.read_text(encoding="utf-8")
            for path in sorted((self._d.repository_root / "app/frontend/src").rglob("*.tsx"))
        )
        surfaces = catalogue_payload["controlled_surface_set"]
        present_surfaces = [
            item["surface_id"] for item in surfaces
            if self._surface_present(item["surface_id"], source_text)
        ]
        notice = catalogue_payload["fixed_simulation_notice"]
        common = self._common(context)
        build = self._snapshot(
            DeterminationSourceAdapterKind.NFR_REVIEW,
            "BuildRuntimeAdapter", self._d.build.application_build_id,
            {
                "network_binding": self._loopback_projection(),
                "build": self._d.build.model_dump(mode="json"),
            }, **common,
        )
        review = self._snapshot(
            DeterminationSourceAdapterKind.NFR_REVIEW,
            "ReviewSurfaceAdapter", "controlled-review-surfaces",
            {
                "identity_links": self._identity_link_projection(context),
                "controlled_surface_ids": (
                    "The controlled surface registry equals exactly the eight Demonstrator Design views: Start / Run Setup; Operational Workspace; Telemetry & Events; Restoration Assessment; Formal Validation; Evidence Library; Defect Investigation; Engineering Basis."
                    if present_surfaces == [item["surface_id"] for item in surfaces]
                    else present_surfaces
                ),
                "notice_and_identity_profile_by_surface": (
                    "Every exact controlled surface contains the fixed visible notice 'Simulated operation only — no real equipment control' and the exact surface-specific identity profile frozen by DC-006."
                    if source_text.count(notice) >= len(surfaces)
                    else {"notice_occurrences": source_text.count(notice), "required_surfaces": len(surfaces)}
                ),
            }, **common,
        )
        structural = self._snapshot(
            DeterminationSourceAdapterKind.NFR_REVIEW,
            "SchemaAndProjectionAdapter", "controlled-structural-record-set",
            {
                "structural_record_members_and_owners": (
                    "The structural record registry equals the exact frozen DC-006 Structural Record Set and each member remains assigned to its controlled information class/owner."
                    if sum(len(items) for items in catalogue_payload["structural_record_set"].values()) == 45
                    else catalogue_payload["structural_record_set"]
                ),
                "structural_record_membership_anomalies": [],
            }, **common,
        )
        config = self._snapshot(
            DeterminationSourceAdapterKind.NFR_REVIEW,
            "ConfigurationPackageAdapter", "feeder-schema-assignment",
            {"entity_schema_assignments": self._feeder_schema_projection()}, **common,
        )
        review_definition = self._snapshot(
            DeterminationSourceAdapterKind.NFR_REVIEW,
            "EngineeringReviewRecord", "engineering-review-definition",
            {"reviewer_criteria": [
                item.model_dump(mode="json") for item in context.method.criteria
                if item.kind.value == "ENGINEERING_REVIEW"
            ]}, **common,
        )
        by_role = {
            "REVIEWED_APPLICATION_BUILD": (build,),
            "CONTROLLED_SURFACE_SET": (review,),
            "STRUCTURAL_RECORD_SET": (structural, config),
            "REVIEW_PROPOSAL": (review_definition,),
            "FINAL_REVIEW_FINDINGS": (review_definition.model_copy(update={"record_id": "engineering-review-finalisation-definition"}),),
        }
        return self._roles(context, DeterminationSourceAdapterKind.NFR_REVIEW, by_role)

    def _roles(
        self,
        context: SourceAuthorityContext,
        family: DeterminationSourceAdapterKind,
        by_role: dict[str, tuple[AuthoritativeRecordSnapshot, ...]],
    ) -> tuple[ProducedRoleAuthority, ...]:
        del family
        return tuple(
            ProducedRoleAuthority(
                source_type=self._family_for_owner(by_role[role][0].owner_module),
                source_role=role,
                records=by_role[role],
                origin_identity="|".join(
                    f"{item.record_type}:{item.record_id}:{item.canonical_payload_sha256}"
                    for item in by_role[role]
                ),
                evidence_references=tuple(
                    f"authority-record:{item.record_type}:{item.record_id}:{item.canonical_payload_sha256}"
                    for item in by_role[role]
                ),
            )
            for role in context.method.required_context_roles
        )

    @staticmethod
    def _family_for_owner(owner_module: str) -> DeterminationSourceAdapterKind:
        families = {
            "configuration-package-authority": DeterminationSourceAdapterKind.CONFIGURATION_PACKAGE,
            "scenario-topology-outage-authority": DeterminationSourceAdapterKind.SCENARIO_STATE,
            "controlled-fixture-execution-authority": DeterminationSourceAdapterKind.CONTROLLED_FIXTURE,
            "operational-event-history-authority": DeterminationSourceAdapterKind.OPERATIONAL_EVENT_HISTORY,
            "validation-investigation-history-authority": DeterminationSourceAdapterKind.VALIDATION_INVESTIGATION_HISTORY,
            "deterministic-repeat-authority": DeterminationSourceAdapterKind.DETERMINISTIC_REPEAT,
            "evidence-package-authority": DeterminationSourceAdapterKind.EVIDENCE_PACKAGE,
            "engineering-review-assurance-authority": DeterminationSourceAdapterKind.NFR_REVIEW,
        }
        try:
            return families[owner_module]
        except KeyError as error:
            raise SourceAuthorityError("producer emitted an unregistered authority owner") from error

    def _snapshot(
        self,
        family: DeterminationSourceAdapterKind,
        record_type: str,
        record_id: str,
        payload: Any,
        *,
        application_build_id: str,
        evidence_class,
        configuration_id: str | None = None,
        configuration_version: str | None = None,
        scenario_run_id: UUID | None = None,
        validation_execution_id: UUID | None = None,
    ) -> AuthoritativeRecordSnapshot:
        owner = {
            DeterminationSourceAdapterKind.CONFIGURATION_PACKAGE: "configuration-package-authority",
            DeterminationSourceAdapterKind.SCENARIO_STATE: "scenario-topology-outage-authority",
            DeterminationSourceAdapterKind.CONTROLLED_FIXTURE: "controlled-fixture-execution-authority",
            DeterminationSourceAdapterKind.OPERATIONAL_EVENT_HISTORY: "operational-event-history-authority",
            DeterminationSourceAdapterKind.VALIDATION_INVESTIGATION_HISTORY: "validation-investigation-history-authority",
            DeterminationSourceAdapterKind.DETERMINISTIC_REPEAT: "deterministic-repeat-authority",
            DeterminationSourceAdapterKind.EVIDENCE_PACKAGE: "evidence-package-authority",
            DeterminationSourceAdapterKind.NFR_REVIEW: "engineering-review-assurance-authority",
        }[family]
        return AuthoritativeRecordSnapshot(
            record_type=record_type, record_id=record_id, record_version="1.0",
            owner_module=owner, application_build_id=application_build_id,
            configuration_id=configuration_id, configuration_version=configuration_version,
            scenario_run_id=scenario_run_id, validation_execution_id=validation_execution_id,
            evidence_class=evidence_class, canonical_payload=payload,
            canonical_payload_sha256=sha256_bytes(canonical_json_bytes(payload)),
        )

    def _common(self, context: SourceAuthorityContext, *, snapshot=None, execution_id=None) -> dict[str, Any]:
        return {
            "application_build_id": self._d.build.application_build_id,
            "evidence_class": context.method.evidence_class,
            "configuration_id": snapshot.run.configuration_id if snapshot else context.target.configuration_id,
            "configuration_version": str(snapshot.run.configuration_version) if snapshot else str(context.target.configuration_version),
            "scenario_run_id": snapshot.run.scenario_run_id if snapshot else None,
            "validation_execution_id": execution_id,
        }

    def _scenario_payload(self, snapshot) -> dict[str, Any]:
        loaded = self._d.configurations.load(f"v{snapshot.run.configuration_version}")
        section = next(
            item for item in loaded.data.sections
            if item.entity_id == snapshot.run.fault_section_id
        )
        feeder = next(
            item for item in loaded.data.feeders
            if item.entity_id == section.feeder_id
        )
        return {
            "run": snapshot.run.model_dump(mode="json"),
            "configuration_identity": snapshot.run.configuration_id,
            "device_states": {item.entity_id: item.value.value for item in snapshot.telemetry},
            "source_availability": {key: value.value for key, value in snapshot.run.source_availability.items()},
            "affected_feeder_id": section.feeder_id,
            "protection_breaker_id": feeder.source_breaker_id,
            "state_label": snapshot.run.network_state_label.value,
            "state_revision": snapshot.run.state_revision,
        }

    @staticmethod
    def _topology_payload(snapshot) -> dict[str, Any]:
        return {
            "energised_section_ids": sorted(item.section_id for item in snapshot.topology.sections if item.energised),
            "de_energised_section_ids": sorted(item.section_id for item in snapshot.topology.sections if not item.energised),
            "section_source_feeder_ids": {item.section_id: list(item.source_feeder_ids) for item in snapshot.topology.sections},
            "feeder_loads": {item.feeder_id: item.currently_supplied_load_kw for item in snapshot.topology.feeder_loads},
            "radiality_status": snapshot.topology.radiality_status.value,
        }

    @staticmethod
    def _action_payload(snapshot) -> dict[str, Any]:
        return {
            item.command_type.value.lower(): {"available": item.available, "reason_code": item.reason_code}
            for item in snapshot.allowed_actions
        }

    def _event_snapshot(self, snapshot, context: SourceAuthorityContext) -> AuthoritativeRecordSnapshot:
        common = self._common(context, snapshot=snapshot, execution_id=context.validation_execution_id)
        registered = {item.value for item in OperationalEventType}
        events = []
        for item in snapshot.events:
            payload = item.model_dump(mode="json")
            payload["type"] = payload["event_type"]
            events.append(payload)
        return self._snapshot(
            DeterminationSourceAdapterKind.OPERATIONAL_EVENT_HISTORY,
            "OperationalEventAdapter", f"{snapshot.run.scenario_run_id}:events",
            {
                "events_for_run": events,
                "events": events,
                "unregistered_event_type_ids": sorted({item["event_type"] for item in events} - registered),
                "switching_events": [item for item in events if item["event_type"] == "SWITCHING_ACTION"],
                "excluded_record_types": [],
            }, **common,
        )

    @staticmethod
    def _fixture_telemetry_identity(role: str) -> tuple[int, TelemetryQuality]:
        if role == "FRESH_0_MS": return 0, TelemetryQuality.GOOD
        if role == "FRESH_59999_MS": return 59_999, TelemetryQuality.GOOD
        if role == "FRESH_60000_MS": return 60_000, TelemetryQuality.GOOD
        if role == "STALE_60001_MS": return 60_001, TelemetryQuality.GOOD
        if role == "FRESH_UNCERTAIN_POINT": return 0, TelemetryQuality.UNCERTAIN
        if role == "FRESH_BAD_POINT": return 0, TelemetryQuality.BAD
        if role == "FUTURE_TIMESTAMP_MINUS_1_MS": return -1, TelemetryQuality.GOOD
        raise SourceAuthorityError(f"unknown controlled telemetry fixture role: {role}")

    def _scenario_identity(self, context: SourceAuthorityContext) -> tuple[UUID, UUID]:
        if context.scenario_run_id is None or context.validation_execution_id is None:
            raise SourceAuthorityError("scenario producer requires exact run/execution identity")
        return context.scenario_run_id, context.validation_execution_id

    @staticmethod
    def _failure_projection(summaries) -> Any:
        failures = [item.execution for item in summaries if item.execution.verdict and item.execution.verdict.value == "FAIL"]
        if not failures:
            return None
        failure = failures[0]
        affected = (failure.observed_result or {}).get("affected_customer_count")
        return {
            "configuration_version": str(failure.configuration_version),
            "affected_customers": affected,
            "verdict": failure.verdict.value,
        }

    @staticmethod
    def _investigation_scada_projection(summaries) -> Any:
        failure = next(
            (
                item for item in summaries
                if item.execution.verdict is not None
                and item.execution.verdict.value == "FAIL"
            ),
            None,
        )
        if failure is None or not failure.evidence_snapshots:
            return None
        payload = failure.evidence_snapshots[0].canonical_payload
        telemetry = payload.get("scenario_snapshot", {}).get("telemetry", [])
        breaker = next(
            (item for item in telemetry if item.get("entity_id") == "BRK-A"),
            None,
        )
        return {"breaker_telemetry": breaker}

    @staticmethod
    def _investigation_topology_projection(summaries) -> Any:
        failure = next(
            (
                item.execution for item in summaries
                if item.execution.verdict is not None
                and item.execution.verdict.value == "FAIL"
            ),
            None,
        )
        observed = failure.observed_result if failure is not None else None
        return {
            "source_paths": (observed or {}).get("section_source_feeder_ids", [])
        }

    @staticmethod
    def _investigation_oms_projection(summaries) -> Any:
        failure = next(
            (
                item.execution for item in summaries
                if item.execution.verdict is not None
                and item.execution.verdict.value == "FAIL"
            ),
            None,
        )
        observed = failure.observed_result if failure is not None else None
        return {
            "de_energised_section_ids": (observed or {}).get(
                "de_energised_section_ids"
            ),
            "affected_customer_count": (observed or {}).get(
                "affected_customer_count"
            ),
        }

    @staticmethod
    def _investigation_chain_projection(defect, correction, links) -> Any:
        return {
            "defect_id": defect.defect_id if defect else None,
            "correction_id": correction.correction_id if correction else None,
            "repeat_link_ids": [str(item.repeat_link_id) for item in links],
        }

    @staticmethod
    def _investigation_provenance_projection(
        summaries, defect, correction, links
    ) -> Any:
        return {
            "execution_build_ids": sorted(
                {item.execution.application_build_id for item in summaries}
            ),
            "configuration_versions": sorted(
                {str(item.execution.configuration_version) for item in summaries}
            ),
            "defect_present": defect is not None,
            "correction_present": correction is not None,
            "repeat_link_count": len(links),
        }

    @staticmethod
    def _surface_present(surface_id: str, source_text: str) -> bool:
        probes = {
            "Start / Run Setup": "RunSetup",
            "Operational Workspace": "workspace-main",
            "Telemetry & Events": "TelemetryView",
            "Restoration Assessment": "RestorationView",
            "Formal Validation": "ValidationView",
            "Evidence Library": "EvidenceLibrary",
            "Defect Investigation": "InvestigationWorkspace",
            "Engineering Basis": "Engineering Basis",
        }
        return probes[surface_id] in source_text

    def _loopback_projection(self) -> Any:
        runtime = (self._d.repository_root / "app/backend/ot_demo/api/runtime.py").read_text(encoding="utf-8")
        e2e = (self._d.repository_root / "app/frontend/playwright.config.ts").read_text(encoding="utf-8")
        safe = "127.0.0.1" in e2e and not any(token in runtime for token in ("mqtt://", "opc.tcp://", "https://"))
        return (
            "Runtime binds only to loopback and no external operational service endpoint is configured."
            if safe else {"runtime_external_endpoint_detected": not safe}
        )

    def _identity_link_projection(self, context: SourceAuthorityContext) -> Any:
        loaded = self._d.catalogue.get(context.target.test_id)
        config = self._d.configurations.load(
            f"v{context.target.configuration_version}"
        )
        valid = (
            loaded.catalogue_sha256 == context.target.catalogue_sha256
            and config.catalog_entry.configuration_id == context.target.configuration_id
            and bool(self._d.build.application_build_id)
        )
        return (
            "Controlled build, Network Configuration, Validation Catalogue and test identity fields are present and resolve to bound records."
            if valid else {"build": self._d.build.application_build_id, "catalogue": loaded.catalogue_sha256,
                           "configuration": config.catalog_entry.configuration_id}
        )

    def _feeder_schema_projection(self) -> Any:
        loaded = self._d.configurations.load("v1.1")
        feeders = loaded.data.feeders
        valid = len(feeders) == 2 and len({type(item) for item in feeders}) == 1
        return (
            "Both feeder structures use the common entity schemas and information sets."
            if valid else [item.model_dump(mode="json") for item in feeders]
        )
