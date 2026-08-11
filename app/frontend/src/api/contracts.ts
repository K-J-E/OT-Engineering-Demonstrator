export type ScenarioMode = 'FORMAL' | 'EXPLORATION'
export type EvidenceClass = 'FORMAL' | 'EXPLORATORY'
export type SwitchState = 'OPEN' | 'CLOSED'
export type TelemetryQuality = 'GOOD' | 'UNCERTAIN' | 'BAD'
export type Freshness = 'FRESH' | 'STALE' | 'INVALID_TIMESTAMP'
export type CommandType =
  | 'INITIATE_FAULT'
  | 'ACKNOWLEDGE_ALARM'
  | 'OPERATE_ISOLATION_DEVICE'
  | 'RESTORE_NORMAL_SOURCE'
  | 'ASSESS_RESTORATION'
  | 'EXECUTE_RESTORATION'
  | 'RESET_RUN'

export interface LoadedValidationDefinition {
  definition: {
    test_id: string
    title: string
    version: string
    status: string
    evidence_class: EvidenceClass
    requirement_ids: string[]
    source_references: string[]
    objective: string
    method: string
    preconditions: string[]
    controlled_inputs: string[]
    procedure_steps: string[]
    checkpoint_obligations: Array<{ checkpoint_id: string; required_content: string[] }>
    expected_result_statement: string
    comparison_expected_values: Record<string, unknown> | null
    evidence_requirements: string[]
    verdict_rule: string
    reset_repeat_rule: string
    constituent_cases: Array<{
      case_id: string
      test_id: string
      case_title: string
      version: string
      selected_fault_section_id: string
      initial_conditions: Record<string, unknown>
      comparison_expected_values: Record<string, unknown>
      checkpoint_obligations: Array<{ checkpoint_id: string; required_content: string[] }>
    }>
  }
  definition_sha256: string
  catalogue_id: string
  catalogue_version: string
  catalogue_sha256: string
}

export interface WorkspaceBootstrap {
  application_build_id: string
  default_actor: string
  default_mode: ScenarioMode
  default_evidence_class: EvidenceClass
  default_configuration_id: string
  default_configuration_version: string
  default_scenario_time: string
  formal_test_id: string
  formal_definition: LoadedValidationDefinition
  exploration_section_ids: string[]
  definition_count: number
  conceptual_boundary_notice: string
}

export interface RunContext {
  scenario_run_id: string
  mode: ScenarioMode
  configuration_id: string
  configuration_version: string
  fault_section_id: string
  fault_type: string
  initial_scenario_time: string
  scenario_time: string
  state_revision: number
  workflow_stage: string
  network_state_label: string
  evidence_class: EvidenceClass
  application_build_id: string
  status: string
  fault_active: boolean
  source_availability: Record<string, string>
}

export interface WorkspaceNode {
  entity_id: string
  position: { x: number; y: number }
  configured: {
    entity_id: string
    entity_type: 'SOURCE' | 'SWITCHING_DEVICE' | 'SECTION'
    name: string
    feeder_id: string | null
    device_type: string | null
    normal_state: SwitchState | null
    normal_source_availability: string | null
    configured_load_kw: number | null
    customer_zone_id: string | null
    customer_count: number | null
  }
  observed: {
    point_id: string
    value: SwitchState
    quality: TelemetryQuality
    timestamp: string
    age_ms: number
    freshness: Freshness
    overall_valid: boolean
    reason_codes: string[]
  } | null
  derived: {
    energised: boolean | null
    source_feeder_ids: string[]
    source_path_node_ids: string[][]
    current_source_availability: string | null
  }
  fault_status: 'FAULTED' | 'NOT_FAULTED' | 'NOT_APPLICABLE'
}

export interface WorkspaceEdge {
  edge_id: string
  endpoint_a_id: string
  endpoint_b_id: string
  semantics: string
  active: boolean
}

