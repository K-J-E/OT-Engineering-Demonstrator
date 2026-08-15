import type { ValidationExecutionSummary, ValidationWorkspaceAction, WorkspaceProjection } from '../../api/contracts'
import { formatTime, humanise, shortId } from '../../components/format'
import { checkpointLabel } from '../../components/scenario-language'

type ValidationStage = {
  checkpoint: string
  title: string
  validation: string
  evidence: string
}

type LoadedDefinition = WorkspaceProjection['validation']['definitions'][number]

function observedNumber(summary: ValidationExecutionSummary | undefined, checkpoint: string, field: string): number | null {
  const value = summary?.evidence_snapshots.find((item) => item.checkpoint_id === checkpoint)?.observed_values[field]
  return typeof value === 'number' ? value : null
}

function controlledValue(summary: ValidationExecutionSummary | undefined, field: string): unknown {
  return summary?.evidence_snapshots.find((item) => item.checkpoint_id === 'CONTROLLED_RESULT')?.observed_values[field]
    ?? summary?.execution.observed_result?.[field]
}

function controlledNumber(summary: ValidationExecutionSummary | undefined, field: string): number | null {
  const value = controlledValue(summary, field)
  return typeof value === 'number' ? value : typeof value === 'string' && Number.isFinite(Number(value)) ? Number(value) : null
}

function controlledText(summary: ValidationExecutionSummary | undefined, field: string): string | null {
  const value = controlledValue(summary, field)
  return typeof value === 'string' && value.length > 0 ? value : null
}

function controlledTextList(summary: ValidationExecutionSummary | undefined, field: string): string[] {
  const value = controlledValue(summary, field)
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === 'string') : []
}

function StageValidationGrid({ stages, currentCheckpoint, savedCheckpoints, exploration = false }: {
  stages: ValidationStage[]
  currentCheckpoint: string
  savedCheckpoints: Set<string>
  exploration?: boolean
}) {
  const currentNumber = Number(currentCheckpoint.slice(1)) || 0
  const explorationComplete = savedCheckpoints.has('CONTROLLED_RESULT')
  return <div className="stage-validation-grid" aria-label="How each operating stage was checked">{stages.map((stage, index) => {
    const stageNumber = Number(stage.checkpoint.slice(1)) || index
    const saved = exploration ? explorationComplete : savedCheckpoints.has(stage.checkpoint)
    const reached = stageNumber <= currentNumber
    const state = saved ? 'saved' : stageNumber === currentNumber ? 'current' : reached ? 'reached' : 'upcoming'
    const status = saved ? (exploration ? 'Included in saved result' : 'Checked and saved') : state === 'current' ? 'Current stage' : reached ? 'Reached—not yet saved' : 'Not reached yet'
    return <article className={state} key={stage.checkpoint}>
      <div className="stage-validation-heading"><span className="stage-number">{index + 1}</span><div><span className="eyebrow">{status}</span><h3>{stage.title}</h3></div></div>
      <p><strong>How it is checked:</strong> {stage.validation}</p>
      <p className="stage-evidence"><strong>Evidence:</strong> {stage.evidence}</p>
    </article>
  })}</div>
}

function ValidationActions({ actions, busy, onAction }: { actions: ValidationWorkspaceAction[]; busy: boolean; onAction: (action: ValidationWorkspaceAction) => void }) {
  if (actions.length === 0) return null
  return <div className="validation-actions">{actions.map((action) => {
    const label = action.action_type === 'START_EXECUTION'
      ? 'Create the validation record'
      : action.action_type === 'CAPTURE_CHECKPOINT'
        ? 'Save the current operating result'
        : 'Complete the validation record'
    return <article key={`${action.test_id}:${action.case_id ?? 'single'}:${action.action_type}`}><button type="button" disabled={!action.available || busy} onClick={() => onAction(action)}>{label}</button><p>{action.reason}</p><span className="reason-code">{humanise(action.reason_code)}</span></article>
  })}</div>
}

function AssuranceValidationModel() {
  return <section className="panel confidence-model" aria-labelledby="confidence-model-title">
    <div className="panel-heading"><div><span className="eyebrow">Two layers of confidence</span><h2 id="confidence-model-title">Operating assurance and system validation are different</h2></div></div>
    <div className="confidence-model-grid">
      <article><span className="status-badge assurance">During the run</span><h3>Operational assurance</h3><p>The operating logic checks the current network, telemetry and safety conditions before allowing each action. It answers: <strong>is this action justified and safe now?</strong></p></article>
      <article><span className="status-badge validation">Above the run</span><h3>System validation</h3><p>A separate evidence-and-comparison layer tests the operating logic against accepted expected outcomes. It answers: <strong>did the operating mechanism calculate and control the scenario correctly?</strong></p></article>
    </div>
    <p className="confidence-connection"><strong>Why both are needed:</strong> operational assurance can correctly apply the information it was given, while system validation can still expose a defective configuration, untrustworthy telemetry input or an error in the topology, outage or restoration logic.</p>
  </section>
}

