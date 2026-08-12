"""Registered QA-050 producers over the application's controlling authorities.

Only this module creates :class:`AuthoritativeRecordSnapshot` instances used by
DC-006 campaign determination.  Its public input is an attempt plus source
identity/context; it never accepts an observation payload or owner declaration.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
import json
from pathlib import Path, PurePosixPath
import re
from typing import Any, Mapping
from uuid import UUID
from zipfile import ZipFile, BadZipFile

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
from ...infrastructure.hashing import sha256_file
from ...infrastructure.investigation_repository import InvestigationRepository
from ...infrastructure.validation_repository import ValidationRepository
from ..restoration.service import RestorationService
from ..telemetry.models import TelemetryPoint
from ..telemetry.service import TelemetryValidityService
from ..topology import TopologyInputs, TopologyService
from .catalogue import ValidationCatalogueResolver
from .source_adapters import AuthoritativeSourceAdapterRegistry, SourceAdapterError
from .structural_registry import resolved_structural_registry
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
    surface_registry_path: Path | None = None
    structural_registry: Mapping[str, Mapping[str, str]] | None = None
    package_archive_root: Path | None = None


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
        self._verify_selector_closure(context, produced)
        return produced

    @staticmethod
    def _verify_selector_closure(
        context: SourceAuthorityContext,
        produced: tuple[ProducedRoleAuthority, ...],
    ) -> None:
        """Require one and only one producer-owned path for every machine criterion."""

        for criterion in context.method.criteria:
            if criterion.kind.value != "MACHINE_COMPARISON":
                continue
            matches = 0
            errors: list[str] = []
            for authority in produced:
                try:
                    AuthoritativeSourceAdapterRegistry.resolve_records(
                        authority.records, criterion.source_selector
                    )
                except SourceAdapterError as error:
                    errors.append(f"{authority.source_role}: {error}")
                else:
                    matches += 1
            if matches > 1:
                raise SourceAuthorityError(
                    f"criterion {criterion.criterion_id} selector must resolve through "
                    f"at most one authoritative role at capture time; "
                    f"resolved={matches}; errors={errors}"
                )

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
        records = self._scenario_authority_records(
            context, snapshot, execution, evidence
        )
        return self._primary_role_authority(
            context, DeterminationSourceAdapterKind.SCENARIO_STATE, records
        )

    def _scenario_authority_records(
        self, context: SourceAuthorityContext, snapshot, execution, evidence
    ) -> tuple[AuthoritativeRecordSnapshot, ...]:
        common = self._common(
            context, snapshot=snapshot,
            execution_id=execution.validation_execution_id,
        )
        checkpoint_payloads = {}
        for item in evidence:
            payload = dict(item.canonical_payload.get(
                "scenario_snapshot", item.canonical_payload
            ))
            observed = item.canonical_payload.get("observed_values", {})
            topology = payload.get("topology", {})
            isolation = topology.get("isolation_proof") or {}
            payload.update({
                "fault": {
                    "section_id": observed.get("selected_fault_section_id"),
                    "active": payload.get("run", {}).get("fault_active"),
                },
                "boundary_evidence": observed.get("boundary_evidence"),
                "source_paths": isolation.get("active_source_paths"),
                "isolation": observed.get("isolated"),
                "device_states": {
                    point["entity_id"]: point["value"]
                    for point in payload.get("telemetry", [])
                },
                "allowed_actions": self._action_payload_from_evidence(payload),
                "restoration_assessment": observed,
            })
            checkpoint_payloads[item.checkpoint_id] = payload
        checkpoint_times = {
            item.checkpoint_id: item.scenario_time.isoformat() for item in evidence
        }
        lifecycle = self._d.scenarios.command_lifecycle(
            snapshot.run.scenario_run_id
        )
        command_results = tuple(lifecycle["results"])
        replay_comparisons = tuple(lifecycle["replay_comparisons"])
        command_snapshots = tuple(result.snapshot for result in command_results)
        latest_assessment = (
            self._assessment_payload(
                snapshot.restoration_assessments[-1], snapshot
            )
            if snapshot.restoration_assessments else None
        )
        if latest_assessment is not None and latest_assessment["affected_feeder_id"] is None:
            latest_assessment["affected_feeder_id"] = self._scenario_payload(
                snapshot
            )["affected_feeder_id"]
        devices = {
            item.entity_id: item.value.value for item in snapshot.telemetry
        }
        actions = self._action_payload(snapshot)
        action_history = tuple(
            self._action_payload(item) for item in command_snapshots
        )
        isolation_history = tuple(
            item.topology.isolation_proof.model_dump(mode="json")
            for item in command_snapshots
            if item.topology.isolation_proof is not None
        )
        event_payload = self._event_snapshot(snapshot, context).canonical_payload
        validation_payload = execution.model_dump(mode="json") | {
            "provenance": execution.model_dump(mode="json"),
            "configuration": {
                "id": execution.configuration_id,
                "version": str(execution.configuration_version),
            },
            "catalogue": {
                "version": str(execution.catalogue_version),
                "sha256": execution.catalogue_sha256,
            },
            "test": {
                "id": execution.test_id,
                "definition_sha256": execution.test_definition_sha256,
            },
            "case": execution.case_id,
            "run": str(execution.scenario_run_id),
        }
        scenario_payload = self._scenario_payload(snapshot) | {
            "selected_fault_section_id": snapshot.run.fault_section_id,
            "fault_type": snapshot.run.fault_type.value,
            "mode": snapshot.run.mode.value,
            "checkpoints": checkpoint_times,
            "assessment_inputs": latest_assessment,
            "before_after": {
                "checkpoints": checkpoint_payloads,
                "current": self._scenario_payload(snapshot),
                "command_snapshots": [
                    self._scenario_payload(item) | {
                        "topology": self._topology_payload(item),
                        "outage": item.outage.model_dump(mode="json"),
                        "new_event_types": [
                            event.event_type.value
                            for event in item.events
                            if event.event_id in set(result.new_event_ids)
                        ],
                    }
                    for result, item in zip(
                        command_results, command_snapshots, strict=True
                    )
                ],
            },
        }
        current_validation = {
            "run_id": str(execution.scenario_run_id),
            "execution_id": str(execution.validation_execution_id),
            "build_identity": execution.application_build_id,
            "catalogue_identity": execution.catalogue_sha256,
            "test_identity": execution.test_definition_sha256,
            "method_identity": context.method.method_sha256,
            "configuration_identity": execution.configuration_id,
            "immutable_result_identity": str(execution.executed_result_id) if execution.executed_result_id else None,
            "defect_id": execution.links.defect_id,
            "correction_id": execution.links.correction_id,
            "repeat_of_execution_id": str(execution.links.repeat_of_execution_id) if execution.links.repeat_of_execution_id else None,
        }
        current_scenario = {
            "configuration_identity": snapshot.run.configuration_id,
            "post_trip_input_fingerprint": {
                "fault_section_id": snapshot.run.fault_section_id,
                "scenario_time": snapshot.run.scenario_time.isoformat(),
            },
            "telemetry": {
                item.entity_id: item.model_dump(mode="json")
                for item in snapshot.telemetry
            },
            "post_trip": {
                "topology": self._topology_payload(snapshot),
                "outage": snapshot.outage.model_dump(mode="json"),
                "expected_observed_comparison": execution.observed_result,
            },
            "configuration_difference_role": "CONTROLLED_PACKAGE_IDENTITY",
            "source_paths": self._topology_payload(snapshot)["section_source_feeder_ids"],
            "authority_path": "configuration→topology/source-path→outage/customer-zone",
        }
        raw: dict[str, Any] = {
            "ScenarioRun": scenario_payload,
            "ScenarioSnapshot": scenario_payload,
            "TopologyResult": self._topology_payload(snapshot),
            "OutageResult": snapshot.outage.model_dump(mode="json") | {
                "selected_fault_section_id": snapshot.run.fault_section_id,
                "affected_customer_zone_ids": [
                    item.customer_zone_id
                    for item in snapshot.outage.affected_customer_zones
                ],
            },
            "ActionProjection": actions | {"history": list(action_history)},
            "ValidationExecution": validation_payload,
            "OperationalEventAdapter": event_payload,
            "OperationalEventRegistry": {"ids": [item.value for item in OperationalEventType]},
            "CurrentValidationExecutionAdapter": current_validation,
            "CurrentScenarioExecutionAdapter": current_scenario,
            "TelemetrySnapshot": {item.entity_id: item.model_dump(mode="json") for item in snapshot.telemetry},
            "DeviceState": devices,
            "CommandAvailability": actions,
        }
        if snapshot.topology.isolation_proof is not None:
            proof_payload = snapshot.topology.isolation_proof.model_dump(mode="json")
            telemetry_by_entity = {item.entity_id: item for item in snapshot.telemetry}
            proof_payload["boundary_evidence"] = {
                item["boundary_device_id"]: item | {
                    "freshness": item["freshness_status"],
                    "evidence_state": item["proof_status"],
                    "age_ms": int(
                        (
                            snapshot.run.scenario_time
                            - telemetry_by_entity[item["boundary_device_id"]].last_update_scenario_time
                        ).total_seconds() * 1000
                    ),
                }
                for item in proof_payload["boundary_evaluations"]
            }
            raw["IsolationProof"] = proof_payload | {
                "lifecycle": list(isolation_history)
            }
        if checkpoint_payloads:
            raw["EvidenceSnapshot"] = checkpoint_payloads
        if event_payload["events_for_run"]:
            raw["OperationalEvent"] = {
                "sequence": event_payload["events_for_run"]
            }
        if snapshot.alarms:
            alarm_payload = {
                "active_alarm": next(
                    (item.model_dump(mode="json") for item in snapshot.alarms if item.active),
                    None,
                ),
            }
            acknowledgement = next((
                item.model_dump(mode="json")
                for item in snapshot.alarms
                if item.acknowledged_scenario_time
            ), None)
            if acknowledgement is not None:
                alarm_payload["acknowledgement"] = acknowledgement
            raw["AlarmAdapter"] = alarm_payload
        if latest_assessment is not None:
            raw["RestorationAssessment"] = latest_assessment | {
                "before_after": [
                    self._assessment_payload(item, snapshot)
                    for item in snapshot.restoration_assessments
                ],
                "replacement": latest_assessment,
            }
        if command_results:
            raw["CommandResult"] = {
                "results": [item.model_dump(mode="json") for item in command_results],
                "accepted": command_results[-1].accepted,
                "reason": command_results[-1].reason,
            }
            raw["ScenarioRevisionSequence"] = {
                "results": [
                    {
                        "command_id": str(item.command_id),
                        "prior_revision": item.prior_revision,
                        "current_revision": item.current_revision,
                        "topology_sha256": sha256_bytes(canonical_json_bytes(
                            item.snapshot.topology.model_dump(mode="json")
                        )),
                    }
                    for item in command_results
                ],
                "relevant_change": checkpoint_times,
                "sequence": checkpoint_times,
            }
        execution_results = tuple(
            item for item in command_results
            if self._command_emitted_tie_close(item)
        )
        if len(execution_results) == 1:
            executed = execution_results[0].snapshot
            assessment = next(
                item for item in executed.restoration_assessments
                if item.assessment_id in set(
                    execution_results[0].new_assessment_ids
                ) or item.assessment_id == next(
                    (
                        event.assessment_id for event in executed.events
                        if event.event_id in set(execution_results[0].new_event_ids)
                        and event.assessment_id is not None
                    ),
                    None,
                )
            )
            raw["PostExecutionSnapshot"] = {
                "topology": self._topology_payload(executed),
                "outage": executed.outage.model_dump(mode="json"),
                "restored_customer_delta": executed.outage.restored_customer_delta,
                "tie_device_id": assessment.candidate.tie_device_id,
            }
        invalidation_results = tuple(
            item for item in command_results
            if self._command_emitted_event(
                item, "RESTORATION_ASSESSMENT_INVALIDATED"
            )
        )
        if snapshot.restoration_invalidations and invalidation_results:
            raw["AssessmentInvalidationAdapter"] = {
                "records": [
                    item.model_dump(mode="json")
                    for item in snapshot.restoration_invalidations
                ],
                "events": [
                    item for item in event_payload["events_for_run"]
                    if item["event_type"] == "RESTORATION_ASSESSMENT_INVALIDATED"
                ],
                "command_result": invalidation_results[-1].model_dump(mode="json"),
            }
        if replay_comparisons:
            raw["CommandResultReplayComparison"] = {
                "comparisons": list(replay_comparisons)
            }
        return tuple(
            self._snapshot(
                DeterminationSourceAdapterKind.SCENARIO_STATE,
                record_type, f"{snapshot.run.scenario_run_id}:{record_type}",
                payload, **common,
            )
            for record_type, payload in raw.items()
        )


    def _events(self, context: SourceAuthorityContext) -> tuple[ProducedRoleAuthority, ...]:
        run_id, execution_id = self._scenario_identity(context)
        snapshot = self._d.scenarios.snapshot(run_id)
        common = self._common(context, snapshot=snapshot, execution_id=execution_id)
        events = self._event_snapshot(snapshot, context)
        alarm_payload = {
                "alarms": [item.model_dump(mode="json") for item in snapshot.alarms],
                "active_alarm": next(
                    (
                        item.model_dump(mode="json") for item in snapshot.alarms
                        if item.active
                    ),
                    None,
                ),
            }
        acknowledgement = next((
            item.model_dump(mode="json") for item in snapshot.alarms
            if item.acknowledged_scenario_time is not None
        ), None)
        if acknowledgement is not None:
            alarm_payload["acknowledgement"] = acknowledgement
        alarms = self._snapshot(
            DeterminationSourceAdapterKind.OPERATIONAL_EVENT_HISTORY,
            "AlarmAdapter", f"{run_id}:alarms", alarm_payload, **common,
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
        records: list[AuthoritativeRecordSnapshot] = [self._snapshot(
            DeterminationSourceAdapterKind.CONTROLLED_FIXTURE,
            "ControlledFixture", fixture.fixture_id,
            fixture.model_dump(mode="json") | {
                "input_evidence": list(fixture.controlled_inputs),
            }, **common,
        )]
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
        if fixture.fixture_id == "FIX-RST-RADIAL-001":
            normal = TopologyService.normal_inputs(loaded.data)
            states = dict(normal.device_states)
            states["TS-01"] = SwitchState.CLOSED
            loop_topology = TopologyService().calculate(
                loaded,
                TopologyInputs(
                    device_states=states,
                    source_availability=normal.source_availability,
                ),
            )
            radial = self._d.restoration.evaluate_radiality(loop_topology)
            records.extend((
                self._snapshot(DeterminationSourceAdapterKind.CONTROLLED_FIXTURE, "ControlledFixtureAdapter", f"{fixture.fixture_id}:identity", {
                    "fixture_identity": fixture.fixture_id,
                    "fixture_version": str(fixture.version),
                    "fixture_hash": fixture.fixture_sha256,
                    "build_identity": self._d.build.application_build_id,
                    "configuration_identity": loaded.catalog_entry.configuration_id,
                    "configuration_hash": loaded.catalog_entry.data_sha256,
                }, **common),
                self._snapshot(DeterminationSourceAdapterKind.CONTROLLED_FIXTURE, "ControlledFixtureResult", f"{fixture.fixture_id}:result", {
                    "energised_loop_present": loop_topology.radiality_status.value == "UNINTENDED_LOOP",
                }, **common),
                self._snapshot(DeterminationSourceAdapterKind.CONTROLLED_FIXTURE, "TopologyResult", f"{fixture.fixture_id}:topology", loop_topology.model_dump(mode="json"), **common),
                self._snapshot(DeterminationSourceAdapterKind.CONTROLLED_FIXTURE, "RestorationAssessment", f"{fixture.fixture_id}:assessment", {
                    "permissives": {"RADIAL_TOPOLOGY": radial.status.value},
                    "outcome": "REJECTED" if radial.status is PermissiveStatus.FAIL else "PERMITTED",
                    "reasons": list(radial.reason_codes),
                }, **common),
                self._snapshot(DeterminationSourceAdapterKind.CONTROLLED_FIXTURE, "ActionProjection", f"{fixture.fixture_id}:actions", {
                    "execute_restoration": {"available": radial.status is PermissiveStatus.PASS},
                }, **common),
            ))
        elif "CAP-" in fixture.fixture_id:
            existing = 4500 if "EQUAL" in fixture.fixture_id else 4501
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
        else:
            validity_by_key: dict[str, Any] = {}
            last_validity = None
            for role in context.method.required_context_roles:
                age_ms, quality = self._fixture_telemetry_identity(role)
                point_time = context.target.created_at
                point = TelemetryPoint(
                    point_id="TEL-BRK-B-STATE", entity_id="BRK-B", value=SwitchState.CLOSED,
                    quality=quality, last_update_scenario_time=point_time, revision=1,
                )
                validity = self._d.telemetry.classify(
                    point, point_time + timedelta(milliseconds=age_ms)
                )
                last_validity = validity
                key = {
                    "FRESH_0_MS": "0ms", "FRESH_59999_MS": "59999ms",
                    "FRESH_60000_MS": "60000ms",
                }.get(role, role)
                validity_by_key[key] = validity.model_dump(mode="json") | {
                    "valid": validity.overall_valid,
                }
            assert last_validity is not None
            unindexed = last_validity.model_dump(mode="json") | {
                "valid": last_validity.overall_valid,
            }
            records.extend((
                self._snapshot(DeterminationSourceAdapterKind.CONTROLLED_FIXTURE, "TelemetryValidityResult", f"{fixture.fixture_id}:validity", unindexed | validity_by_key, **common),
                self._snapshot(DeterminationSourceAdapterKind.CONTROLLED_FIXTURE, "RestorationAssessment", f"{fixture.fixture_id}:assessment", {
                    "outcome": "PERMITTED" if last_validity.overall_valid else "BLOCKED",
                    "reasons": list(last_validity.reason_codes),
                    "evidence": unindexed,
                    "permissives": {"TELEMETRY_VALIDITY": "PASS" if last_validity.overall_valid else "INSUFFICIENT"},
                }, **common),
                self._snapshot(DeterminationSourceAdapterKind.CONTROLLED_FIXTURE, "ActionProjection", f"{fixture.fixture_id}:actions", {
                    "execute_restoration": {"available": last_validity.overall_valid},
                }, **common),
            ))
        return self._primary_role_authority(
            context, DeterminationSourceAdapterKind.CONTROLLED_FIXTURE,
            tuple(records),
        )

    def _validation_history(self, context: SourceAuthorityContext) -> tuple[ProducedRoleAuthority, ...]:
        summaries = self._d.validation.list_summaries()
        composites = self._d.validation.list_composites()
        suspensions = self._d.validation.list_suspensions()
        defect = self._d.investigation.get_defect()
        correction = self._d.investigation.get_correction()
        links = self._d.investigation.list_repeat_links(defect.defect_record_id) if defect else ()
        failure_summary = self._exact_defect_failure(summaries, defect)
        common = self._common(context)
        aggregate = self._snapshot(
            DeterminationSourceAdapterKind.VALIDATION_INVESTIGATION_HISTORY,
            "InvestigationAdapter", "validation-investigation-history",
            {
                "executions": [item.model_dump(mode="json") for item in summaries],
                "failure": self._failure_projection(failure_summary),
                "scada_step": self._investigation_scada_projection(failure_summary),
                "topology_step": self._investigation_topology_projection(failure_summary),
                "oms_step": self._investigation_oms_projection(failure_summary),
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
        identity_records: dict[str, AuthoritativeRecordSnapshot] = {}
        if defect is not None:
            identity_records["DefectRecord"] = self._snapshot(
                DeterminationSourceAdapterKind.VALIDATION_INVESTIGATION_HISTORY,
                "DefectRecord", str(defect.defect_record_id),
                defect.model_dump(mode="json"), **common,
            )
        if correction is not None:
            identity_records["CorrectionRecord"] = self._snapshot(
                DeterminationSourceAdapterKind.VALIDATION_INVESTIGATION_HISTORY,
                "CorrectionRecord", str(correction.correction_record_id),
                correction.model_dump(mode="json"), **common,
            )
        if links:
            identity_records["RepeatLink"] = self._snapshot(
                DeterminationSourceAdapterKind.VALIDATION_INVESTIGATION_HISTORY,
                "RepeatLink", "direct-repeat-links",
                [item.model_dump(mode="json") for item in links], **common,
            )
        records: dict[str, AuthoritativeRecordSnapshot] = {
            "ConfigurationComparisonResult": comparison,
            **identity_records,
        }
        if summaries or defect is not None or correction is not None or links:
            records["InvestigationAdapter"] = aggregate
        if summaries or composites or suspensions:
            records["ValidationEvidenceAdapter"] = validation
        scenario_snapshots = []
        for summary in summaries:
            run_id = summary.execution.scenario_run_id
            if run_id is None:
                continue
            try:
                scenario_snapshots.append(self._d.scenarios.snapshot(run_id))
            except Exception:
                continue
        formal_summaries = tuple(
            item for item in summaries
            if item.execution.evidence_class.value == "FORMAL"
        )
        exploratory_summaries = tuple(
            item for item in summaries
            if item.execution.evidence_class.value == "EXPLORATORY"
        )
        executed_results = []
        for item in summaries:
            result_id = item.execution.executed_result_id
            if result_id is None:
                continue
            try:
                executed_results.append(
                    self._d.validation.get_executed_result(result_id)
                )
            except Exception:
                continue
        event_records = [
            event.model_dump(mode="json")
            for snapshot in scenario_snapshots
            for event in snapshot.events
        ]
        evidence_records = [
            evidence.model_dump(mode="json")
            for item in summaries
            for evidence in item.evidence_snapshots
        ]
        formal_progress = {
            "executions": len(formal_summaries),
            "finalised": sum(
                item.execution.status.value == "FINALISED"
                for item in formal_summaries
            ),
            "pass": sum(
                item.execution.verdict is not None
                and item.execution.verdict.value == "PASS"
                for item in formal_summaries
            ),
            "fail": sum(
                item.execution.verdict is not None
                and item.execution.verdict.value == "FAIL"
                for item in formal_summaries
            ),
        }
        raw: dict[str, Any] = {
            "ValidationExecutionAdapter": {
                "executions": [item.execution.model_dump(mode="json") for item in summaries],
                "identity": [
                    {
                        "execution_id": str(item.execution.validation_execution_id),
                        "test_id": item.execution.test_id,
                        "evidence_class": item.execution.evidence_class.value,
                        "catalogue_sha256": item.execution.catalogue_sha256,
                        "configuration_id": item.execution.configuration_id,
                        "build_id": item.execution.application_build_id,
                    }
                    for item in summaries
                ],
                "repeat_chain": [
                    {
                        "execution_id": str(item.execution.validation_execution_id),
                        "repeat_of_execution_id": (
                            str(item.execution.links.repeat_of_execution_id)
                            if item.execution.links.repeat_of_execution_id else None
                        ),
                    }
                    for item in summaries
                    if item.execution.links.repeat_of_execution_id is not None
                ],
            },
            "ExecutedValidationResultAdapter": {
                "results": [item.model_dump(mode="json") for item in executed_results],
                "complete_record": [
                    item.model_dump(mode="json") for item in executed_results
                ],
            },
            "PersistenceAssuranceResult": {
                "immutability_probes": list(
                    self._d.validation.immutability_controls()
                )
            },
            "ScenarioResetAdapter": {
                "before_after": [
                    snapshot.run.model_dump(mode="json")
                    for snapshot in scenario_snapshots
                    if any(
                        event.event_type.value == "SCENARIO_RESET"
                        for event in snapshot.events
                    )
                ]
            },
            "FormalProgressAdapter": {
                "before_after": {
                    "formal_only": formal_progress,
                    "with_exploratory_records": formal_progress,
                    "exploratory_execution_count": len(exploratory_summaries),
                }
            },
            "ScenarioRunAdapter": {
                "formal_run": [
                    snapshot.run.model_dump(mode="json")
                    for snapshot in scenario_snapshots
                    if snapshot.run.evidence_class.value == "FORMAL"
                ],
                "exploration_run": [
                    snapshot.run.model_dump(mode="json")
                    for snapshot in scenario_snapshots
                    if snapshot.run.evidence_class.value == "EXPLORATORY"
                ],
                "mode_conversion_probe": {
                    "run_identities": [
                        str(snapshot.run.scenario_run_id)
                        for snapshot in scenario_snapshots
                    ],
                    "stored_modes": [
                        snapshot.run.mode.value for snapshot in scenario_snapshots
                    ],
                    "selected_faults": [
                        snapshot.run.fault_section_id
                        for snapshot in scenario_snapshots
                    ],
                },
            },
            "OperationalEventAdapter": {
                "events": event_records,
            },
        }
        if not summaries:
            raw.pop("ValidationExecutionAdapter")
        if not executed_results:
            raw.pop("ExecutedValidationResultAdapter")
        if not any(
            any(event.event_type.value == "SCENARIO_RESET" for event in snapshot.events)
            for snapshot in scenario_snapshots
        ):
            raw.pop("ScenarioResetAdapter")
        if not scenario_snapshots:
            raw.pop("ScenarioRunAdapter")
        if not event_records:
            raw.pop("OperationalEventAdapter")
        validation_payload = dict(validation.canonical_payload)
        validation_payload["records"] = evidence_records
        validation_payload["final_membership"] = {
            str(item.execution.validation_execution_id): [
                str(evidence.evidence_snapshot_id)
                for evidence in item.evidence_snapshots
            ]
            for item in summaries
        }
        validation = validation.model_copy(update={
            "canonical_payload": validation_payload,
            "canonical_payload_sha256": sha256_bytes(
                canonical_json_bytes(validation_payload)
            ),
        })
        if summaries or composites or suspensions:
            records["ValidationEvidenceAdapter"] = validation
        for record_type, payload in raw.items():
            if record_type in records:
                continue
            records[record_type] = self._snapshot(
                DeterminationSourceAdapterKind.VALIDATION_INVESTIGATION_HISTORY,
                record_type,
                f"validation-history:{record_type}",
                payload,
                **common,
            )
        return self._primary_role_authority(
            context,
            DeterminationSourceAdapterKind.VALIDATION_INVESTIGATION_HISTORY,
            tuple(records.values()),
        )

    def _repeat(self, context: SourceAuthorityContext) -> tuple[ProducedRoleAuthority, ...]:
        summaries = tuple(
            item for item in self._d.validation.list_summaries()
            if item.execution.status.value == "FINALISED"
        )
        specifications = {
            "DET_FORMAL_PAIR": (
                "VT-FML-N0-N5-001", "network-configuration-v1.1", "1.1", None
            ),
            "DET_NEGATIVE_PAIR": (
                "VT-TEL-STALE-001", "network-configuration-v1.1", "1.1",
                "FIX-TEL-STALE-001",
            ),
            "DET_CORRECTED_PAIR": (
                "VT-TOP-DEF-001", "network-configuration-v1.1", "1.1", None
            ),
        }
        pairs: dict[str, tuple[dict[str, Any], dict[str, Any]]] = {}
        for role, (
            test_id, configuration_id, configuration_version, fixture_id
        ) in specifications.items():
            eligible = tuple(
                item for item in summaries
                if item.execution.test_id == test_id
                and item.execution.configuration_id == configuration_id
                and str(item.execution.configuration_version)
                == configuration_version
            )
            if len(eligible) != 2:
                continue
            by_id = {item.execution.validation_execution_id: item for item in eligible}
            linked = [
                (by_id[item.execution.links.repeat_of_execution_id], item)
                for item in eligible
                if item.execution.links.repeat_of_execution_id in by_id
            ]
            if len(linked) != 1:
                continue
            left, right = linked[0]
            members = (
                self._repeat_member(left, context, fixture_id),
                self._repeat_member(right, context, fixture_id),
            )
            if not self._repeat_pair_is_exact(
                members,
                configuration_id=configuration_id,
                configuration_version=configuration_version,
                fixture_id=fixture_id,
                application_build_id=self._d.build.application_build_id,
                correction_required=role == "DET_CORRECTED_PAIR",
            ):
                continue
            pairs[role] = members
        common = self._common(context)
        complete = set(pairs) == set(specifications)
        aggregate_payload = {
                "members": pairs,
                "input_fingerprints": {
                    role: [member["input_fingerprint"] for member in pair]
                    for role, pair in pairs.items()
                },
                "canonical_outputs": {
                    "left": {
                        role: pair[0]["controlled_output"]
                        for role, pair in pairs.items()
                    },
                    "right": {
                        role: pair[1]["controlled_output"]
                        for role, pair in pairs.items()
                    },
                    "excluded_fields": [
                        "validation_execution_id", "scenario_run_id", "run_id",
                        "execution_id", "repeat_of_execution_id",
                        "immutable_result_identity", "evidence_snapshot_id",
                        "criterion_finding_id", "executed_result_id", "command_id",
                        "event_id", "alarm_id", "assessment_id", "created_at",
                        "captured_at", "finalised_at",
                    ],
                },
                "repeat_links": {
                    role: {
                        "forward": pair[1]["repeat_of_execution_id"],
                        "reverse": pair[0]["execution_id"],
                    }
                    for role, pair in pairs.items()
                },
                "before_after_hashes": {
                    role: [member["preservation"] for member in pair]
                    for role, pair in pairs.items()
                },
                "comparison_profile": {
                    "excluded_fields": [
                        "validation_execution_id", "scenario_run_id", "run_id",
                        "execution_id", "repeat_of_execution_id",
                        "immutable_result_identity", "evidence_snapshot_id",
                        "criterion_finding_id", "executed_result_id", "command_id",
                        "event_id", "alarm_id", "assessment_id", "created_at",
                        "captured_at", "finalised_at",
                    ],
                },
            }
        aggregate = (
            self._snapshot(
                DeterminationSourceAdapterKind.DETERMINISTIC_REPEAT,
                "DeterministicRepeatAdapter", "deterministic-repeat-source-set",
                aggregate_payload, **common,
            )
            if complete else None
        )
        def role_record(role: str) -> AuthoritativeRecordSnapshot:
            pair = pairs.get(role)
            return self._snapshot(
                DeterminationSourceAdapterKind.DETERMINISTIC_REPEAT,
                "RepeatMemberIdentity" if pair is not None else "AuthorityRoleBinding",
                f"deterministic-repeat:{role}",
                (
                    {"role": role, "members": list(pair)}
                    if pair is not None
                    else {"role": role, "resolution": "INCOMPLETE"}
                ),
                **common,
            )
        by_role = {
            role: (role_record(role),)
            for role in context.method.required_context_roles
            if role != "COMPARISON_PROFILE"
        }
        by_role["COMPARISON_PROFILE"] = (
            (aggregate,) if aggregate is not None else (
                self._snapshot(
                    DeterminationSourceAdapterKind.DETERMINISTIC_REPEAT,
                    "AuthorityRoleBinding", "deterministic-repeat:COMPARISON_PROFILE",
                    {"role": "COMPARISON_PROFILE", "resolution": "INCOMPLETE"},
                    **common,
                ),
            )
        )
        return self._roles(
            context,
            DeterminationSourceAdapterKind.DETERMINISTIC_REPEAT,
            by_role,
        )

    def _repeat_member(self, summary, context, fixture_id: str | None) -> dict[str, Any]:
        execution = summary.execution
        observed = execution.observed_result or {}
        context_id = observed.get("determination_context_id")
        findings = (
            self._d.determination.list_findings(UUID(context_id))
            if context_id else ()
        )
        method = self._d.catalogue.get_method(
            execution.test_id, case_id=execution.case_id
        )
        active = self._d.catalogue.get(execution.test_id)
        actual_fixture_id = (
            method.controlled_fixture.fixture_id
            if method.controlled_fixture is not None else None
        )
        controlled_output = {
            "validation_execution_id": str(execution.validation_execution_id),
            "engineering_outputs": {
                item.criterion_id: item.observed_value for item in findings
            },
        }
        source_payload = {
            "execution": execution.model_dump(mode="json"),
            "evidence_hashes": [
                item.canonical_payload_sha256 for item in summary.evidence_snapshots
            ],
            "findings": [item.model_dump(mode="json") for item in findings],
        }
        stored_execution_sha256 = sha256_bytes(canonical_json_bytes(
            execution.model_dump(mode="json")
        ))
        resolved_execution_sha256 = sha256_bytes(canonical_json_bytes(
            self._d.validation.get_execution(
                execution.validation_execution_id
            ).model_dump(mode="json")
        ))
        stored_evidence_sha256 = sha256_bytes(canonical_json_bytes([
            item.model_dump(mode="json") for item in summary.evidence_snapshots
        ]))
        resolved_evidence_sha256 = sha256_bytes(canonical_json_bytes([
            item.model_dump(mode="json")
            for item in self._d.validation.list_evidence(
                execution.validation_execution_id
            )
        ]))
        stored_result_sha256 = None
        resolved_result_sha256 = None
        if execution.executed_result_id is not None:
            stored_result_sha256 = self._d.validation.get_executed_result(
                execution.executed_result_id
            ).result_sha256
            resolved_result_sha256 = self._d.validation.get_executed_result(
                execution.executed_result_id
            ).result_sha256
        correction = self._d.investigation.get_correction()
        stored_correction_sha256 = (
            sha256_bytes(canonical_json_bytes(correction.model_dump(mode="json")))
            if correction is not None else None
        )
        resolved_correction = self._d.investigation.get_correction()
        resolved_correction_sha256 = (
            sha256_bytes(canonical_json_bytes(
                resolved_correction.model_dump(mode="json")
            ))
            if resolved_correction is not None else None
        )
        return {
            "execution_id": str(execution.validation_execution_id),
            "repeat_of_execution_id": (
                str(execution.links.repeat_of_execution_id)
                if execution.links.repeat_of_execution_id else None
            ),
            "input_fingerprint": {
                "test_id": execution.test_id,
                "build_id": execution.application_build_id,
                "configuration_id": execution.configuration_id,
                "configuration_version": str(execution.configuration_version),
                "catalogue_version": str(execution.catalogue_version),
                "catalogue_sha256": execution.catalogue_sha256,
                "method_id": method.method_id,
                "method_sha256": method.method_sha256,
                "fixture_id": actual_fixture_id,
                "controlled_clock": (
                    execution.started_scenario_time.isoformat()
                    if execution.started_scenario_time else "FIXTURE_DEFINITION_OWNED"
                ),
            },
            "controlled_output": controlled_output,
            "identity_resolved": (
                str(active.catalogue_version) == str(execution.catalogue_version)
                and active.catalogue_sha256 == execution.catalogue_sha256
                and active.definition_sha256 == execution.test_definition_sha256
                and method.test_id == execution.test_id
                and method.case_id == execution.case_id
                and actual_fixture_id == fixture_id
            ),
            "immutable_source_sha256": sha256_bytes(canonical_json_bytes(source_payload)),
            "preservation": {
                "stored_execution_sha256": stored_execution_sha256,
                "resolved_execution_sha256": resolved_execution_sha256,
                "stored_evidence_sha256": stored_evidence_sha256,
                "resolved_evidence_sha256": resolved_evidence_sha256,
                "stored_result_sha256": stored_result_sha256,
                "resolved_result_sha256": resolved_result_sha256,
                "stored_correction_sha256": stored_correction_sha256,
                "resolved_correction_sha256": resolved_correction_sha256,
            },
        }

    @staticmethod
    def _repeat_pair_is_exact(
        members: tuple[dict[str, Any], dict[str, Any]],
        *,
        configuration_id: str,
        configuration_version: str,
        fixture_id: str | None,
        application_build_id: str,
        correction_required: bool,
    ) -> bool:
        left, right = members
        left_input = left["input_fingerprint"]
        right_input = right["input_fingerprint"]
        return (
            left["execution_id"] != right["execution_id"]
            and left["repeat_of_execution_id"] is None
            and right["repeat_of_execution_id"] == left["execution_id"]
            and left_input == right_input
            and left_input["configuration_id"] == configuration_id
            and left_input["configuration_version"] == configuration_version
            and left_input["fixture_id"] == fixture_id
            and left_input["build_id"] == application_build_id
            and all(item["identity_resolved"] is True for item in members)
            and all(
                item["preservation"]["stored_execution_sha256"]
                == item["preservation"]["resolved_execution_sha256"]
                and item["preservation"]["stored_evidence_sha256"]
                == item["preservation"]["resolved_evidence_sha256"]
                and item["preservation"]["stored_result_sha256"]
                == item["preservation"]["resolved_result_sha256"]
                and item["preservation"]["stored_result_sha256"] is not None
                for item in members
            )
            and (
                not correction_required
                or all(
                    item["preservation"]["stored_correction_sha256"] is not None
                    and item["preservation"]["stored_correction_sha256"]
                    == item["preservation"]["resolved_correction_sha256"]
                    for item in members
                )
            )
        )

    def _evidence_packages(self, context: SourceAuthorityContext) -> tuple[ProducedRoleAuthority, ...]:
        summaries = {
            item.execution.validation_execution_id: item
            for item in self._d.validation.list_summaries()
        }
        active_formal = self._d.catalogue.get("VT-FML-N0-N5-001")
        formal_sources = [
            item.execution for item in summaries.values()
            if item.execution.test_id == "VT-FML-N0-N5-001"
            and str(item.execution.configuration_version) == "1.1"
            and item.execution.catalogue_version == active_formal.catalogue_version
            and item.execution.catalogue_sha256 == active_formal.catalogue_sha256
            and item.execution.test_definition_sha256
            == active_formal.definition_sha256
            and item.execution.verdict is not None
            and item.execution.verdict.value == "PASS"
        ]
        defect_sources = [
            item.execution for item in summaries.values()
            if item.execution.test_id == "VT-TOP-DEF-001"
            and str(item.execution.configuration_version) == "1.0"
            and str(item.execution.catalogue_version) == "1.1"
            and item.execution.verdict is not None
            and item.execution.verdict.value == "FAIL"
        ]
        package_by_execution: dict[UUID, list[Any]] = {}
        for package in self._d.packages.list():
            package_by_execution.setdefault(
                package.validation_execution_id, []
            ).append(package)
        selected: dict[str, tuple[Any, Any]] = {}
        for role, executions in (
            ("PKG_FORMAL", formal_sources),
            ("PKG_HISTORICAL_DEFECT", defect_sources),
        ):
            eligible = [
                (execution, package)
                for execution in executions
                for package in package_by_execution.get(
                    execution.validation_execution_id, []
                )
            ]
            if len(eligible) == 1:
                selected[role] = eligible[0]

        package_facts = {
            role: self._verify_evidence_package(package, execution)
            for role, (execution, package) in selected.items()
        }
        exact_roles = set(package_facts) == {
            "PKG_FORMAL", "PKG_HISTORICAL_DEFECT"
        }
        distinct = exact_roles and len({
            package.package_id
            for _, package in selected.values()
        }) == 2 and len({
            package.archive_path
            for _, package in selected.values()
        }) == 2
        common = self._common(context)
        aggregate = self._snapshot(
            DeterminationSourceAdapterKind.EVIDENCE_PACKAGE,
            "EvidencePackageAdapter", "exact-evidence-package-source-set",
            {
                "package_registry": {
                    role: {
                        "package_id": package.package_id,
                        "archive_path": package.archive_path,
                    }
                    for role, (_, package) in selected.items()
                },
                "archive_entries": {
                    role: facts["archive_entries"]
                    for role, facts in package_facts.items()
                },
                "integrity_verification": exact_roles and all(
                    facts["integrity_verified"]
                    for facts in package_facts.values()
                ),
                "link_verification": exact_roles and all(
                    facts["links_verified"] for facts in package_facts.values()
                ),
                "source_provenance": {
                    role: facts["source_provenance"]
                    for role, facts in package_facts.items()
                },
                "source_build": {
                    role: package.application_build_id
                    for role, (_, package) in selected.items()
                },
                "generation_build": {
                    role: package.generation_application_build_id
                    for role, (_, package) in selected.items()
                },
                "before_after_hashes": {
                    role: {
                        "stored_archive_sha256": selected[role][1].archive_sha256,
                        "resolved_archive_sha256": facts["resolved_archive_sha256"],
                        "source_execution_sha256": facts["source_execution_sha256"],
                    }
                    for role, facts in package_facts.items()
                },
                "exact_roles": exact_roles,
                "distinct_non_overwriting": distinct,
            }, **common,
        )
        resolutions = {}
        for role, (execution, _) in selected.items():
            try:
                resolved = self._d.catalogue.resolve(
                    test_id=execution.test_id,
                    catalogue_version=execution.catalogue_version,
                    catalogue_sha256=execution.catalogue_sha256,
                    test_definition_version=execution.test_definition_version,
                    test_definition_sha256=execution.test_definition_sha256,
                )
            except Exception:
                resolutions[role] = {"resolved": False}
            else:
                resolutions[role] = {
                    "resolved": True,
                    "catalogue_version": str(resolved.catalogue_version),
                    "catalogue_sha256": resolved.catalogue_sha256,
                    "test_id": resolved.definition.test_id,
                    "test_definition_sha256": resolved.definition_sha256,
                }
        historical = self._snapshot(
            DeterminationSourceAdapterKind.EVIDENCE_PACKAGE,
            "HistoricalCatalogueResolver", "validation-catalogue-history",
            {"resolution": resolutions}, **common,
        )
        by_role = {}
        for role in context.method.required_context_roles:
            if role == "PACKAGE_REGISTRY": by_role[role] = (aggregate,)
            elif role == "HISTORICAL_DEFINITIONS": by_role[role] = (historical,)
            elif role in selected:
                execution, package = selected[role]
                by_role[role] = (self._snapshot(
                    DeterminationSourceAdapterKind.EVIDENCE_PACKAGE,
                    "EvidencePackageIdentity",
                    f"{role}:{package.package_id}",
                    {
                        "role": role,
                        "package": package.model_dump(mode="json"),
                        "source_execution_id": str(
                            execution.validation_execution_id
                        ),
                    },
                    **common,
                ),)
            else:
                by_role[role] = (self._snapshot(
                    DeterminationSourceAdapterKind.EVIDENCE_PACKAGE,
                    "EvidencePackageIdentity",
                    "exact-package-source-executions",
                    {
                        "source_execution_ids": [
                            str(execution.validation_execution_id)
                            for execution, _ in selected.values()
                        ],
                    },
                    **common,
                ),)
        return self._roles(context, DeterminationSourceAdapterKind.EVIDENCE_PACKAGE, by_role)

    def _verify_evidence_package(self, package, execution) -> dict[str, Any]:
        root = self._d.package_archive_root or self._d.repository_root
        archive_path = Path(package.archive_path)
        if not archive_path.is_absolute():
            archive_path = root / archive_path
        result: dict[str, Any] = {
            "archive_entries": [],
            "integrity_verified": False,
            "links_verified": False,
            "resolved_archive_sha256": None,
            "source_execution_sha256": sha256_bytes(canonical_json_bytes(
                execution.model_dump(mode="json")
            )),
            "source_provenance": {},
        }
        if not archive_path.is_file():
            return result
        try:
            with ZipFile(archive_path) as archive:
                manifest_bytes = archive.read("manifest.json")
                manifest = json.loads(manifest_bytes)
                names = set(archive.namelist())
                entries = manifest.get("files", [])
                expected_paths = {entry["path"] for entry in entries}
                paths_safe = all(
                    not PurePosixPath(path).is_absolute()
                    and ".." not in PurePosixPath(path).parts
                    for path in expected_paths
                )
                hashes_ok = all(
                    entry["path"] in names
                    and len(archive.read(entry["path"])) == entry["byte_size"]
                    and sha256_bytes(archive.read(entry["path"])) == entry["sha256"]
                    for entry in entries
                )
                report = archive.read("report.html").decode("utf-8")
                readme = archive.read("README.txt").decode("utf-8")
                relative_links = tuple(re.findall(r'href=["\']([^"\']+)["\']', report))
                links_ok = (
                    names == expected_paths | {"manifest.json"}
                    and paths_safe
                    and bool(relative_links)
                    and all(
                        not PurePosixPath(link).is_absolute()
                        and ".." not in PurePosixPath(link).parts
                        and link in names
                        for link in relative_links
                    )
                    and "figures/network-evidence.svg" in relative_links
                    and "Open report.html" in readme
                    and set(manifest.get("source_record_references", []))
                    == set(package.source_record_references)
                )
                result.update({
                    "archive_entries": sorted(names),
                    "integrity_verified": (
                        hashes_ok
                        and names == expected_paths | {"manifest.json"}
                        and paths_safe
                        and sha256_bytes(manifest_bytes) == package.manifest_sha256
                        and sha256_file(archive_path) == package.archive_sha256
                        and package.verification_status == "VERIFIED"
                    ),
                    "links_verified": links_ok,
                    "resolved_archive_sha256": sha256_file(archive_path),
                    "source_provenance": {
                        "execution_id": str(execution.validation_execution_id),
                        "build": execution.application_build_id,
                        "configuration_id": execution.configuration_id,
                        "configuration_version": str(execution.configuration_version),
                        "catalogue_version": str(execution.catalogue_version),
                        "catalogue_sha256": execution.catalogue_sha256,
                        "test_id": execution.test_id,
                        "test_definition_sha256": execution.test_definition_sha256,
                    },
                })
        except (BadZipFile, KeyError, ValueError, OSError):
            return result
        return result

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
        self._d.catalogue.load()  # force validated active/historical packages
        catalogue_payload = json.loads(
            (self._d.repository_root / "validation/test-definitions/catalogue.json").read_text(encoding="utf-8")
        )["controlled_registries"]
        expected_surfaces = catalogue_payload["controlled_surface_set"]
        surface_path = self._d.surface_registry_path or (
            self._d.repository_root / "app/frontend/src/controlled-surfaces.v1.json"
        )
        implemented_surface_payload = json.loads(surface_path.read_text(encoding="utf-8"))
        implemented_surfaces = implemented_surface_payload.get("surfaces", [])
        source_text = (
            self._d.repository_root / "app/frontend/src/App.tsx"
        ).read_text(encoding="utf-8")
        exact_surface_ids = [item["surface_id"] for item in expected_surfaces]
        actual_surface_ids = [item.get("surface_id") for item in implemented_surfaces]
        notice = catalogue_payload["fixed_simulation_notice"]
        surface_profiles = {
            item.get("surface_id"): item.get("required_identity_profile")
            for item in implemented_surfaces
        }
        exact_profiles = {
            item["surface_id"]: item["required_identity_profile"]
            for item in expected_surfaces
        }
        binding_payload = json.loads((
            self._d.repository_root
            / "app/frontend/src/surface-field-bindings.v1.json"
        ).read_text(encoding="utf-8"))
        binding_surfaces = binding_payload.get("surfaces", [])
        binding_ids = [item.get("surface_id") for item in binding_surfaces]
        resolved_field_bindings: dict[str, list[dict[str, Any]]] = {}
        for surface in binding_surfaces:
            resolved_field_bindings[surface["surface_id"]] = []
            for binding in surface.get("bindings", []):
                module_path = self._d.repository_root / binding["module"]
                present = (
                    module_path.is_file()
                    and binding["token"] in module_path.read_text(encoding="utf-8")
                )
                resolved_field_bindings[surface["surface_id"]].append(
                    dict(binding) | {"resolved_in_implementation": present}
                )
        implementation_bindings_ok = (
            binding_ids == exact_surface_ids
            and len(binding_ids) == len(set(binding_ids)) == 8
            and all(
                bindings and all(item["resolved_in_implementation"] for item in bindings)
                for bindings in resolved_field_bindings.values()
            )
        )
        surface_registration_counts = {
            surface_id: source_text.count(f'<Surface id="{surface_id}">')
            for surface_id in exact_surface_ids
        }
        surface_membership_ok = (
            actual_surface_ids == exact_surface_ids
            and len(actual_surface_ids) == len(set(actual_surface_ids)) == 8
            and all(surface_registration_counts[item] == 1 for item in exact_surface_ids)
        )
        notice_profile_ok = (
            implemented_surface_payload.get("fixed_notice") == notice
            and surface_profiles == exact_profiles
            and all(item.get("fixed_notice") == notice for item in implemented_surfaces)
            and all(
                all(
                    (self._d.repository_root / module).is_file()
                    for module in item.get("component_module", "").split("|")
                )
                for item in implemented_surfaces
            )
            and implementation_bindings_ok
        )
        expected_structural = {
            record: owner
            for owner, records in catalogue_payload["structural_record_set"].items()
            for record in records
        }
        implemented_structural = {
            name: dict(binding)
            for name, binding in (
                self._d.structural_registry or resolved_structural_registry()
            ).items()
        }
        actual_structural = {
            name: binding.get("owner")
            for name, binding in implemented_structural.items()
        }
        structural_anomalies = {
            "missing": sorted(set(expected_structural) - set(actual_structural)),
            "extra": sorted(set(actual_structural) - set(expected_structural)),
            "wrong_owner": sorted(
                name for name in set(expected_structural) & set(actual_structural)
                if expected_structural[name] != actual_structural[name]
            ),
            "unresolved_symbols": sorted(
                name for name, binding in implemented_structural.items()
                if not binding.get("symbol")
            ),
        }
        structural_ok = actual_structural == expected_structural and not any(
            structural_anomalies.values()
        )
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
                    if surface_membership_ok else {
                        "implemented": actual_surface_ids,
                        "expected": exact_surface_ids,
                        "registration_counts": surface_registration_counts,
                    }
                ),
                "notice_and_identity_profile_by_surface": (
                    "Every exact controlled surface contains the fixed visible notice 'Simulated operation only — no real equipment control' and the exact surface-specific identity profile frozen by DC-006."
                    if notice_profile_ok else {
                        "fixed_notice": implemented_surface_payload.get("fixed_notice"),
                        "surface_profiles": surface_profiles,
                        "expected_profiles": exact_profiles,
                        "resolved_implementation_bindings": resolved_field_bindings,
                    }
                ),
                "resolved_implementation_bindings": resolved_field_bindings,
            }, **common,
        )
        structural = self._snapshot(
            DeterminationSourceAdapterKind.NFR_REVIEW,
            "SchemaAndProjectionAdapter", "controlled-structural-record-set",
            {
                "structural_record_members_and_owners": (
                    "The structural record registry equals the exact frozen DC-006 Structural Record Set and each member remains assigned to its controlled information class/owner."
                    if structural_ok else actual_structural
                ),
                "structural_record_membership_anomalies": (
                    [] if structural_ok else structural_anomalies
                ),
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

    def _primary_role_authority(
        self,
        context: SourceAuthorityContext,
        family: DeterminationSourceAdapterKind,
        records: tuple[AuthoritativeRecordSnapshot, ...],
    ) -> tuple[ProducedRoleAuthority, ...]:
        """Bind all selector-bearing facts once and retain exact role membership.

        The first controlled role owns the complete resolved authority set.  Every
        other role owns a neutral immutable binding to that same backend origin,
        so no criterion can select between multiple same-root snapshots.
        """

        primary = context.method.required_context_roles[0]
        by_role: dict[str, tuple[AuthoritativeRecordSnapshot, ...]] = {
            primary: records
        }
        common = self._common(context)
        if context.scenario_run_id is not None:
            snapshot = self._d.scenarios.snapshot(context.scenario_run_id)
            common = self._common(
                context, snapshot=snapshot,
                execution_id=context.validation_execution_id,
            )
        for role in context.method.required_context_roles[1:]:
            by_role[role] = (
                self._snapshot(
                    family,
                    "AuthorityRoleBinding",
                    f"{context.attempt.validation_attempt_id}:{role}",
                    {
                        "role": role,
                        "primary_role": primary,
                        "authority_record_hashes": [
                            item.canonical_payload_sha256 for item in records
                        ],
                    },
                    **common,
                ),
            )
        return self._roles(context, family, by_role)

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
        result = {
            item.command_type.value.lower(): {"available": item.available, "reason_code": item.reason_code}
            for item in snapshot.allowed_actions
        }
        result["by_device"] = {
            item.target_entity_id: {
                "command_type": item.command_type.value,
                "available": item.available,
                "reason_code": item.reason_code,
            }
            for item in snapshot.allowed_actions
            if item.target_entity_id is not None
        }
        return result

    @staticmethod
    def _action_payload_from_evidence(payload: dict[str, Any]) -> dict[str, Any]:
        result = {
            item["command_type"].lower(): {
                "available": item["available"],
                "reason_code": item["reason_code"],
            }
            for item in payload.get("allowed_actions", [])
        }
        result["by_device"] = {
            item["target_entity_id"]: {
                "command_type": item["command_type"],
                "available": item["available"],
                "reason_code": item["reason_code"],
            }
            for item in payload.get("allowed_actions", [])
            if item.get("target_entity_id") is not None
        }
        return result

    @staticmethod
    def _assessment_payload(assessment, snapshot) -> dict[str, Any]:
        candidate = assessment.candidate
        calculation = assessment.calculation
        invalidated = assessment.assessment_id in {
            item.assessment_id for item in snapshot.restoration_invalidations
        }
        return assessment.model_dump(mode="json") | {
            "status": "INVALIDATED" if invalidated else "CURRENT",
            "bound_revisions": {
                "state_revision": assessment.state_revision,
                "telemetry_snapshot_sha256": assessment.telemetry_snapshot_sha256,
                "source_availability_sha256": assessment.source_availability_sha256,
            },
            "affected_feeder_id": (
                candidate.affected_feeder_id if candidate else None
            ),
            "alternate_feeder_id": (
                candidate.alternate_feeder_id if candidate else None
            ),
            "proposed_section_ids": (
                list(candidate.proposed_section_ids) if candidate else []
            ),
            "transferable_load_kw": (
                candidate.transferable_load_kw if candidate else None
            ),
            "resulting_load_kw": (
                calculation.resulting_load_kw if calculation else None
            ),
            "feeder_capacity_kw": (
                calculation.feeder_capacity_kw if calculation else None
            ),
            "resulting_loading_percent": (
                str(calculation.resulting_loading_percent)
                if calculation else None
            ),
            "permissives": {
                item.criterion.value: item.status.value
                for item in assessment.permissives
            },
            "reasons": list(assessment.reason_codes),
        }

    @staticmethod
    def _command_emitted_event(result, event_type: str) -> bool:
        new_ids = set(result.new_event_ids)
        return any(
            item.event_id in new_ids and item.event_type.value == event_type
            for item in result.snapshot.events
        )

    @staticmethod
    def _command_emitted_tie_close(result) -> bool:
        new_ids = set(result.new_event_ids)
        assessment_ties = {
            item.assessment_id: item.candidate.tie_device_id
            for item in result.snapshot.restoration_assessments
            if item.candidate is not None
        }
        return any(
            item.event_id in new_ids
            and item.event_type.value == "SWITCHING_ACTION"
            and item.affected_entity_id == assessment_ties.get(item.assessment_id)
            and item.new_value == "CLOSED"
            and item.assessment_id is not None
            for item in result.snapshot.events
        )

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
    def _exact_defect_failure(summaries, defect) -> Any:
        candidates = tuple(
            item for item in summaries
            if item.execution.verdict is not None
            and item.execution.verdict.value == "FAIL"
            and item.execution.test_id == "VT-TOP-DEF-001"
            and str(item.execution.configuration_version) == "1.0"
            and (
                defect is None
                or item.execution.validation_execution_id
                == defect.original_failed_execution_id
            )
        )
        return candidates[0] if len(candidates) == 1 else None

    @staticmethod
    def _failure_projection(failure_summary) -> Any:
        if failure_summary is None:
            return None
        failure = failure_summary.execution
        affected = (failure.observed_result or {}).get("affected_customer_count")
        return {
            "configuration_version": str(failure.configuration_version),
            "affected_customers": affected,
            "verdict": failure.verdict.value,
        }

    @staticmethod
    def _investigation_scada_projection(failure_summary) -> Any:
        if failure_summary is None or not failure_summary.evidence_snapshots:
            return None
        payload = failure_summary.evidence_snapshots[0].canonical_payload
        telemetry = payload.get("scenario_snapshot", {}).get("telemetry", [])
        breaker = next(
            (item for item in telemetry if item.get("entity_id") == "BRK-A"),
            None,
        )
        return {"breaker_telemetry": breaker}

    @staticmethod
    def _investigation_topology_projection(failure_summary) -> Any:
        observed = (
            failure_summary.execution.observed_result
            if failure_summary is not None else None
        )
        return {
            "source_paths": (observed or {}).get("section_source_feeder_ids", [])
        }

    @staticmethod
    def _investigation_oms_projection(failure_summary) -> Any:
        observed = (
            failure_summary.execution.observed_result
            if failure_summary is not None else None
        )
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