export interface WorkspaceFeeder {
  feeder_id: string
  name: string
  source_id: string
  source_breaker_id: string
  section_ids: string[]
  configured_capacity_kw: number
  configured_normal_load_kw: number
  derived_currently_supplied_load_kw: number | null
  derived_load_attribution_complete: boolean
  derived_supplied_section_ids: string[]
}

export interface TelemetryRow {
  point_id: string
  entity_id: string
  value: SwitchState
  quality: TelemetryQuality
  timestamp: string
  age_ms: number
  freshness: Freshness
  quality_valid: boolean
  timestamp_valid: boolean
  overall_valid: boolean
  reason_codes: string[]
}

export interface AlarmRecord {
  alarm_id: string
  scenario_run_id: string
  entity_id: string
  alarm_type: string
  active: boolean
  acknowledgement_state: string
  generated_scenario_time: string
  acknowledged_scenario_time: string | null
  acknowledged_by: string | null
}

export interface OperationalEvent {
  event_id: string
  scenario_run_id: string
  event_sequence: number
  scenario_time: string
  state_revision: number
  source: string
  event_type: string
  affected_entity_id: string | null
  description: string
  actor: string | null
  previous_value: string | null
  new_value: string | null
  command_id: string | null
  alarm_id: string | null
  assessment_id: string | null
}

export interface RestorationCandidate {
  candidate_id: string
  affected_feeder_id: string
  alternate_feeder_id: string
  alternate_source_id: string
  alternate_source_breaker_id: string
  tie_device_id: string
  requested_tie_state: SwitchState
  proposed_section_ids: string[]
  proposed_path_edge_ids: string[]
  transferable_load_kw: number
  proposed_restored_customer_count: number
}

export interface RestorationAssessment {
  assessment_id: string
  assessment_sequence: number
  scenario_run_id: string
  configuration_id: string
  state_revision: number
  scenario_time: string
  candidate: RestorationCandidate | null
  telemetry_snapshot_sha256: string
  source_availability_sha256: string
  telemetry_evidence: Array<{
    point_id: string
    entity_id: string
    value: SwitchState
    quality: TelemetryQuality
    timestamp: string
    revision: number
    age_ms: number
    freshness: Freshness
    overall_valid: boolean
    reason_codes: string[]
  }>
  source_availability: Record<string, string>
  permissives: Array<{
    criterion: string
    status: 'PASS' | 'FAIL' | 'INSUFFICIENT'
    reason_codes: string[]
    evidence_point_ids: string[]
  }>
  calculation: {
    alternate_feeder_id: string
    existing_supplied_load_kw: number
    transferable_load_kw: number
    resulting_load_kw: number
    feeder_capacity_kw: number
    resulting_loading_percent: number | string
    capacity_pass: boolean
  } | null
  outcome: 'NO_CANDIDATE' | 'BLOCKED' | 'REJECTED' | 'PERMITTED'
  reason_codes: string[]
}

export interface AssessmentInvalidation {
  invalidation_id: string
  assessment_id: string
  scenario_run_id: string
  superseding_state_revision: number
  superseding_scenario_time: string
  reason_code: string
  event_id: string
}

export interface WorkspaceAction {
  action_id: string
  command_type: CommandType
  target_entity_id: string | null
  requested_state: SwitchState | null
  alarm_id: string | null
  assessment_id: string | null
  available: boolean
  reason_code: string
  reason: string
  expected_revision: number
  proposed_scenario_time: string
  confirmation_required: boolean
  confirmation_text: string | null
}

export interface EvidenceSnapshot {
  evidence_snapshot_id: string
  validation_execution_id: string
  test_id: string
  scenario_run_id: string
  evidence_class: EvidenceClass
  configuration_id: string
  configuration_version: string
  application_build_id: string
  state_revision: number
  checkpoint_id: string
  scenario_time: string
  content_categories: string[]
  source_record_references: string[]
  observed_values: Record<string, unknown>
  canonical_payload_sha256: string
}