function campaignTitle(definition: LoadedDefinition): string {
  if (definition.definition.test_id === 'VT-EXP-ALL-001') return 'All represented fault locations'
  if (definition.definition.test_id === 'VT-EXP-ROLE-001') return 'Feeder-role reversal and varied restoration outcomes'
  return definition.definition.title
}

function campaignPurpose(definition: LoadedDefinition): string {
  if (definition.definition.test_id === 'VT-EXP-ALL-001') return 'Checks that each represented fault location derives the correct affected feeder, isolation boundaries, customer impact and telemetry-trust response.'
  if (definition.definition.test_id === 'VT-EXP-ROLE-001') return 'Checks that the same network logic works with either feeder in the affected or alternate role and correctly produces permitted, rejected or no-candidate outcomes.'
  return definition.definition.objective
}

function ExplorationValidationProcedure({ projection, definitions, summary, actions, busy, onAction }: {
  projection: WorkspaceProjection
  definitions: LoadedDefinition[]
  summary: ValidationExecutionSummary | undefined
  actions: ValidationWorkspaceAction[]
  busy: boolean
  onAction: (action: ValidationWorkspaceAction) => void
}) {
  const executions = [...projection.validation.library_executions, ...projection.validation.run_executions]
    .filter((item, index, all) => all.findIndex((candidate) => candidate.execution.validation_execution_id === item.execution.validation_execution_id) === index)
  const campaigns = definitions.filter((item) => item.definition.constituent_cases.length > 0)
  const availableActions = actions.filter((item) => item.available)
  const currentCase = definitions
    .flatMap((item) => item.definition.constituent_cases.map((caseDefinition) => ({ definition: item, caseDefinition })))
    .find((item) => item.definition.definition.test_id === summary?.execution.test_id && item.caseDefinition.case_id === summary.execution.case_id)
  const preservedResultCount = summary?.evidence_snapshots.length ?? 0

  return <section className="panel validation-procedure" aria-labelledby="exploration-procedure-title">
    <div className="panel-heading"><div><span className="eyebrow">Validation procedure</span><h2 id="exploration-procedure-title">How the trial evidence is controlled and extended</h2></div><span className={`status-badge ${summary?.execution.status === 'FINALISED' ? 'success' : 'neutral'}`}>{summary?.execution.status === 'FINALISED' ? 'Current result complete' : 'Current result in progress'}</span></div>
    <p>This is more than a results summary. It shows how one calculated outcome becomes an auditable record and how separate runs can later prove behaviour across different network conditions without being merged into a fictional scenario.</p>
    <div className="procedure-grid" aria-label="Trial validation procedure">
      <article><span className="procedure-number">1</span><div><h3>Bind controlled inputs</h3><p>The selected section, accepted network configuration, application version, test definition and scenario identity are fixed before comparison.</p></div></article>
      <article><span className="procedure-number">2</span><div><h3>Preserve the calculated result</h3><p>Topology, isolation, outage, restoration and source identities are saved together in an immutable controlled-result snapshot.</p></div></article>
      <article><span className="procedure-number">3</span><div><h3>Compare with the accepted case</h3><p>The observed result is compared with the case-specific expected values. A blocked operational action may be correct; a blocked test means valid evidence could not be produced.</p></div></article>
      <article><span className="procedure-number">4</span><div><h3>Build exact multi-run evidence</h3><p>Each scenario keeps its own identity. A campaign result can be assembled only from the required constituent cases, with missing, duplicate or mismatched membership made explicit.</p></div></article>
    </div>

    <div className="current-validation-contribution">
      <div><span className="eyebrow">Current run contribution</span><h3>{currentCase?.caseDefinition.case_title ?? `${projection.run.fault_section_id} controlled trial result`}</h3></div>
      <div className="contribution-status"><span className={`status-badge ${summary?.execution.status === 'FINALISED' ? 'success' : 'neutral'}`}>{summary?.execution.status === 'FINALISED' ? 'Immutable result saved' : 'Evidence being assembled'}</span><strong>{preservedResultCount} controlled result{preservedResultCount === 1 ? '' : 's'}</strong><span>{summary?.execution.verdict ?? 'Not yet determined'}</span></div>
      <p>{currentCase === undefined ? 'This run remains a separately identifiable trial record.' : `This run contributes the ${currentCase.caseDefinition.case_id} constituent case to “${campaignTitle(currentCase.definition)}”. It does not imply that the other required scenarios have been executed.`}</p>
    </div>

    <section className="campaign-section" aria-labelledby="multi-scenario-campaigns-title">
      <div className="section-heading"><div><span className="eyebrow">Cross-scenario assurance</span><h3 id="multi-scenario-campaigns-title">Multi-scenario validation campaigns</h3></div><p>Coverage is calculated from finalised, separately preserved trial executions in this evidence history.</p></div>
      <div className="callout neutral"><strong>Catalogue/reference view.</strong> This section shows the wider controlled validation design; it is not a requirement for completing the current trial. The selectable fault-location trials can populate the standard cases, while special stale-boundary and feeder-role cases are retained as catalogue references and exercised through controlled validation tests rather than launched from this reviewer page. An incomplete campaign count does not change the result above.</div>
      {campaigns.length === 0 ? <p className="empty-state">No constituent-case campaign is exposed by the loaded validation catalogue.</p> : <div className="campaign-grid">{campaigns.map((campaign) => {
        const cases = campaign.definition.constituent_cases
        const requiredCaseIds = new Set(cases.map((item) => item.case_id))
        const savedCases = new Set(executions.filter((item) => item.execution.test_id === campaign.definition.test_id
          && item.execution.status === 'FINALISED'
          && item.execution.case_id !== null
          && item.execution.case_id !== undefined
          && requiredCaseIds.has(item.execution.case_id)
          && item.execution.test_definition_sha256 === campaign.definition_sha256
          && item.execution.configuration_id === projection.run.configuration_id
          && item.execution.configuration_version === projection.run.configuration_version
          && item.execution.application_build_id === projection.application_build_id).map((item) => item.execution.case_id!))
        const latestComposite = projection.validation.composites.filter((item) => item.test_id === campaign.definition.test_id).at(-1)
        return <article className="campaign-card" aria-label={`Validation campaign: ${campaignTitle(campaign)}`} key={campaign.definition.test_id}>
          <div className="campaign-heading"><div><h4>{campaignTitle(campaign)}</h4><p>{campaignPurpose(campaign)}</p></div><span className={`status-badge ${savedCases.size === cases.length && cases.length > 0 ? 'success' : 'neutral'}`}>{savedCases.size} of {cases.length} cases preserved</span></div>
          <ul className="campaign-case-list">{cases.map((caseDefinition) => {
            const isCurrent = summary?.execution.test_id === campaign.definition.test_id && summary.execution.case_id === caseDefinition.case_id
            const isSaved = savedCases.has(caseDefinition.case_id)
            return <li key={caseDefinition.case_id}><div><strong>{caseDefinition.case_title}</strong><small>{caseDefinition.selected_fault_section_id} · {caseDefinition.case_id}</small></div><span className={`status-badge ${isSaved ? 'success' : 'neutral'}`}>{isCurrent ? (isSaved ? 'Current run saved' : 'Current run') : isSaved ? 'Earlier run saved' : 'Separate run required'}</span></li>
          })}</ul>
          <details className="technical-details campaign-records"><summary>Campaign composition and records</summary>{latestComposite === undefined ? <p>No combined campaign record has been assembled from this evidence history yet. The validation service retains each result separately and will refuse a final campaign determination until the exact required membership is present.</p> : <><div className="composite-summary"><strong>{latestComposite.completeness.status === 'COMPLETE' ? 'Complete constituent membership' : 'Incomplete constituent membership'}</strong><span>{latestComposite.determination ?? 'No campaign determination'} · {latestComposite.status}</span></div><p>{latestComposite.determination_reason}</p><p><strong>Present cases:</strong> {latestComposite.completeness.present_case_ids.join(', ') || 'none'}</p><p><strong>Missing cases:</strong> {latestComposite.completeness.missing_case_ids.join(', ') || 'none'}</p><div className="record-list">{latestComposite.constituent_links.map((link) => <article key={link.case_id}><strong>{link.case_id}</strong><span>{link.source_kind === 'SUSPENSION_RESULT' ? 'Stopped attempt record' : 'Executed result'} · {link.constituent_verdict ?? 'No determination'}</span><small>Run {link.scenario_run_id ?? 'not created'} · source {link.validation_execution_id ?? link.suspension_record_id}</small></article>)}</div></>}</details>
        </article>
      })}</div>}
    </section>

    <div className="validation-safeguard"><div><span className="eyebrow">Invalid-result safeguard</span><h3>Required evidence is never guessed</h3><p>If a controlled input is missing or becomes invalid, the attempt is preserved as stopped evidence instead of being assigned a misleading PASS or FAIL.</p></div><span className="status-badge neutral">{projection.validation.suspensions.length} stopped attempt{projection.validation.suspensions.length === 1 ? '' : 's'} recorded</span></div>
    {projection.validation.suspensions.length > 0 && <details className="technical-details"><summary>Stopped-attempt records</summary><div className="record-list">{projection.validation.suspensions.map((item) => <article key={item.suspension_record_id}><strong>{humanise(item.reason_code)}</strong><span>{humanise(item.lifecycle_position)} · {humanise(item.authority.authority_kind)}</span><small>Attempt {item.validation_attempt_id} · target {item.target_selection_id}</small></article>)}</div></details>}
    {availableActions.length > 0 && <ValidationActions actions={availableActions} busy={busy} onAction={onAction} />}
  </section>
}

