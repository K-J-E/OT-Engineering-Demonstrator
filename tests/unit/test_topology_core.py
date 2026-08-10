"""I2 topology domain: REQ-TOP-001–009, REQ-NFR-003/009, DC-003."""

import json
from pathlib import Path

import pytest

from ot_demo.domain.enums import (
    BoundaryEvidenceCondition,
    BoundaryOperationNeed,
    BoundaryProofStatus,
    FreshnessStatus,
    RadialityStatus,
    SourceAvailability,
    SwitchState,
    TelemetryQuality,
)
from ot_demo.domain.configuration import NetworkConfigurationData
from ot_demo.infrastructure.configuration_loader import JsonConfigurationLoader
from ot_demo.modules.configuration.models import LoadedConfiguration
from ot_demo.modules.topology import BoundaryObservation, TopologyInputs, TopologyService
from ot_demo.modules.topology.service import TopologyInputError


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
EXPECTED_BOUNDARIES = {
    "SEC-A1": ("BRK-A", "SW-A12"),
    "SEC-A2": ("SW-A12", "SW-A23"),
    "SEC-A3": ("SW-A23", "SW-A34"),
    "SEC-A4": ("SW-A34", "TS-01"),
    "SEC-B1": ("BRK-B", "SW-B12"),
    "SEC-B2": ("SW-B12", "SW-B23"),
    "SEC-B3": ("SW-B23", "SW-B34"),
    "SEC-B4": ("SW-B34", "TS-01"),
}


@pytest.fixture(scope="module")
def loader() -> JsonConfigurationLoader:
    return JsonConfigurationLoader(REPOSITORY_ROOT / "config/network")


@pytest.fixture(scope="module")
def v11(loader: JsonConfigurationLoader) -> LoadedConfiguration:
    return loader.load("v1.1")


def inputs_for(
    loaded: LoadedConfiguration,
    *,
    device_overrides: dict[str, SwitchState] | None = None,
    source_overrides: dict[str, SourceAvailability] | None = None,
    active_fault: str | None = None,
    observations: dict[str, BoundaryObservation] | None = None,
) -> TopologyInputs:
    normal = TopologyService.normal_inputs(loaded.data)
    device_states = dict(normal.device_states)
    device_states.update(device_overrides or {})
    source_availability = dict(normal.source_availability)
    source_availability.update(source_overrides or {})
    return TopologyInputs(
        device_states=device_states,
        source_availability=source_availability,
        faulted_section_ids=frozenset({active_fault}) if active_fault else frozenset(),
        active_fault_section_id=active_fault,
        boundary_observations=observations or {},
    )


def trustworthy(device_id: str, state: SwitchState) -> BoundaryObservation:
    return BoundaryObservation(
        device_id=device_id,
        observed_state=state,
        quality=TelemetryQuality.GOOD,
        freshness_status=FreshnessStatus.FRESH,
    )


def cyclic_fixture(v11: LoadedConfiguration) -> LoadedConfiguration:
    """Create a validated lower-level fixture without editing the canonical package."""

    payload = v11.data.model_dump(mode="json")
    for edge in payload["connectivity_edges"]:
        if edge["edge_id"] == "EDGE-SW-A23-2":
            edge["endpoint_b_id"] = "SEC-A1"
    data = NetworkConfigurationData.model_validate_json(
        json.dumps(payload),
        strict=True,
    )
    return LoadedConfiguration(
        catalog_entry=v11.catalog_entry,
        manifest=v11.manifest,
        data=data,
    )


@pytest.mark.i2
def test_normal_v11_derives_all_sections_sources_load_and_radiality(
    v11: LoadedConfiguration,
) -> None:
    result = TopologyService().calculate(v11, inputs_for(v11))
    sections = {state.section_id: state for state in result.sections}
    loads = {load.feeder_id: load for load in result.feeder_loads}

    assert all(state.energised for state in sections.values())
    assert {
        section_id: state.source_feeder_ids
        for section_id, state in sections.items()
    } == {
        "SEC-A1": ("FDR-A",),
        "SEC-A2": ("FDR-A",),
        "SEC-A3": ("FDR-A",),
        "SEC-A4": ("FDR-A",),
        "SEC-B1": ("FDR-B",),
        "SEC-B2": ("FDR-B",),
        "SEC-B3": ("FDR-B",),
        "SEC-B4": ("FDR-B",),
    }
    assert result.radiality_status is RadialityStatus.RADIAL
    assert result.unintended_loop_component_section_ids == ()
    assert result.available_source_ids == ("ZS-01",)
    assert result.available_source_feeder_ids == ("FDR-A", "FDR-B")
    assert result.active_source_feeder_ids == ("FDR-A", "FDR-B")
    assert len(result.active_edge_ids) == 16
    assert loads["FDR-A"].configured_normal_load_kw == 3200
    assert loads["FDR-A"].currently_supplied_load_kw == 3200
    assert loads["FDR-B"].configured_normal_load_kw == 4200
    assert loads["FDR-B"].currently_supplied_load_kw == 4200