export interface ValidationExecutionSummary {
  execution: {
    validation_execution_id: string
    test_id: string
    test_definition_version: string
    test_definition_sha256: string
    catalogue_version?: string
    catalogue_sha256: string
    case_id?: string | null
    case_definition_version?: string | null
    case_definition_sha256?: string | null
    scenario_run_id: string
    scenario_mode: ScenarioMode
    evidence_class: EvidenceClass
    configuration_id: string
    configuration_version: string
    application_build_id: string
    status: 'ACTIVE' | 'FINALISED'
    started_scenario_time: string
    finalised_scenario_time: string | null
    expected_result_statement: string
    expected_comparison_values: Record<string, unknown> | null
    observed_result: Record<string, unknown> | null
    calculations: Record<string, unknown> | null
    evidence_snapshot_ids: string[]
    verdict: string | null
    verdict_reason: string | null
    links: Record<string, string | null>
  }
  evidence_snapshots: EvidenceSnapshot[]
}

export interface EvidenceExportCandidate {
  validation_execution_id: string
  test_id: string
  evidence_class: EvidenceClass
  scenario_run_id: string
  source_run_status: string
  export_available: boolean
  reason_code: string
  reason: string
}

export interface EvidencePackage {
  package_id: string
  validation_execution_id: string
  test_id: string
  test_definition_version: string
  test_definition_sha256: string
  evidence_class: EvidenceClass
  scenario_run_id: string
  configuration_id: string
  configuration_version: string
  application_build_id: string
  generation_application_build_id: string
  evidence_snapshot_ids: string[]
  manifest_sha256: string
  archive_sha256: string
  archive_path: string
  verification_status: 'VERIFIED'
  source_record_references: string[]
}

export interface ValidationWorkspaceAction {
  action_type: 'START_EXECUTION' | 'CAPTURE_CHECKPOINT' | 'FINALISE_EXECUTION'
  available: boolean
  reason_code: string
  reason: string
  test_id: string
  case_id: string | null
  validation_execution_id: string | null
  checkpoint_id: string | null
}

export interface CompositeValidationResult {
  composite_result_id: string
  test_id: string
  test_definition_version: string
  test_definition_sha256: string
  catalogue_version: string
  catalogue_sha256: string
  evidence_class: 'EXPLORATORY'
  application_build_id: string
  configuration_id: string
  configuration_version: string
  required_case_ids: string[]
  constituent_links: Array<{
    case_id: string
    source_kind?: 'EXECUTION_RESULT' | 'SUSPENSION_RESULT'
    validation_execution_id: string | null
    executed_result_id?: string | null
    suspension_record_id?: string | null
    scenario_run_id: string | null
    case_definition_sha256: string | null
    unavailable_required_input_role?: 'APPLICATION_BUILD' | 'CONFIGURATION' | 'CATALOGUE' | 'TEST_DEFINITION' | 'CASE_DEFINITION' | 'CONTROLLED_FIXTURE' | null
    constituent_verdict: string | null
    evidence_snapshot_ids: string[]
  }>
  completeness: {
    status: 'INCOMPLETE' | 'COMPLETE'
    required_case_ids: string[]
    present_case_ids: string[]
    missing_case_ids: string[]
    duplicate_case_ids: string[]
    mismatched_case_ids: string[]
    reasons: string[]
  }
  status: 'DRAFT' | 'FINALISED'
  determination: 'PASS' | 'FAIL' | 'BLOCKED-TEST' | null
  determination_reason: string
  source_record_references: string[]
  created_at: string
  finalised_at: string | null
}

export interface ValidationSuspensionRecord {
  suspension_record_id: string
  validation_attempt_id: string
  target_selection_id: string
  condition_id: 'VSC-001' | 'VSC-002' | 'VSC-003' | 'VSC-004' | 'VSC-005'
  lifecycle_position: 'PRE_EXECUTION_ENTRY' | 'EXECUTION_IN_PROGRESS' | 'EVIDENCE_FINALISATION'
  status: 'FINALISED'
  reason_code: string
  deterministic_fingerprint: string
  verifier_application_build_id: string
  evidence: Array<{ evidence_id: string; evidence_type: string; failure_code: string; payload_sha256: string }>
  authority: { authority_kind: string; proposer_actor_id: string; proposer_role: string; reviewer_actor_id: string; reviewer_role: string }
  scenario_run_id: string | null
  validation_execution_id: string | null
  finalised_at: string
}