function ExplorationValidation({ projection, busy, onAction, onContinue }: {
  projection: WorkspaceProjection
  busy: boolean
  onAction: (action: ValidationWorkspaceAction) => void
  onContinue: (view: 'operational' | 'restoration') => void
}) {
  const definitions = projection.validation.definitions.filter((item) => item.definition.evidence_class === 'EXPLORATORY')
  const definition = definitions.find((item) => item.definition.test_id === 'VT-EXP-ALL-001') ?? definitions[0]
  const summary = projection.validation.run_executions.find((item) => item.execution.test_id === 'VT-EXP-ALL-001')
  const savedCheckpoints = new Set(summary?.evidence_snapshots.map((item) => item.checkpoint_id) ?? [])
  const resultSaved = savedCheckpoints.has('CONTROLLED_RESULT')
  const assessment = projection.restoration_assessments.at(-1)
  const selectedSection = controlledText(summary, 'selected_fault_section_id') ?? projection.run.fault_section_id
  const affectedFeeder = controlledText(summary, 'affected_feeder_id') ?? projection.network_nodes.find((item) => item.configured.entity_id === selectedSection)?.configured.feeder_id ?? 'the affected feeder'
  const boundaries = controlledTextList(summary, 'incident_boundary_device_ids')
  const finalAffected = controlledNumber(summary, 'affected_customer_count') ?? projection.summary.affected_customer_count
  const alternateRestored = controlledNumber(summary, 'restored_customer_delta') ?? projection.summary.restored_customer_delta
  const proposedSections = controlledTextList(summary, 'proposed_section_ids')
  const alternateFeeder = controlledText(summary, 'alternate_feeder_id') ?? assessment?.candidate?.alternate_feeder_id ?? 'the alternate feeder'
  const loading = controlledNumber(summary, 'resulting_loading_percent') ?? (assessment?.calculation === null || assessment?.calculation === undefined ? null : Number(assessment.calculation.resulting_loading_percent))
  const outcome = controlledText(summary, 'restoration_outcome') ?? assessment?.outcome ?? 'NOT YET CHECKED'
  const feederCustomerTotal = projection.network_nodes
    .filter((item) => item.configured.entity_type === 'SECTION' && item.configured.feeder_id === affectedFeeder)
    .reduce((total, item) => total + (item.configured.customer_count ?? 0), 0)
  const beforeAlternateAffected = resultSaved ? finalAffected + alternateRestored : projection.summary.affected_customer_count
  const normalSupplyRestored = Math.max(0, feederCustomerTotal - beforeAlternateAffected)
  const stages: ValidationStage[] = [
    { checkpoint: 'N0', title: 'Starting network and selected fault', validation: 'The selected section is checked against the controlled network configuration before any simulated operation begins.', evidence: `${selectedSection} selected on ${affectedFeeder}; source configuration ${projection.run.configuration_id}.` },
    { checkpoint: 'N1', title: 'Fault impact and feeder trip', validation: 'Connectivity is recalculated after the simulated protection trip, then customer counts are summed only from sections that no longer have a source path.', evidence: resultSaved || projection.run.network_state_label !== 'N0' ? `${feederCustomerTotal} customers are recorded as initially affected on ${affectedFeeder}.` : 'The affected sections and customer total will be calculated after the simulated feeder trip.' },
    { checkpoint: 'N2', title: 'Fault isolation', validation: 'Every incident-boundary switch must be open, have acceptable signal quality, have a fresh timestamp, and leave no energised path to the fault.', evidence: boundaries.length === 0 ? 'Isolation evidence is included in the controlled result when the boundary proof is complete.' : `${boundaries.join(' and ')} are the saved incident boundaries.` },
    { checkpoint: 'N3', title: 'Normal-supply recovery', validation: 'The normal feeder breaker is reclosed only after isolation is proven; topology and customer impact are recalculated from the resulting switch positions.', evidence: resultSaved || ['N3', 'N4', 'N5'].includes(projection.run.network_state_label) ? `${normalSupplyRestored} customers were restored from the normal feeder; ${beforeAlternateAffected} remained affected before alternate supply.` : 'The revised customer impact will be calculated after safe normal-supply restoration.' },
    { checkpoint: 'N4', title: 'Alternate-supply decision', validation: 'The proposed path is checked for trustworthy telemetry, fault separation, radial operation and feeder capacity before any tie switch can close.', evidence: `${humanise(outcome)}${loading === null ? '' : ` at ${loading.toFixed(1)}% alternate-feeder loading`}${proposedSections.length === 0 ? '.' : ` for ${proposedSections.join(', ')} from ${alternateFeeder}.`}` },
    { checkpoint: 'N5', title: 'Final restored network', validation: 'After permitted switching, the application recalculates sources, feeder loading, radiality and remaining customer impact, then preserves the combined result.', evidence: resultSaved || projection.run.network_state_label === 'N5' ? `${alternateRestored} customers were restored from the alternate feeder; ${finalAffected} remain affected and the selected fault remains isolated.` : 'The final sources, loading and remaining customer impact will be shown after any permitted restoration is applied.' },
  ]
  const actions = projection.validation.actions.filter((item) => item.test_id === 'VT-EXP-ALL-001')

  return <div className="view-stack">
    <AssuranceValidationModel />
    <section className="panel" aria-labelledby="exploration-stage-validation-title">
      <div className="panel-heading"><div><span className="eyebrow">Operational assurance</span><h2 id="exploration-stage-validation-title">How each operating stage was checked</h2></div><span className="status-badge neutral">6 operating stages</span></div>
      <p>These are the live network, telemetry and safety checks used by the operating logic while this trial is running. They determine which actions can proceed; they are not the secondary validation verdict.</p>
      <StageValidationGrid stages={stages} currentCheckpoint={projection.run.network_state_label} savedCheckpoints={savedCheckpoints} exploration />
      <div className="assurance-conclusion"><strong>What this operating assurance demonstrates</strong><p>The selected fault trips its affected feeder, the fault can be isolated, healthy supply can be restored where the current network permits it, and every restoration action remains subject to telemetry, radiality and feeder-capacity checks.</p></div>
      <p className="traceability-pointer">The saved operating result becomes input to the separate <strong>system validation</strong> report below, where the behaviour of the operating logic is compared with the accepted case expectation.</p>
    </section>

    <section className="panel validation-progress" aria-labelledby="exploration-evidence-title">
      <div className="panel-heading"><div><span className="eyebrow">Trial system-validation report</span><h2 id="exploration-evidence-title">Validation of the operating logic for this case</h2></div><span className="status-badge exploratory">Separate trial record</span></div>
      <p>This secondary layer checks whether the operating mechanism produced the accepted case-specific result from the selected fault, configuration and telemetry. It is designed to reveal incorrect source relationships, isolation boundaries, customer calculations or restoration decisions. The result remains separate and is never counted as controlled validation evidence.</p>
      <div className="progress-grid validation-summary"><article><strong>{selectedSection}</strong><span>Selected fault section</span></article><article><strong>{summary?.evidence_snapshots.length ?? 0}</strong><span>Combined results saved</span></article><article><strong>{summary?.execution.verdict ?? 'Not assessed'}</strong><span>Validation result</span></article></div>
      <button type="button" className="secondary-action" onClick={() => onContinue('operational')}>Return to operations</button>
      {definition !== undefined && <details className="technical-details"><summary>Technical test traceability</summary><p>The exact controlled definition and source identities used for this trial remain available here for audit.</p><dl className="definition-grid"><div><dt>Controlled test</dt><dd>{definition.definition.test_id} · v{definition.definition.version}</dd></div><div><dt>Validation catalogue</dt><dd>v{definition.catalogue_version} · {definition.catalogue_sha256}</dd></div><div><dt>Definition fingerprint</dt><dd>{definition.definition_sha256}</dd></div><div><dt>Requirement references</dt><dd>{definition.definition.requirement_ids.join(', ')}</dd></div></dl></details>}
    </section>

    <ExplorationValidationProcedure projection={projection} definitions={definitions} summary={summary} actions={actions} busy={busy} onAction={onAction} />
  </div>
}

