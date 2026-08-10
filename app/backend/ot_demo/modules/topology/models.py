"""Pure-domain inputs and deterministic topology read models for I2."""

from typing import Annotated

from pydantic import Field, model_validator
from typing_extensions import Self

from ...domain.base import FrozenModel
from ...domain.enums import (
    BoundaryEvidenceCondition,
    BoundaryOperationNeed,
    BoundaryProofStatus,
    FreshnessStatus,
    RadialityStatus,
    SourceAvailability,
    SwitchState,
    TelemetryQuality,
)
from ...domain.value_objects import ConfigurationId, EngineeringId, NonNegativeKilowatts


class BoundaryObservation(FrozenModel):
    """Preclassified evidence supplied to I2; timestamp arithmetic belongs to I3."""

    device_id: EngineeringId
    observed_state: SwitchState | None
    quality: TelemetryQuality | None
    freshness_status: FreshnessStatus | None


class TopologyInputs(FrozenModel):
    """Complete pure-domain state needed to evaluate one network revision."""

    device_states: dict[EngineeringId, SwitchState]
    source_availability: dict[EngineeringId, SourceAvailability]
    faulted_section_ids: frozenset[EngineeringId] = frozenset()
    active_fault_section_id: EngineeringId | None = None
    boundary_observations: dict[EngineeringId, BoundaryObservation] = Field(
        default_factory=dict
    )

    @model_validator(mode="after")
    def active_fault_is_faulted(self) -> Self:
        if (
            self.active_fault_section_id is not None
            and self.active_fault_section_id not in self.faulted_section_ids
        ):
            raise ValueError("active_fault_section_id must be present in faulted_section_ids")
        mismatched = sorted(
            key
            for key, observation in self.boundary_observations.items()
            if key != observation.device_id
        )
        if mismatched:
            raise ValueError(
                "boundary observation keys must match observation device IDs: "
                f"{mismatched}"
            )
        return self


class SourcePath(FrozenModel):
    source_id: EngineeringId
    source_feeder_id: EngineeringId
    source_breaker_id: EngineeringId
    target_section_id: EngineeringId
    node_ids: Annotated[tuple[EngineeringId, ...], Field(min_length=3)]
    edge_ids: Annotated[tuple[EngineeringId, ...], Field(min_length=2)]


class SectionDerivedState(FrozenModel):
    section_id: EngineeringId
    energised: bool
    faulted: bool
    source_feeder_ids: tuple[EngineeringId, ...]
    source_paths: tuple[SourcePath, ...]

    @model_validator(mode="after")
    def validate_path_summary(self) -> Self:
        path_feeders = tuple(sorted({path.source_feeder_id for path in self.source_paths}))
        if self.source_feeder_ids != path_feeders:
            raise ValueError("source_feeder_ids must summarize source_paths")
        if self.energised != bool(self.source_paths):
            raise ValueError("energised must be derived from source-path presence")
        return self


class DerivedFeederLoad(FrozenModel):
    feeder_id: EngineeringId
    configured_normal_load_kw: NonNegativeKilowatts
    currently_supplied_load_kw: NonNegativeKilowatts | None
    supplied_section_ids: tuple[EngineeringId, ...]
    multiply_supplied_section_ids: tuple[EngineeringId, ...]
    load_attribution_complete: bool


class BoundaryEvaluation(FrozenModel):
    """Evidence result only; operation_need is not I3 workflow authorisation."""

    boundary_device_id: EngineeringId
    observed_state: SwitchState | None
    quality: TelemetryQuality | None
    freshness_status: FreshnessStatus | None
    evidence_condition: BoundaryEvidenceCondition
    proof_status: BoundaryProofStatus
    operation_need: BoundaryOperationNeed
    reason_codes: tuple[str, ...]


class IsolationProof(FrozenModel):
    fault_section_id: EngineeringId
    incident_boundary_device_ids: tuple[EngineeringId, ...]
    boundary_evaluations: tuple[BoundaryEvaluation, ...]
    evaluated_source_feeder_ids: tuple[EngineeringId, ...]
    active_source_paths: tuple[SourcePath, ...]
    all_boundaries_proven_open: bool
    zero_active_source_paths: bool
    isolated: bool
    reason_codes: tuple[str, ...]

    @model_validator(mode="after")
    def validate_result_conjunction(self) -> Self:
        expected = self.all_boundaries_proven_open and self.zero_active_source_paths
        if self.isolated != expected:
            raise ValueError("isolation requires all boundaries open and zero source paths")
        return self


class TopologyResult(FrozenModel):
    configuration_id: ConfigurationId
    configured_edge_ids: tuple[EngineeringId, ...]
    active_edge_ids: tuple[EngineeringId, ...]
    available_source_ids: tuple[EngineeringId, ...]
    available_source_feeder_ids: tuple[EngineeringId, ...]
    active_source_feeder_ids: tuple[EngineeringId, ...]
    radiality_status: RadialityStatus
    unintended_loop_component_section_ids: tuple[tuple[EngineeringId, ...], ...]
    sections: tuple[SectionDerivedState, ...]
    feeder_loads: tuple[DerivedFeederLoad, ...]
    isolation_proof: IsolationProof | None