export interface WorkspaceProjection {
  application_build_id: string
  run: RunContext
  configuration_status: string
  summary: {
    de_energised_section_ids: string[]
    affected_customer_count: number
    restored_customer_delta: number
    active_alarm_count: number
    unacknowledged_alarm_count: number
    current_assessment_status: string
    current_assessment_id: string | null
    current_assessment_invalidated: boolean
    radiality_status: string
  }
  network_nodes: WorkspaceNode[]
  network_edges: WorkspaceEdge[]
  feeders: WorkspaceFeeder[]
  telemetry: TelemetryRow[]
  alarms: AlarmRecord[]
  events: OperationalEvent[]
  isolation_proof: {
    fault_section_id: string
    incident_boundary_device_ids: string[]
    boundary_evaluations: Array<{
      boundary_device_id: string
      observed_state: SwitchState | null
      quality: TelemetryQuality | null
      freshness_status: Freshness | null
      evidence_condition: string
      proof_status: string
      operation_need: string
      reason_codes: string[]
    }>
    active_source_paths: unknown[]
    all_boundaries_proven_open: boolean
    zero_active_source_paths: boolean
    isolated: boolean
    reason_codes: string[]
  } | null
  restoration_assessments: RestorationAssessment[]
  restoration_invalidations: AssessmentInvalidation[]
  allowed_actions: WorkspaceAction[]
  validation: {
    definitions: LoadedValidationDefinition[]
    run_executions: ValidationExecutionSummary[]
    library_executions: ValidationExecutionSummary[]
    composites: CompositeValidationResult[]
    suspensions: ValidationSuspensionRecord[]
    progress: {
      definition_count: number
      definitions_without_execution_count: number
      execution_count: number
      active_execution_count: number
      finalised_execution_count: number
      pass_count: number
      fail_count: number
      blocked_test_count: number
    }
    actions: ValidationWorkspaceAction[]
  }
  conceptual_boundary_notice: string
}

export interface CommandResult {
  accepted: boolean
  reason_code: string
  reason: string
  snapshot: { run: RunContext }
}

export interface InvestigationFact {
  label: string
  value: string
}

export interface InvestigationStep {
  step_id: string
  title: string
  facts: InvestigationFact[]
  source_record_references: string[]
}

export interface InvestigationWorkspace {
  original_failure: ValidationExecutionSummary
  steps: InvestigationStep[]
  configuration_comparison: {
    defective: { configuration_id: string; version: string; package_sha256: string; data_sha256: string; schema_sha256: string }
    corrected: { configuration_id: string; version: string; package_sha256: string; data_sha256: string; schema_sha256: string }
    differences: Array<{ path: string; before: string; after: string }>
    unchanged_information_classes: string[]
  }
  defect_record: null | {
    defect_record_id: string
    defect_id: string
    original_failed_execution_id: string
    root_cause: string
    engineering_propagation: string[]
    recorded_by: string
    investigation_snapshot_sha256: string
  }
  correction_record: null | {
    correction_record_id: string
    correction_id: string
    defect_id: string
    engineering_effect: string
    verification_basis: string[]
    reviewed_by: string
  }
  direct_repeat: ValidationExecutionSummary | null
  regression: ValidationExecutionSummary | null
  repeat_links: Array<{ repeat_link_id: string; relationship_type: 'DIRECT_REPEAT' | 'REGRESSION'; original_execution_id: string; new_execution_id: string; application_build_id: string }>
  actions: Array<{ action_type: 'RECORD_DEFECT' | 'RECORD_CORRECTION' | 'RUN_DIRECT_REPEAT' | 'RUN_REGRESSION'; available: boolean; reason_code: string; reason: string }>
  same_build_proven: boolean
  conceptual_boundary_notice: string
}
