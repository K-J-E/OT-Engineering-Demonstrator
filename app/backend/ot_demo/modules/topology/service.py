"""Generic graph, energisation, radiality and DC-003 isolation processing."""

from collections import defaultdict
from collections.abc import Iterable
from itertools import pairwise

import networkx as nx

from ...domain.configuration import ConnectivityEdge, NetworkConfigurationData
from ...domain.enums import (
    BoundaryEvidenceCondition,
    BoundaryOperationNeed,
    BoundaryProofStatus,
    FreshnessStatus,
    RadialityStatus,
    SourceAvailability,
    SwitchState,
    SwitchingDeviceType,
    TelemetryQuality,
)
from ...modules.configuration.models import LoadedConfiguration
from .models import (
    BoundaryEvaluation,
    BoundaryObservation,
    DerivedFeederLoad,
    IsolationProof,
    SectionDerivedState,
    SourcePath,
    TopologyInputs,
    TopologyResult,
)


class TopologyInputError(ValueError):
    """Raised when a pure-domain input is incomplete or inconsistent."""


class TopologyService:
    """Derive network state solely from configuration and current pure-domain inputs."""

    def calculate(
        self,
        loaded: LoadedConfiguration,
        inputs: TopologyInputs,
    ) -> TopologyResult:
        configuration = loaded.data
        self._validate_inputs(configuration, inputs)

        devices_by_id = {
            device.entity_id: device for device in configuration.switching_devices
        }
        source_side_edge_ids = self._source_side_edge_ids(configuration)

        active_edge_ids = tuple(
            sorted(
                edge.edge_id
                for edge in configuration.connectivity_edges
                if inputs.device_states[self._device_endpoint(edge, devices_by_id)]
                is SwitchState.CLOSED
            )
        )
        active_edge_set = set(active_edge_ids)

        # A zone substation is a common availability source, while each feeder
        # breaker is a separate feeder injection. Excluding source-side edges from
        # distribution traversal prevents the shared source entity from becoming
        # an artificial feeder-to-feeder bus connection.
        distribution_graph = self._build_graph(
            edge
            for edge in configuration.connectivity_edges
            if edge.edge_id in active_edge_set and edge.edge_id not in source_side_edge_ids
        )

        available_source_ids = tuple(
            sorted(
                source.entity_id
                for source in configuration.sources
                if inputs.source_availability[source.entity_id]
                is SourceAvailability.AVAILABLE
            )
        )
        available_source_id_set = set(available_source_ids)
        available_feeders = tuple(
            sorted(
                feeder.entity_id
                for feeder in configuration.feeders
                if feeder.source_id in available_source_id_set
            )
        )
        active_source_feeders = tuple(
            sorted(
                feeder.entity_id
                for feeder in configuration.feeders
                if feeder.entity_id in available_feeders
                and inputs.device_states[feeder.source_breaker_id] is SwitchState.CLOSED
            )
        )

        paths_by_section = self._derive_source_paths(
            configuration=configuration,
            graph=distribution_graph,
            source_side_edge_ids=source_side_edge_ids,
            available_feeder_ids=set(active_source_feeders),
        )
        faulted_section_ids = set(inputs.faulted_section_ids)
        section_states = tuple(
            SectionDerivedState(
                section_id=section.entity_id,
                energised=bool(paths_by_section[section.entity_id]),
                faulted=section.entity_id in faulted_section_ids,
                source_feeder_ids=tuple(
                    sorted(
                        {
                            path.source_feeder_id
                            for path in paths_by_section[section.entity_id]
                        }
                    )
                ),
                source_paths=tuple(paths_by_section[section.entity_id]),
            )
            for section in sorted(configuration.sections, key=lambda item: item.entity_id)
        )

        radiality_status, loop_components = self._derive_radiality(
            configuration,
            distribution_graph,
            set(active_source_feeders),
        )
        feeder_loads = self._derive_feeder_loads(configuration, section_states)
        isolation_proof = (
            self._derive_isolation_proof(
                configuration,
                inputs.active_fault_section_id,
                inputs.boundary_observations,
                paths_by_section[inputs.active_fault_section_id],
                available_feeders,
            )
            if inputs.active_fault_section_id is not None
            else None
        )

        return TopologyResult(
            configuration_id=loaded.catalog_entry.configuration_id,
            configured_edge_ids=tuple(
                sorted(edge.edge_id for edge in configuration.connectivity_edges)
            ),
            active_edge_ids=active_edge_ids,
            available_source_ids=available_source_ids,
            available_source_feeder_ids=available_feeders,
            active_source_feeder_ids=active_source_feeders,
            radiality_status=radiality_status,
            unintended_loop_component_section_ids=loop_components,
            sections=section_states,
            feeder_loads=feeder_loads,
            isolation_proof=isolation_proof,
        )

    @staticmethod
    def normal_inputs(configuration: NetworkConfigurationData) -> TopologyInputs:
        """Build explicit normal inputs from configured normal values for fixtures/startup."""

        return TopologyInputs(
            device_states={
                device.entity_id: device.normal_state
                for device in configuration.switching_devices
            },
            source_availability={
                source.entity_id: source.normal_source_availability
                for source in configuration.sources
            },
        )

    @staticmethod
    def _validate_inputs(
        configuration: NetworkConfigurationData,
        inputs: TopologyInputs,
    ) -> None:
        device_ids = {device.entity_id for device in configuration.switching_devices}
        source_ids = {source.entity_id for source in configuration.sources}
        section_ids = {section.entity_id for section in configuration.sections}
        if set(inputs.device_states) != device_ids:
            raise TopologyInputError(
                "device_states must contain every configured device exactly once"
            )
        if set(inputs.source_availability) != source_ids:
            raise TopologyInputError(
                "source_availability must contain every configured source exactly once"
            )
        unknown_faults = sorted(set(inputs.faulted_section_ids) - section_ids)
        if unknown_faults:
            raise TopologyInputError(f"unknown faulted sections: {unknown_faults}")
        unknown_observations = sorted(set(inputs.boundary_observations) - device_ids)
        if unknown_observations:
            raise TopologyInputError(
                f"boundary observations reference unknown devices: {unknown_observations}"
            )

    @staticmethod
    def _device_endpoint(edge: ConnectivityEdge, devices_by_id: dict[str, object]) -> str:
        if edge.endpoint_a_id in devices_by_id:
            return edge.endpoint_a_id
        return edge.endpoint_b_id

    @staticmethod
    def _source_side_edge_ids(configuration: NetworkConfigurationData) -> set[str]:
        source_ids = {source.entity_id for source in configuration.sources}
        breaker_ids = {feeder.source_breaker_id for feeder in configuration.feeders}
        return {
            edge.edge_id
            for edge in configuration.connectivity_edges
            if {edge.endpoint_a_id, edge.endpoint_b_id} & source_ids
            and {edge.endpoint_a_id, edge.endpoint_b_id} & breaker_ids
        }

    @staticmethod
    def _build_graph(edges: Iterable[ConnectivityEdge]) -> nx.Graph:
        graph = nx.Graph()
        for edge in sorted(edges, key=lambda item: item.edge_id):
            graph.add_edge(
                edge.endpoint_a_id,
                edge.endpoint_b_id,
                edge_id=edge.edge_id,
            )
        return graph

    def _derive_source_paths(
        self,
        *,
        configuration: NetworkConfigurationData,
        graph: nx.Graph,
        source_side_edge_ids: set[str],
        available_feeder_ids: set[str],
    ) -> dict[str, list[SourcePath]]:
        paths: dict[str, list[SourcePath]] = defaultdict(list)
        sections = sorted(configuration.sections, key=lambda item: item.entity_id)
        for feeder in sorted(configuration.feeders, key=lambda item: item.entity_id):
            if feeder.entity_id not in available_feeder_ids:
                continue
            source_edge = next(
                edge
                for edge in configuration.connectivity_edges
                if edge.edge_id in source_side_edge_ids
                and feeder.source_breaker_id in {edge.endpoint_a_id, edge.endpoint_b_id}
                and feeder.source_id in {edge.endpoint_a_id, edge.endpoint_b_id}
            )
            if feeder.source_breaker_id not in graph:
                continue
            for section in sections:
                if section.entity_id not in graph:
                    continue
                simple_paths = nx.all_simple_paths(
                    graph,
                    feeder.source_breaker_id,
                    section.entity_id,
                )
                for node_path in simple_paths:
                    edge_path = tuple(
                        graph.edges[node_a, node_b]["edge_id"]
                        for node_a, node_b in pairwise(node_path)
                    )
                    paths[section.entity_id].append(
                        SourcePath(
                            source_id=feeder.source_id,
                            source_feeder_id=feeder.entity_id,
                            source_breaker_id=feeder.source_breaker_id,
                            target_section_id=section.entity_id,
                            node_ids=(feeder.source_id, *node_path),
                            edge_ids=(source_edge.edge_id, *edge_path),
                        )
                    )
        for section_paths in paths.values():
            section_paths.sort(
                key=lambda path: (
                    path.source_feeder_id,
                    len(path.edge_ids),
                    path.edge_ids,
                )
            )
        return paths

    @staticmethod
    def _derive_radiality(
        configuration: NetworkConfigurationData,
        graph: nx.Graph,
        available_feeder_ids: set[str],
    ) -> tuple[RadialityStatus, tuple[tuple[str, ...], ...]]:
        section_ids = {section.entity_id for section in configuration.sections}
        injection_by_breaker = {
            feeder.source_breaker_id: feeder.entity_id
            for feeder in configuration.feeders
            if feeder.entity_id in available_feeder_ids
        }
        invalid_components: list[tuple[str, ...]] = []
        for component in nx.connected_components(graph):
            subgraph = graph.subgraph(component)
            injections = set(component) & set(injection_by_breaker)
            if not nx.is_tree(subgraph) or len(injections) > 1:
                invalid_components.append(tuple(sorted(set(component) & section_ids)))
        if invalid_components:
            return RadialityStatus.UNINTENDED_LOOP, tuple(sorted(invalid_components))
        return RadialityStatus.RADIAL, ()

    @staticmethod
    def _derive_feeder_loads(
        configuration: NetworkConfigurationData,
        section_states: tuple[SectionDerivedState, ...],
    ) -> tuple[DerivedFeederLoad, ...]:
        section_by_id = {section.entity_id: section for section in configuration.sections}
        result: list[DerivedFeederLoad] = []
        for feeder in sorted(configuration.feeders, key=lambda item: item.entity_id):
            supplied_sections = tuple(
                state.section_id
                for state in section_states
                if state.source_feeder_ids == (feeder.entity_id,)
            )
            multiply_supplied_sections = tuple(
                state.section_id
                for state in section_states
                if feeder.entity_id in state.source_feeder_ids
                and len(state.source_feeder_ids) > 1
            )
            result.append(
                DerivedFeederLoad(
                    feeder_id=feeder.entity_id,
                    configured_normal_load_kw=feeder.normal_connected_load_kw,
                    currently_supplied_load_kw=(
                        None
                        if multiply_supplied_sections
                        else sum(
                            section_by_id[section_id].load_kw
                            for section_id in supplied_sections
                        )
                    ),
                    supplied_section_ids=supplied_sections,
                    multiply_supplied_section_ids=multiply_supplied_sections,
                    load_attribution_complete=not multiply_supplied_sections,
                )
            )
        return tuple(result)

    def _derive_isolation_proof(
        self,
        configuration: NetworkConfigurationData,
        fault_section_id: str,
        observations: dict[str, BoundaryObservation],
        active_source_paths: list[SourcePath],
        available_feeder_ids: tuple[str, ...],
    ) -> IsolationProof:
        device_ids = {device.entity_id for device in configuration.switching_devices}
        incident_boundaries = tuple(
            sorted(
                next(
                    endpoint
                    for endpoint in (edge.endpoint_a_id, edge.endpoint_b_id)
                    if endpoint in device_ids
                )
                for edge in configuration.connectivity_edges
                if fault_section_id in {edge.endpoint_a_id, edge.endpoint_b_id}
            )
        )
        evaluations = tuple(
            self._evaluate_boundary(device_id, observations.get(device_id))
            for device_id in incident_boundaries
        )
        all_open = bool(evaluations) and all(
            item.proof_status is BoundaryProofStatus.PROVEN_OPEN
            for item in evaluations
        )
        zero_paths = not active_source_paths
        reasons: list[str] = []
        if not all_open:
            reasons.append("INCIDENT_BOUNDARIES_NOT_ALL_PROVEN_OPEN")
        if not zero_paths:
            reasons.append("ACTIVE_SOURCE_PATH_REMAINS")
        if all_open and zero_paths:
            reasons.append("FAULT_ISOLATED")
        return IsolationProof(
            fault_section_id=fault_section_id,
            incident_boundary_device_ids=incident_boundaries,
            boundary_evaluations=evaluations,
            evaluated_source_feeder_ids=available_feeder_ids,
            active_source_paths=tuple(active_source_paths),
            all_boundaries_proven_open=all_open,
            zero_active_source_paths=zero_paths,
            isolated=all_open and zero_paths,
            reason_codes=tuple(reasons),
        )

    @staticmethod
    def _evaluate_boundary(
        device_id: str,
        observation: BoundaryObservation | None,
    ) -> BoundaryEvaluation:
        if (
            observation is not None
            and observation.quality is TelemetryQuality.GOOD
            and observation.freshness_status is FreshnessStatus.FRESH
        ):
            if observation.observed_state is SwitchState.OPEN:
                return BoundaryEvaluation(
                    boundary_device_id=device_id,
                    observed_state=observation.observed_state,
                    quality=observation.quality,
                    freshness_status=observation.freshness_status,
                    evidence_condition=BoundaryEvidenceCondition.TRUSTWORTHY_OPEN,
                    proof_status=BoundaryProofStatus.PROVEN_OPEN,
                    operation_need=BoundaryOperationNeed.NONE_SATISFIED,
                    reason_codes=("TRUSTWORTHY_OPEN_SATISFIED",),
                )
            if observation.observed_state is SwitchState.CLOSED:
                return BoundaryEvaluation(
                    boundary_device_id=device_id,
                    observed_state=observation.observed_state,
                    quality=observation.quality,
                    freshness_status=observation.freshness_status,
                    evidence_condition=BoundaryEvidenceCondition.TRUSTWORTHY_CLOSED,
                    proof_status=BoundaryProofStatus.PROVEN_CLOSED,
                    operation_need=BoundaryOperationNeed.OPEN_REQUIRED,
                    reason_codes=("TRUSTWORTHY_CLOSED_REQUIRES_OPEN",),
                )

        reasons: list[str] = []
        if observation is None:
            reasons.append("OBSERVATION_MISSING")
            observed_state = quality = freshness = None
        else:
            observed_state = observation.observed_state
            quality = observation.quality
            freshness = observation.freshness_status
            if observed_state is None:
                reasons.append("OBSERVED_STATE_MISSING")
            if quality is None:
                reasons.append("QUALITY_MISSING")
            elif quality is not TelemetryQuality.GOOD:
                reasons.append(f"QUALITY_{quality.value}")
            if freshness is None:
                reasons.append("FRESHNESS_MISSING")
            elif freshness is not FreshnessStatus.FRESH:
                reasons.append(f"FRESHNESS_{freshness.value}")
        return BoundaryEvaluation(
            boundary_device_id=device_id,
            observed_state=observed_state,
            quality=quality,
            freshness_status=freshness,
            evidence_condition=BoundaryEvidenceCondition.UNTRUSTWORTHY_OR_ABSENT,
            proof_status=BoundaryProofStatus.UNPROVEN,
            operation_need=BoundaryOperationNeed.EVIDENCE_REQUIRED,
            reason_codes=tuple(reasons),
        )
