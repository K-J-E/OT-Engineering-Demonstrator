"""Configuration-driven I4 candidate discovery and restoration assessment."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from uuid import NAMESPACE_URL, UUID, uuid5

from ...domain.configuration import Feeder
from ...domain.enums import (
    PermissiveStatus,
    RadialityStatus,
    RestorationCriterion,
    RestorationOutcome,
    SourceAvailability,
    SwitchState,
    SwitchingDeviceType,
)
from ...infrastructure.hashing import canonical_json_bytes, sha256_bytes
from ...modules.configuration.models import LoadedConfiguration
from ...modules.outage.models import OutageResult
from ...modules.telemetry.models import TelemetryPoint, TelemetryValidity
from ...modules.topology import TopologyInputs, TopologyResult, TopologyService
from .models import (
    PermissiveResult,
    RestorationAssessment,
    RestorationCalculation,
    RestorationCandidate,
    RestorationTelemetryEvidence,
)


@dataclass(frozen=True)
class RestorationAssessmentInputs:
    assessment_id: UUID
    assessment_sequence: int
    scenario_run_id: UUID
    state_revision: int
    scenario_time: datetime
    fault_section_id: str
    telemetry: tuple[TelemetryPoint, ...]
    telemetry_validity: tuple[TelemetryValidity, ...]
    source_availability: dict[str, SourceAvailability]
    current_topology: TopologyResult
    current_outage: OutageResult


class RestorationService:
    """Keep candidate discovery, evidence and engineering permissives separate."""

    def __init__(self) -> None:
        self._topology = TopologyService()

    def assess(
        self,
        loaded: LoadedConfiguration,
        inputs: RestorationAssessmentInputs,
    ) -> RestorationAssessment:
        candidate = self.discover_candidate(loaded, inputs)
        required_points = self._required_evidence_points(loaded, inputs.telemetry)
        validity_by_id = {item.point_id: item for item in inputs.telemetry_validity}
        evidence = tuple(
            self._evidence(point, validity_by_id[point.point_id])
            for point in required_points
        )
        telemetry_sha = self.telemetry_snapshot_sha(required_points)
        source_sha = self.source_availability_sha(inputs.source_availability)

        if candidate is None:
            return RestorationAssessment(
                assessment_id=inputs.assessment_id,
                assessment_sequence=inputs.assessment_sequence,
                scenario_run_id=inputs.scenario_run_id,
                configuration_id=loaded.catalog_entry.configuration_id,
                state_revision=inputs.state_revision,
                scenario_time=inputs.scenario_time,
                candidate=None,
                telemetry_snapshot_sha256=telemetry_sha,
                source_availability_sha256=source_sha,
                telemetry_evidence=evidence,
                source_availability=inputs.source_availability,
                permissives=(),
                calculation=None,
                outcome=RestorationOutcome.NO_CANDIDATE,
                reason_codes=("NO_RESTORATION_CANDIDATE",),
            )

        invalid_ids = tuple(item.point_id for item in evidence if not item.overall_valid)
        telemetry_result = PermissiveResult(
            criterion=RestorationCriterion.TELEMETRY_VALIDITY,
            status=(
                PermissiveStatus.INSUFFICIENT
                if invalid_ids
                else PermissiveStatus.PASS
            ),
            reason_codes=(
                ("REQUIRED_TELEMETRY_UNTRUSTWORTHY",)
                if invalid_ids
                else ("REQUIRED_TELEMETRY_TRUSTWORTHY",)
            ),
            evidence_point_ids=tuple(item.point_id for item in evidence),
        )

        current_proof = inputs.current_topology.isolation_proof
        isolation_pass = bool(current_proof and current_proof.isolated)
        isolation = PermissiveResult(
            criterion=RestorationCriterion.FAULT_ISOLATION,
            status=(PermissiveStatus.PASS if isolation_pass else PermissiveStatus.FAIL),
            reason_codes=(
                ("FAULT_ISOLATION_PROVEN",)
                if isolation_pass
                else ("FAULT_ISOLATION_NOT_PROVEN",)
            ),
            evidence_point_ids=(
                current_proof.incident_boundary_device_ids if current_proof else ()
            ),
        )

        proposed = self._proposed_topology(loaded, inputs, candidate)
        point_by_entity = {point.entity_id: point for point in inputs.telemetry}
        source_available = (
            inputs.source_availability[candidate.alternate_source_id]
            is SourceAvailability.AVAILABLE
        )
        breaker_closed = (
            point_by_entity[candidate.alternate_source_breaker_id].value
            is SwitchState.CLOSED
        )
        supplied = all(
            candidate.alternate_feeder_id
            in next(
                item for item in proposed.sections if item.section_id == section_id
            ).source_feeder_ids
            for section_id in candidate.proposed_section_ids
        )
        alternate_pass = source_available and breaker_closed and supplied
        alternate = PermissiveResult(
            criterion=RestorationCriterion.ALTERNATE_SOURCE,
            status=(PermissiveStatus.PASS if alternate_pass else PermissiveStatus.FAIL),
            reason_codes=tuple(
                code
                for condition, code in (
                    (source_available, "ALTERNATE_SOURCE_AVAILABLE"),
                    (breaker_closed, "ALTERNATE_BREAKER_CLOSED"),
                    (supplied, "ALTERNATE_SOURCE_PATH_PROVEN"),
                )
                if not condition
            )
            or ("ALTERNATE_SOURCE_AND_PATH_PROVEN",),
            evidence_point_ids=(candidate.alternate_source_breaker_id,),
        )

        radial_pass = proposed.radiality_status is RadialityStatus.RADIAL
        radial = PermissiveResult(
            criterion=RestorationCriterion.RADIAL_TOPOLOGY,
            status=(PermissiveStatus.PASS if radial_pass else PermissiveStatus.FAIL),
            reason_codes=(
                ("PROPOSED_TOPOLOGY_RADIAL",)
                if radial_pass
                else ("PROPOSED_TOPOLOGY_UNINTENDED_LOOP",)
            ),
            evidence_point_ids=tuple(item.point_id for item in evidence),
        )

        load = next(
            item
            for item in inputs.current_topology.feeder_loads
            if item.feeder_id == candidate.alternate_feeder_id
        )
        feeder = self._feeder(loaded, candidate.alternate_feeder_id)
        calculation = self.calculate_capacity(
            alternate_feeder_id=feeder.entity_id,
            existing_load_kw=load.currently_supplied_load_kw or 0,
            transferable_load_kw=candidate.transferable_load_kw,
            capacity_kw=feeder.capacity_kw,
        )
        capacity = PermissiveResult(
            criterion=RestorationCriterion.CAPACITY,
            status=(
                PermissiveStatus.PASS
                if calculation.capacity_pass
                else PermissiveStatus.FAIL
            ),
            reason_codes=(
                ("RESULTING_LOAD_WITHIN_CAPACITY",)
                if calculation.capacity_pass
                else ("RESULTING_LOAD_EXCEEDS_CAPACITY",)
            ),
        )
        permissives = (isolation, alternate, radial, telemetry_result, capacity)
        if invalid_ids:
            outcome = RestorationOutcome.BLOCKED
            reasons = ("INSUFFICIENT_OR_UNRELIABLE_INFORMATION",)
        elif any(item.status is PermissiveStatus.FAIL for item in permissives):
            outcome = RestorationOutcome.REJECTED
            reasons = tuple(
                reason
                for item in permissives
                if item.status is PermissiveStatus.FAIL
                for reason in item.reason_codes
            )
        else:
            outcome = RestorationOutcome.PERMITTED
            reasons = ("ALL_RESTORATION_PERMISSIVES_PASS",)

        return RestorationAssessment(
            assessment_id=inputs.assessment_id,
            assessment_sequence=inputs.assessment_sequence,
            scenario_run_id=inputs.scenario_run_id,
            configuration_id=loaded.catalog_entry.configuration_id,
            state_revision=inputs.state_revision,
            scenario_time=inputs.scenario_time,
            candidate=candidate,
            telemetry_snapshot_sha256=telemetry_sha,
            source_availability_sha256=source_sha,
            telemetry_evidence=evidence,
            source_availability=inputs.source_availability,
            permissives=permissives,
            calculation=calculation,
            outcome=outcome,
            reason_codes=reasons,
        )

    def discover_candidate(
        self,
        loaded: LoadedConfiguration,
        inputs: RestorationAssessmentInputs,
    ) -> RestorationCandidate | None:
        config = loaded.data
        section_by_id = {item.entity_id: item for item in config.sections}
        fault = section_by_id[inputs.fault_section_id]
        feeder_by_id = {item.entity_id: item for item in config.feeders}
        current_section = {item.section_id: item for item in inputs.current_topology.sections}
        point_states = {point.entity_id: point.value for point in inputs.telemetry}

        ties = sorted(
            (
                device
                for device in config.switching_devices
                if device.device_type is SwitchingDeviceType.TIE_SWITCH
            ),
            key=lambda item: item.entity_id,
        )
        edge_by_device: dict[str, list[object]] = {}
        for tie in ties:
            edge_by_device[tie.entity_id] = [
                edge
                for edge in config.connectivity_edges
                if tie.entity_id in {edge.endpoint_a_id, edge.endpoint_b_id}
            ]
        for tie in ties:
            adjacent_sections = tuple(
                next(
                    endpoint
                    for endpoint in (edge.endpoint_a_id, edge.endpoint_b_id)
                    if endpoint != tie.entity_id
                )
                for edge in edge_by_device[tie.entity_id]
            )
            affected_sides = tuple(
                section_id
                for section_id in adjacent_sections
                if section_by_id[section_id].feeder_id == fault.feeder_id
            )
            if len(affected_sides) != 1:
                continue
            alternate_side = next(
                section_id for section_id in adjacent_sections if section_id not in affected_sides
            )
            alternate_feeder = feeder_by_id[section_by_id[alternate_side].feeder_id]
            structural_states = dict(point_states)
            structural_states[tie.entity_id] = SwitchState.CLOSED
            structural_states[alternate_feeder.source_breaker_id] = SwitchState.CLOSED
            structural_sources = dict(inputs.source_availability)
            structural_sources[alternate_feeder.source_id] = SourceAvailability.AVAILABLE
            proposed = self._topology.calculate(
                loaded,
                TopologyInputs(
                    device_states=structural_states,
                    source_availability=structural_sources,
                    faulted_section_ids=frozenset({inputs.fault_section_id}),
                    active_fault_section_id=inputs.fault_section_id,
                ),
            )
            proposed_by_id = {item.section_id: item for item in proposed.sections}
            section_ids = tuple(
                sorted(
                    section.entity_id
                    for section in config.sections
                    if section.feeder_id == fault.feeder_id
                    and section.entity_id != inputs.fault_section_id
                    and not current_section[section.entity_id].energised
                    and alternate_feeder.entity_id
                    in proposed_by_id[section.entity_id].source_feeder_ids
                )
            )
            if not section_ids:
                continue
            paths = tuple(
                path
                for section_id in section_ids
                for path in proposed_by_id[section_id].source_paths
                if path.source_feeder_id == alternate_feeder.entity_id
            )
            path_edges = tuple(sorted({edge for path in paths for edge in path.edge_ids}))
            transferable = sum(section_by_id[item].load_kw for item in section_ids)
            affected_sections = set(inputs.current_outage.de_energised_section_ids)
            restored_customers = sum(
                mapping.customer_count
                for mapping in config.customer_zone_mappings
                if mapping.section_id in section_ids and mapping.section_id in affected_sections
            )
            identity = "|".join(
                (
                    loaded.catalog_entry.configuration_id,
                    inputs.fault_section_id,
                    tie.entity_id,
                    alternate_feeder.entity_id,
                    *section_ids,
                )
            )
            return RestorationCandidate(
                candidate_id=uuid5(NAMESPACE_URL, identity),
                affected_feeder_id=fault.feeder_id,
                alternate_feeder_id=alternate_feeder.entity_id,
                alternate_source_id=alternate_feeder.source_id,
                alternate_source_breaker_id=alternate_feeder.source_breaker_id,
                tie_device_id=tie.entity_id,
                proposed_section_ids=section_ids,
                proposed_path_edge_ids=path_edges,
                transferable_load_kw=transferable,
                proposed_restored_customer_count=restored_customers,
            )
        return None

    def _proposed_topology(
        self,
        loaded: LoadedConfiguration,
        inputs: RestorationAssessmentInputs,
        candidate: RestorationCandidate,
    ) -> TopologyResult:
        states = {point.entity_id: point.value for point in inputs.telemetry}
        states[candidate.tie_device_id] = candidate.requested_tie_state
        return self._topology.calculate(
            loaded,
            TopologyInputs(
                device_states=states,
                source_availability=inputs.source_availability,
                faulted_section_ids=frozenset({inputs.fault_section_id}),
                active_fault_section_id=inputs.fault_section_id,
            ),
        )

    @staticmethod
    def calculate_capacity(
        *,
        alternate_feeder_id: str,
        existing_load_kw: int,
        transferable_load_kw: int,
        capacity_kw: int,
    ) -> RestorationCalculation:
        resulting = existing_load_kw + transferable_load_kw
        percent = (Decimal(resulting) * Decimal(100) / Decimal(capacity_kw)).quantize(
            Decimal("0.1"), rounding=ROUND_HALF_UP
        )
        return RestorationCalculation(
            alternate_feeder_id=alternate_feeder_id,
            existing_supplied_load_kw=existing_load_kw,
            transferable_load_kw=transferable_load_kw,
            resulting_load_kw=resulting,
            feeder_capacity_kw=capacity_kw,
            resulting_loading_percent=percent,
            capacity_pass=resulting <= capacity_kw,
        )

    @staticmethod
    def telemetry_snapshot_sha(points: tuple[TelemetryPoint, ...]) -> str:
        payload = [
            point.model_dump(mode="json")
            for point in sorted(points, key=lambda item: item.point_id)
        ]
        return sha256_bytes(canonical_json_bytes(payload))

    @staticmethod
    def source_availability_sha(values: dict[str, SourceAvailability]) -> str:
        return sha256_bytes(
            canonical_json_bytes(
                {key: value.value for key, value in sorted(values.items())}
            )
        )

    @staticmethod
    def _required_evidence_points(
        loaded: LoadedConfiguration,
        telemetry: tuple[TelemetryPoint, ...],
    ) -> tuple[TelemetryPoint, ...]:
        monitored = {
            device.entity_id
            for device in loaded.data.switching_devices
            if device.monitored
        }
        return tuple(
            sorted(
                (point for point in telemetry if point.entity_id in monitored),
                key=lambda item: item.point_id,
            )
        )

    @staticmethod
    def _evidence(
        point: TelemetryPoint,
        validity: TelemetryValidity,
    ) -> RestorationTelemetryEvidence:
        return RestorationTelemetryEvidence(
            point_id=point.point_id,
            entity_id=point.entity_id,
            value=point.value,
            quality=point.quality,
            timestamp=point.last_update_scenario_time,
            revision=point.revision,
            age_ms=validity.age_ms,
            freshness=validity.freshness,
            overall_valid=validity.overall_valid,
            reason_codes=validity.reason_codes,
        )

    @staticmethod
    def _feeder(loaded: LoadedConfiguration, feeder_id: str) -> Feeder:
        return next(item for item in loaded.data.feeders if item.entity_id == feeder_id)
