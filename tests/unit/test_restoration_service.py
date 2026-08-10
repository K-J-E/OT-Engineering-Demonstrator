"""Focused I4 decision precedence and capacity gates."""

from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

import pytest

from ot_demo.domain.enums import (
    PermissiveStatus,
    RadialityStatus,
    RestorationCriterion,
    RestorationOutcome,
    SwitchState,
    TelemetryQuality,
)
from ot_demo.infrastructure.configuration_loader import JsonConfigurationLoader
from ot_demo.modules.outage import OutageService
from ot_demo.modules.restoration import RestorationAssessmentInputs, RestorationService
from ot_demo.modules.telemetry.models import TelemetryPoint
from ot_demo.modules.telemetry.service import TelemetryValidityService
from ot_demo.modules.topology import BoundaryObservation, TopologyInputs, TopologyService


ROOT = Path(__file__).resolve().parents[2]
T0 = datetime(2030, 1, 1, tzinfo=timezone.utc)


def formal_n3_inputs():
    loaded = JsonConfigurationLoader(ROOT / "config/network").load("v1.1")
    states = {
        device.entity_id: device.normal_state
        for device in loaded.data.switching_devices
    }
    states.update({"SW-A12": SwitchState.OPEN, "SW-A23": SwitchState.OPEN})
    telemetry = tuple(
        TelemetryPoint(
            point_id=device.entity_id,
            entity_id=device.entity_id,
            value=states[device.entity_id],
            quality=TelemetryQuality.GOOD,
            last_update_scenario_time=T0,
            revision=4,
        )
        for device in sorted(loaded.data.switching_devices, key=lambda item: item.entity_id)
    )
    validity_service = TelemetryValidityService()
    validities = tuple(validity_service.classify(point, T0) for point in telemetry)
    sources = TopologyService.normal_inputs(loaded.data).source_availability
    topology = TopologyService().calculate(
        loaded,
        TopologyInputs(
            device_states=states,
            source_availability=sources,
            faulted_section_ids=frozenset({"SEC-A2"}),
            active_fault_section_id="SEC-A2",
            boundary_observations={
                point.entity_id: BoundaryObservation(
                    device_id=point.entity_id,
                    observed_state=point.value,
                    quality=point.quality,
                    freshness_status=validities[index].freshness,
                )
                for index, point in enumerate(telemetry)
            },
        ),
    )
    outage = OutageService().calculate(loaded, topology)
    return loaded, RestorationAssessmentInputs(
        assessment_id=UUID(int=1),
        assessment_sequence=1,
        scenario_run_id=UUID(int=2),
        state_revision=4,
        scenario_time=T0,
        fault_section_id="SEC-A2",
        telemetry=telemetry,
        telemetry_validity=validities,
        source_availability=dict(sources),
        current_topology=topology,
        current_outage=outage,
    )


@pytest.mark.i4
def test_no_candidate_has_precedence_and_no_permissives(monkeypatch) -> None:
    loaded, inputs = formal_n3_inputs()
    service = RestorationService()
    monkeypatch.setattr(service, "discover_candidate", lambda *_: None)
    assessment = service.assess(loaded, inputs)
    assert assessment.outcome is RestorationOutcome.NO_CANDIDATE
    assert assessment.candidate is None
    assert assessment.permissives == ()


@pytest.mark.i4
def test_trustworthy_energised_loop_is_rejected(monkeypatch) -> None:
    loaded, inputs = formal_n3_inputs()
    service = RestorationService()
    candidate = service.discover_candidate(loaded, inputs)
    assert candidate is not None
    original = service._proposed_topology(loaded, inputs, candidate)
    looped = original.model_copy(
        update={
            "radiality_status": RadialityStatus.UNINTENDED_LOOP,
            "unintended_loop_component_section_ids": (("SEC-A3", "SEC-A4"),),
        }
    )
    monkeypatch.setattr(service, "_proposed_topology", lambda *_: looped)
    assessment = service.assess(loaded, inputs)
    radial = next(
        item
        for item in assessment.permissives
        if item.criterion is RestorationCriterion.RADIAL_TOPOLOGY
    )
    assert radial.status is PermissiveStatus.FAIL
    assert assessment.outcome is RestorationOutcome.REJECTED


@pytest.mark.i4
def test_complete_evidence_with_failed_isolation_is_rejected() -> None:
    loaded, inputs = formal_n3_inputs()
    proof = inputs.current_topology.isolation_proof
    assert proof is not None
    not_isolated = proof.model_copy(
        update={
            "all_boundaries_proven_open": False,
            "isolated": False,
            "reason_codes": ("INCIDENT_BOUNDARIES_NOT_ALL_PROVEN_OPEN",),
        }
    )
    changed_topology = inputs.current_topology.model_copy(
        update={"isolation_proof": not_isolated}
    )
    assessment = RestorationService().assess(
        loaded,
        RestorationAssessmentInputs(
            **{
                **inputs.__dict__,
                "current_topology": changed_topology,
            }
        ),
    )
    isolation = next(
        item
        for item in assessment.permissives
        if item.criterion is RestorationCriterion.FAULT_ISOLATION
    )
    assert isolation.status is PermissiveStatus.FAIL
    assert assessment.outcome is RestorationOutcome.REJECTED