@pytest.mark.i2
def test_fault_status_is_independent_from_energisation(v11: LoadedConfiguration) -> None:
    result = TopologyService().calculate(
        v11,
        inputs_for(v11, active_fault="SEC-A2"),
    )
    section = next(item for item in result.sections if item.section_id == "SEC-A2")

    assert section.faulted is True
    assert section.energised is True
    assert section.source_feeder_ids == ("FDR-A",)


@pytest.mark.i2
def test_source_unavailability_removes_energisation_without_changing_active_edges(
    v11: LoadedConfiguration,
) -> None:
    result = TopologyService().calculate(
        v11,
        inputs_for(
            v11,
            source_overrides={"ZS-01": SourceAvailability.UNAVAILABLE},
        ),
    )

    assert not any(section.energised for section in result.sections)
    assert result.available_source_ids == ()
    assert result.active_source_feeder_ids == ()
    assert len(result.active_edge_ids) == 16


@pytest.mark.i2
def test_closed_tie_with_two_active_feeder_sources_is_not_radial(
    v11: LoadedConfiguration,
) -> None:
    result = TopologyService().calculate(
        v11,
        inputs_for(v11, device_overrides={"TS-01": SwitchState.CLOSED}),
    )

    assert result.radiality_status is RadialityStatus.UNINTENDED_LOOP
    assert result.unintended_loop_component_section_ids == (
        tuple(sorted(EXPECTED_BOUNDARIES)),
    )
    assert all(len(section.source_feeder_ids) == 2 for section in result.sections)
    assert all(
        load.currently_supplied_load_kw is None
        and not load.load_attribution_complete
        for load in result.feeder_loads
    )


@pytest.mark.i2
def test_energised_cyclic_component_is_an_unintended_loop(
    v11: LoadedConfiguration,
) -> None:
    fixture = cyclic_fixture(v11)
    result = TopologyService().calculate(fixture, inputs_for(fixture))

    assert result.radiality_status is RadialityStatus.UNINTENDED_LOOP
    assert result.unintended_loop_component_section_ids == (("SEC-A1", "SEC-A2"),)


@pytest.mark.i2
def test_de_energised_cyclic_component_is_not_an_unintended_energised_loop(
    v11: LoadedConfiguration,
) -> None:
    fixture = cyclic_fixture(v11)
    result = TopologyService().calculate(
        fixture,
        inputs_for(fixture, device_overrides={"BRK-A": SwitchState.OPEN}),
    )
    sections = {section.section_id: section for section in result.sections}

    assert result.radiality_status is RadialityStatus.RADIAL
    assert result.unintended_loop_component_section_ids == ()
    assert sections["SEC-A1"].energised is False
    assert sections["SEC-A2"].energised is False


@pytest.mark.i2
@pytest.mark.parametrize(("section_id", "expected"), EXPECTED_BOUNDARIES.items())
def test_all_v11_incident_boundary_pairs_are_derived_from_connectivity(
    v11: LoadedConfiguration,
    section_id: str,
    expected: tuple[str, str],
) -> None:
    result = TopologyService().calculate(
        v11,
        inputs_for(v11, active_fault=section_id),
    )

    assert result.isolation_proof is not None
    assert result.isolation_proof.incident_boundary_device_ids == tuple(sorted(expected))