export function ValidationView({ projection, busy, onAction, onContinue }: { projection: WorkspaceProjection; busy: boolean; onAction: (action: ValidationWorkspaceAction) => void; onContinue: (view: 'operational' | 'restoration') => void }) {
  if (projection.run.mode === 'EXPLORATION') return <ExplorationValidation projection={projection} busy={busy} onAction={onAction} onContinue={onContinue} />

  const definition = projection.validation.definitions.find((item) => item.definition.test_id === 'VT-FML-N0-N5-001')
  const summary = projection.validation.run_executions.find((item) => item.execution.test_id === 'VT-FML-N0-N5-001')
  const relevantActions = projection.validation.actions.filter((item) => item.test_id === 'VT-FML-N0-N5-001')
  const startAction = relevantActions.find((item) => item.action_type === 'START_EXECUTION' && item.available)
  const captureAction = relevantActions.find((item) => item.action_type === 'CAPTURE_CHECKPOINT' && item.checkpoint_id === projection.run.network_state_label && item.available)
  const finaliseAction = relevantActions.find((item) => item.action_type === 'FINALISE_EXECUTION' && item.available)
  const savedCheckpoints = new Set(summary?.evidence_snapshots.map((item) => item.checkpoint_id) ?? [])
  const currentCheckpointCaptured = summary?.evidence_snapshots.some((evidence) => evidence.checkpoint_id === projection.run.network_state_label) === true
  const initialAffected = observedNumber(summary, 'N1', 'affected_customer_count')
  const upstreamAffected = observedNumber(summary, 'N3', 'affected_customer_count')
  const finalAffected = observedNumber(summary, 'N5', 'affected_customer_count')
  const finalRestored = observedNumber(summary, 'N5', 'restored_customer_delta')
  const assessment = projection.restoration_assessments.at(-1)
  const formalCriteriaCount = definition?.definition.determination_method?.criteria.length ?? 0
  const stages: ValidationStage[] = [
    { checkpoint: 'N0', title: 'Normal network baseline', validation: 'The starting switch positions, feeder sources, customer supply and controlled configuration are preserved before any fault is introduced.', evidence: 'Normal supply and zero active faults are compared with the approved starting state.' },
    { checkpoint: 'N1', title: 'Fault and feeder trip', validation: 'The protection operation is checked against the selected fault, then topology is recalculated to identify every section and customer that lost supply.', evidence: initialAffected === null ? 'The feeder-trip event and calculated outage are preserved.' : `${initialAffected} affected customers were preserved and compared with the approved outcome.` },
    { checkpoint: 'N2', title: 'Fault isolation', validation: 'Both incident-boundary switches must report open with acceptable quality and fresh timestamps, and the topology must show zero active source paths to the fault.', evidence: projection.isolation_proof === null ? 'Boundary positions, telemetry trust and source-path proof are preserved.' : `${projection.isolation_proof.all_boundaries_proven_open ? 'Every boundary is proven open' : 'Boundary proof is incomplete'}; ${projection.isolation_proof.zero_active_source_paths ? 'no energised path reaches the fault' : 'an active source path remains'}.` },
    { checkpoint: 'N3', title: 'Healthy upstream section restored', validation: 'The normal breaker reclose is allowed only after isolation; the resulting topology and outage total are recalculated to confirm supply did not cross the fault.', evidence: upstreamAffected === null ? 'The upstream restoration and resulting customer impact are preserved.' : `${upstreamAffected} customers remained affected after normal-supply recovery.` },
    { checkpoint: 'N4', title: 'Alternate supply assessed', validation: 'The candidate path is checked for fault separation, trustworthy telemetry, radial operation and feeder capacity before switching is permitted.', evidence: assessment === undefined ? 'The assessment outcome and every individual permissive are preserved.' : `${humanise(assessment.outcome)}${assessment.calculation === null ? '' : ` at ${Number(assessment.calculation.resulting_loading_percent).toFixed(1)}% feeder loading`}.` },
    { checkpoint: 'N5', title: 'Eligible healthy sections restored', validation: 'After the permitted tie operation, sources, radiality, feeder loading and customer impact are recalculated and compared with the approved final outcome.', evidence: finalAffected === null ? 'The final topology, restored customers and remaining outage are preserved.' : `${finalRestored ?? 0} customers restored in the final step; ${finalAffected} remained affected.` },
  ]

  return <div className="view-stack">
    <AssuranceValidationModel />
    <section className="panel" aria-labelledby="stage-validation-title">
      <div className="panel-heading"><div><span className="eyebrow">Operational assurance</span><h2 id="stage-validation-title">How each operating stage was checked</h2></div><p>Green stages have an immutable saved record; grey stages have not yet been reached.</p></div>
      <p>These checks belong to the operating mechanism itself. They use the current connectivity, switch positions, telemetry trust and capacity conditions to decide whether each simulated action can proceed safely.</p>
      <StageValidationGrid stages={stages} currentCheckpoint={projection.run.network_state_label} savedCheckpoints={savedCheckpoints} />
      <div className="assurance-conclusion"><strong>What this operating assurance confirms</strong><p>A fault trips the feeder, the fault can be isolated, healthy supply can be restored in stages, and the final network remains radial and within feeder capacity.</p></div>
      <p className="traceability-pointer">The saved operating states become input to the separate <strong>system validation</strong> report below, which tests whether this operating mechanism produced the accepted result.</p>
    </section>

    <section className="panel validation-progress" aria-labelledby="validation-progress-title">
      <div className="panel-heading"><div><span className="eyebrow">System-validation report</span><h2 id="validation-progress-title">Validation of the operating logic</h2></div><span className="status-badge formal">{savedCheckpoints.size} of 6 states saved</span></div>
      <p>This secondary layer tests the complete isolation-to-restoration mechanism against an accepted expected result. Its purpose is to detect whether a configuration error, telemetry-evidence problem, or defect in the topology, outage or restoration logic caused the operating mechanism to produce the wrong outcome.</p>
      <div className="progress-grid validation-summary"><article><strong>{checkpointLabel(projection.run.network_state_label)}</strong><span>Current scenario state</span></article><article><strong>{savedCheckpoints.size}</strong><span>States validated and saved</span></article><article><strong>{summary?.execution.verdict ?? 'Not assessed'}</strong><span>Overall validation result</span></article></div>
      <button type="button" className="secondary-action" onClick={() => onContinue('operational')}>Return to operations</button>
      {definition !== undefined && <details className="technical-details"><summary>Technical test traceability</summary><p>This section retains the exact identifiers and comparison definitions used to reproduce and audit the validation.</p><dl className="definition-grid"><div><dt>Test reference</dt><dd>{definition.definition.test_id} · v{definition.definition.version}</dd></div><div><dt>Evidence class</dt><dd>{definition.definition.evidence_class}</dd></div><div><dt>Validation catalogue</dt><dd>v{definition.catalogue_version} · {definition.catalogue_sha256}</dd></div><div><dt>Definition fingerprint</dt><dd>{definition.definition_sha256}</dd></div><div><dt>Requirement references</dt><dd>{definition.definition.requirement_ids.join(', ')}</dd></div><div><dt>Source references</dt><dd>{definition.definition.source_references.join(', ')}</dd></div></dl>{definition.definition.determination_method !== undefined && definition.definition.determination_method !== null && <><p><strong>Comparison method:</strong> {definition.definition.determination_method.method_id} · {definition.definition.determination_method.context_kind}</p><ul>{definition.definition.determination_method.criteria.map((criterion) => <li key={criterion.criterion_id}>{criterion.criterion_id} · {humanise(criterion.kind)}</li>)}</ul></>}</details>}
    </section>

    <section className="panel validation-procedure" aria-labelledby="formal-procedure-title">
      <div className="panel-heading"><div><span className="eyebrow">Validation procedure</span><h2 id="formal-procedure-title">How the validation result is produced</h2></div><span className={`status-badge ${summary?.execution.status === 'FINALISED' ? 'success' : 'neutral'}`}>{summary?.execution.status === 'FINALISED' ? 'Procedure complete' : 'Procedure in progress'}</span></div>
      <p>The validation verdict is not assigned from the final screen alone. It is produced from controlled entry conditions, six separately preserved network states and the accepted comparison method.</p>
      <div className="procedure-grid" aria-label="Controlled validation procedure">
        <article><span className="procedure-number">1</span><div><h3>Lock the validation basis</h3><p>The application version, network configuration, accepted test definition, catalogue and controlled scenario identity are bound before evidence is accepted.</p></div></article>
        <article><span className="procedure-number">2</span><div><h3>Preserve each network state</h3><p>Normal supply, fault impact, isolation, normal recovery, alternate-supply assessment and the final restored topology remain separate immutable snapshots.</p></div></article>
        <article><span className="procedure-number">3</span><div><h3>Evaluate controlled criteria</h3><p>{formalCriteriaCount > 0 ? `${formalCriteriaCount} accepted criteria trace expected and observed values back to their controlled source records.` : 'Accepted comparisons trace expected and observed values back to their controlled source records.'} Missing evidence cannot be converted into a PASS.</p></div></article>
        <article><span className="procedure-number">4</span><div><h3>Finalise an auditable result</h3><p>The verdict, evidence identities, source links and integrity fingerprints are finalised together before a downloadable evidence package can be created.</p></div></article>
      </div>
      <div className="validation-safeguard"><div><span className="eyebrow">Current procedure status</span><h3>{savedCheckpoints.size} of 6 required network states preserved</h3><p>{summary?.execution.verdict === null || summary === undefined ? 'The validation determination remains open until the required state evidence and controlled comparisons are complete.' : `The immutable finding chain produced ${summary.execution.verdict}; its source records remain available in the report traceability and evidence record.`}</p></div><span className={`status-badge ${summary?.execution.verdict === 'PASS' ? 'success' : 'neutral'}`}>{summary?.execution.verdict ?? 'Not yet determined'}</span></div>
    </section>

    <section className="panel" aria-labelledby="execution-title">
      <div className="panel-heading"><div><span className="eyebrow">Validation evidence record</span><h2 id="execution-title">Saved evidence for this walkthrough</h2></div><span className={`status-badge ${currentCheckpointCaptured ? 'success' : 'neutral'}`}>{summary?.execution.status === 'FINALISED' ? 'Complete' : summary?.execution.status ?? 'Preparing'}</span></div>
      {summary === undefined ? <><p className="empty-state">The evidence record has not been created yet.</p>{startAction !== undefined && <button type="button" className="primary-action" disabled={busy} onClick={() => onAction(startAction)}>Create evidence record</button>}</> : <>
        <p>{summary.evidence_snapshots.length === 0 ? 'No scenario states have been saved yet.' : `${summary.evidence_snapshots.length} scenario state${summary.evidence_snapshots.length === 1 ? '' : 's'} saved.`} {summary.execution.verdict === null ? <>The validation result remains <strong>not assessed</strong> until the approved comparison process is completed.</> : <>The approved comparison process is complete: <strong>{summary.execution.verdict}</strong>.</>}</p>
        {summary.evidence_snapshots.length > 0 && <div className="evidence-grid">{summary.evidence_snapshots.map((evidence) => <article key={evidence.evidence_snapshot_id}><div><strong>{checkpointLabel(evidence.checkpoint_id)}</strong><span className="status-badge success">Saved</span></div><p>{formatTime(evidence.scenario_time)}</p><small>Record {shortId(evidence.evidence_snapshot_id)}</small></article>)}</div>}
        <details className="technical-details"><summary>Evidence record identity</summary><dl className="identity-grid"><div><dt>Evidence record ID</dt><dd>{summary.execution.validation_execution_id}</dd></div><div><dt>Scenario run</dt><dd>{summary.execution.scenario_run_id}</dd></div><div><dt>Evidence class</dt><dd>{summary.execution.evidence_class}</dd></div><div><dt>Application version</dt><dd>{summary.execution.application_build_id}</dd></div><div><dt>Network version</dt><dd>{summary.execution.configuration_id}</dd></div><div><dt>Started</dt><dd>{formatTime(summary.execution.started_scenario_time)}</dd></div><div><dt>Validation result</dt><dd>{summary.execution.verdict ?? 'No PASS/FAIL has been created.'}</dd></div></dl></details>
      </>}
      {captureAction !== undefined && <div className="guided-continuation"><p><strong>{checkpointLabel(projection.run.network_state_label)}</strong> has not been saved.</p><button type="button" className="primary-action" disabled={busy} onClick={() => onAction(captureAction)}>Save this state now</button></div>}
      {finaliseAction !== undefined && <div className="guided-continuation"><p>All required states are present.</p><button type="button" className="primary-action" disabled={busy} onClick={() => onAction(finaliseAction)}>Complete evidence record</button></div>}
    </section>
  </div>
}
