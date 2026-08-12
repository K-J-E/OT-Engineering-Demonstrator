"""Implemented DC-006 structural record ownership registry.

The catalogue freezes the engineering names and owners.  This registry binds
each name to an actual backend domain/schema/projection symbol so NFR evidence
is derived from the implementation rather than recounted from the catalogue.
"""

from __future__ import annotations

from importlib import import_module


IMPLEMENTED_STRUCTURAL_RECORD_SET: dict[str, dict[str, str]] = {
    "ConfigurationCatalogEntry": {"owner": "configuration", "symbol": "ot_demo.modules.configuration.models.ConfigurationCatalogEntry"},
    "NetworkEntity": {"owner": "configuration", "symbol": "ot_demo.domain.configuration.NetworkConfigurationData"},
    "ConnectivityEdge": {"owner": "configuration", "symbol": "ot_demo.domain.configuration.ConnectivityEdge"},
    "LoadCapacity": {"owner": "configuration", "symbol": "ot_demo.domain.configuration.Feeder"},
    "CustomerZoneMapping": {"owner": "configuration", "symbol": "ot_demo.domain.configuration.CustomerZoneMapping"},
    "ConfigurationManifest": {"owner": "configuration", "symbol": "ot_demo.modules.configuration.models.ConfigurationManifest"},
    "ScenarioRun": {"owner": "scenario", "symbol": "ot_demo.modules.scenario.models.RunContext"},
    "TelemetryPoint": {"owner": "telemetry", "symbol": "ot_demo.modules.telemetry.models.TelemetryPoint"},
    "TelemetryValidity": {"owner": "telemetry", "symbol": "ot_demo.modules.telemetry.models.TelemetryValidity"},
    "Alarm": {"owner": "telemetry", "symbol": "ot_demo.modules.telemetry.models.AlarmRecord"},
    "TelemetrySnapshot": {"owner": "telemetry", "symbol": "ot_demo.modules.scenario.models.ScenarioSnapshot"},
    "TopologySnapshot": {"owner": "topology/outage", "symbol": "ot_demo.modules.topology.models.TopologyResult"},
    "SectionDerivedState": {"owner": "topology/outage", "symbol": "ot_demo.modules.topology.models.SectionDerivedState"},
    "IsolationProof": {"owner": "topology/outage", "symbol": "ot_demo.modules.topology.models.IsolationProof"},
    "OutageSnapshot": {"owner": "topology/outage", "symbol": "ot_demo.modules.outage.models.OutageResult"},
    "CalculationTrace": {"owner": "topology/outage", "symbol": "ot_demo.modules.topology.models.TopologyResult"},
    "RestorationCandidate": {"owner": "restoration", "symbol": "ot_demo.modules.restoration.models.RestorationCandidate"},
    "PermissiveResult": {"owner": "restoration", "symbol": "ot_demo.modules.restoration.models.PermissiveResult"},
    "RestorationAssessment": {"owner": "restoration", "symbol": "ot_demo.modules.restoration.models.RestorationAssessment"},
    "AssessmentInvalidation": {"owner": "restoration", "symbol": "ot_demo.modules.restoration.models.AssessmentInvalidation"},
    "RestorationExecutionBinding": {"owner": "restoration", "symbol": "ot_demo.modules.restoration.models.RestorationExecutionBinding"},
    "OperationalEvent": {"owner": "events", "symbol": "ot_demo.modules.events.models.OperationalEvent"},
    "TestDefinition": {"owner": "validation", "symbol": "ot_demo.modules.validation.models.ValidationTestDefinition"},
    "ValidationExecution": {"owner": "validation", "symbol": "ot_demo.modules.validation.models.ValidationExecution"},
    "EvidenceSnapshot": {"owner": "validation", "symbol": "ot_demo.modules.validation.models.EvidenceSnapshot"},
    "ExecutedValidationResult": {"owner": "validation", "symbol": "ot_demo.modules.validation.models.ExecutedValidationResult"},
    "DefectRecord": {"owner": "validation", "symbol": "ot_demo.modules.investigation.models.DefectRecord"},
    "CorrectionRecord": {"owner": "validation", "symbol": "ot_demo.modules.investigation.models.CorrectionRecord"},
    "RepeatLink": {"owner": "validation", "symbol": "ot_demo.modules.investigation.models.RepeatLink"},
    "ConstituentCaseDefinition": {"owner": "validation_assurance", "symbol": "ot_demo.modules.validation.models.ConstituentCaseDefinition"},
    "CompositeValidationResult": {"owner": "validation_assurance", "symbol": "ot_demo.modules.validation.models.CompositeValidationResult"},
    "CompositeConstituentLink": {"owner": "validation_assurance", "symbol": "ot_demo.modules.validation.models.CompositeConstituentLink"},
    "AcceptedCatalogueRevision": {"owner": "validation_assurance", "symbol": "ot_demo.modules.validation.models.LoadedValidationDefinition"},
    "ValidationSuspensionCondition": {"owner": "validation_assurance", "symbol": "ot_demo.domain.enums.ValidationSuspensionCondition"},
    "ValidationSuspensionRecord": {"owner": "validation_assurance", "symbol": "ot_demo.modules.validation.models.ValidationSuspensionRecord"},
    "SuspensionEvidenceRecord": {"owner": "validation_assurance", "symbol": "ot_demo.modules.validation.models.ValidationSuspensionEvidence"},
    "ValidationAttempt": {"owner": "validation_assurance", "symbol": "ot_demo.modules.validation.models.ValidationAttempt"},
    "ValidationTargetSelection": {"owner": "validation_assurance", "symbol": "ot_demo.modules.validation.models.ValidationTargetSelection"},
    "DeterminationMethodDefinition": {"owner": "validation_assurance", "symbol": "ot_demo.modules.validation.models.DeterminationMethodDefinition"},
    "CriterionDefinition": {"owner": "validation_assurance", "symbol": "ot_demo.modules.validation.models.CriterionDefinition"},
    "DeterminationContext": {"owner": "validation_assurance", "symbol": "ot_demo.modules.validation.models.DeterminationContext"},
    "CriterionFinding": {"owner": "validation_assurance", "symbol": "ot_demo.modules.validation.models.CriterionFinding"},
    "EngineeringReviewProposal": {"owner": "validation_assurance", "symbol": "ot_demo.modules.validation.models.EngineeringReviewProposal"},
    "EngineeringReviewFinalisation": {"owner": "validation_assurance", "symbol": "ot_demo.modules.validation.models.EngineeringReviewFinalisation"},
    "EvidencePackage": {"owner": "evidence_export", "symbol": "ot_demo.modules.evidence_export.models.EvidencePackage"},
}


def resolved_structural_registry() -> dict[str, dict[str, str]]:
    """Return the registry only after every implementation symbol resolves."""

    result: dict[str, dict[str, str]] = {}
    for record_name, binding in IMPLEMENTED_STRUCTURAL_RECORD_SET.items():
        module_name, symbol_name = binding["symbol"].rsplit(".", 1)
        module = import_module(module_name)
        getattr(module, symbol_name)
        result[record_name] = dict(binding)
    return result