@pytest.mark.i2
@pytest.mark.parametrize(
    ("observation", "condition", "proof", "operation"),
    [
        (
            trustworthy("TS-01", SwitchState.OPEN),
            BoundaryEvidenceCondition.TRUSTWORTHY_OPEN,
            BoundaryProofStatus.PROVEN_OPEN,
            BoundaryOperationNeed.NONE_SATISFIED,
        ),
        (
            trustworthy("TS-01", SwitchState.CLOSED),
            BoundaryEvidenceCondition.TRUSTWORTHY_CLOSED,
            BoundaryProofStatus.PROVEN_CLOSED,
            BoundaryOperationNeed.OPEN_REQUIRED,
        ),
        (
            BoundaryObservation(
                device_id="TS-01",
                observed_state=SwitchState.OPEN,
                quality=TelemetryQuality.GOOD,
                freshness_status=FreshnessStatus.STALE,
            ),
            BoundaryEvidenceCondition.UNTRUSTWORTHY_OR_ABSENT,
            BoundaryProofStatus.UNPROVEN,
            BoundaryOperationNeed.EVIDENCE_REQUIRED,
        ),
        (
            BoundaryObservation(
                device_id="TS-01",
                observed_state=SwitchState.OPEN,
                quality=TelemetryQuality.UNCERTAIN,
                freshness_status=FreshnessStatus.FRESH,
            ),
            BoundaryEvidenceCondition.UNTRUSTWORTHY_OR_ABSENT,
            BoundaryProofStatus.UNPROVEN,
            BoundaryOperationNeed.EVIDENCE_REQUIRED,
        ),
        (
            BoundaryObservation(
                device_id="TS-01",
                observed_state=SwitchState.OPEN,
                quality=TelemetryQuality.BAD,
                freshness_status=FreshnessStatus.FRESH,
            ),
            BoundaryEvidenceCondition.UNTRUSTWORTHY_OR_ABSENT,
            BoundaryProofStatus.UNPROVEN,
            BoundaryOperationNeed.EVIDENCE_REQUIRED,
        ),
        (
            BoundaryObservation(
                device_id="TS-01",
                observed_state=SwitchState.OPEN,
                quality=TelemetryQuality.GOOD,
                freshness_status=FreshnessStatus.INVALID_TIMESTAMP,
            ),
            BoundaryEvidenceCondition.UNTRUSTWORTHY_OR_ABSENT,
            BoundaryProofStatus.UNPROVEN,
            BoundaryOperationNeed.EVIDENCE_REQUIRED,
        ),
    ],
)
def test_dc003_boundary_evidence_conditions(
    v11: LoadedConfiguration,
    observation: BoundaryObservation,
    condition: BoundaryEvidenceCondition,
    proof: BoundaryProofStatus,
    operation: BoundaryOperationNeed,
) -> None:
    result = TopologyService().calculate(
        v11,
        inputs_for(
            v11,
            active_fault="SEC-A4",
            observations={"TS-01": observation},
        ),
    )
    assert result.isolation_proof is not None
    evaluation = next(
        item
        for item in result.isolation_proof.boundary_evaluations
        if item.boundary_device_id == "TS-01"
    )

    assert evaluation.evidence_condition is condition
    assert evaluation.proof_status is proof
    assert evaluation.operation_need is operation


@pytest.mark.i2
def test_missing_boundary_evidence_is_unproven_without_open_operation(
    v11: LoadedConfiguration,
) -> None:
    result = TopologyService().calculate(
        v11,
        inputs_for(v11, active_fault="SEC-A4"),
    )
    assert result.isolation_proof is not None
    tie = next(
        item
        for item in result.isolation_proof.boundary_evaluations
        if item.boundary_device_id == "TS-01"
    )

    assert tie.proof_status is BoundaryProofStatus.UNPROVEN
    assert tie.operation_need is BoundaryOperationNeed.EVIDENCE_REQUIRED
    assert tie.reason_codes == ("OBSERVATION_MISSING",)


@pytest.mark.i2
def test_isolation_requires_all_boundaries_proven_open_and_zero_paths(
    v11: LoadedConfiguration,
) -> None:
    boundary_observations = {
        device_id: trustworthy(device_id, SwitchState.OPEN)
        for device_id in ("SW-A12", "SW-A23")
    }
    isolated = TopologyService().calculate(
        v11,
        inputs_for(
            v11,
            device_overrides={
                "SW-A12": SwitchState.OPEN,
                "SW-A23": SwitchState.OPEN,
            },
            active_fault="SEC-A2",
            observations=boundary_observations,
        ),
    )
    path_remains = TopologyService().calculate(
        v11,
        inputs_for(
            v11,
            active_fault="SEC-A2",
            observations=boundary_observations,
        ),
    )

    assert isolated.isolation_proof is not None
    assert isolated.isolation_proof.all_boundaries_proven_open is True
    assert isolated.isolation_proof.zero_active_source_paths is True
    assert isolated.isolation_proof.isolated is True
    assert path_remains.isolation_proof is not None
    assert path_remains.isolation_proof.all_boundaries_proven_open is True
    assert path_remains.isolation_proof.zero_active_source_paths is False
    assert path_remains.isolation_proof.isolated is False


@pytest.mark.i2
def test_inputs_must_cover_configured_devices_and_sources(v11: LoadedConfiguration) -> None:
    normal = TopologyService.normal_inputs(v11.data)
    incomplete_states = dict(normal.device_states)
    incomplete_states.pop("TS-01")

    with pytest.raises(TopologyInputError, match="every configured device exactly once"):
        TopologyService().calculate(
            v11,
            TopologyInputs(
                device_states=incomplete_states,
                source_availability=dict(normal.source_availability),
            ),
        )
