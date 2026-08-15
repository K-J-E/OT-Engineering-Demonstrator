import type { RestorationAssessment, ValidationWorkspaceAction, WorkspaceAction, WorkspaceProjection } from '../../api/contracts'
import { formatAge, formatKw, formatTime, humanise, shortId } from '../../components/format'

const outcomeMeaning: Record<RestorationAssessment['outcome'], string> = {
  NO_CANDIDATE: 'No healthy de-energised group and valid alternate path were identified.',
  BLOCKED: 'The check cannot make a safe decision because required device information is missing, too old or untrustworthy.',
  REJECTED: 'The device information is sufficient, but one or more network or capacity checks did not pass.',
  PERMITTED: 'A restoration option exists and every required safety, network, telemetry and capacity check passed.',
}

export function RestorationView({
  projection,
  busyActionId,
  validationBusy,
  onExecute,
  onSaveEvidence,
  onViewEvidence,
  formalEvidenceRequired = true,
  reviewAvailableAtAssessment = false,
}: {
  projection: WorkspaceProjection
  busyActionId: string | null
  validationBusy: boolean
  onExecute: (action: WorkspaceAction) => void
  onSaveEvidence: (action: ValidationWorkspaceAction) => void
  onViewEvidence: () => void
  formalEvidenceRequired?: boolean
  reviewAvailableAtAssessment?: boolean
}) {
  const assessment = projection.restoration_assessments.at(-1)
  const invalidation = assessment === undefined ? undefined : projection.restoration_invalidations.find((item) => item.assessment_id === assessment.assessment_id)
  const assessAction = projection.allowed_actions.find((item) => item.command_type === 'ASSESS_RESTORATION')
  const executeAction = projection.allowed_actions.find((item) => item.command_type === 'EXECUTE_RESTORATION')
  const canExecuteRestoration = executeAction?.available === true
  const formalSummary = projection.validation.run_executions.find((item) => item.execution.test_id === 'VT-FML-N0-N5-001')
  const assessmentEvidenceSaved = formalSummary?.evidence_snapshots.some((item) => item.checkpoint_id === 'N4') === true
  const saveAssessmentAction = projection.validation.actions.find((item) => item.test_id === 'VT-FML-N0-N5-001' && item.action_type === 'CAPTURE_CHECKPOINT' && item.checkpoint_id === 'N4')
  if (assessment === undefined) {
    return <section className="panel empty-assessment" aria-labelledby="restoration-title">
      <span className="eyebrow">Alternate-supply review</span><h2 id="restoration-title">Check whether healthy de-energised sections can be restored</h2>
      <p>This check finds healthy sections that remain without supply, traces a path from the alternate feeder, verifies that the network stays radial, checks the required telemetry, and confirms that the alternate feeder has sufficient spare capacity.</p>
      <p className="reason-box">No suitable candidate path, restoration permitted, restoration rejected and restoration blocked are all possible correct outcomes.</p>
      {assessAction !== undefined && <button type="button" disabled={!assessAction.available || busyActionId !== null} onClick={() => onExecute(assessAction)}>Run alternate-supply check</button>}
      {assessAction !== undefined && !assessAction.available && <p className="reason-box">First isolate the fault and restore the healthy upstream section from its normal feeder.</p>}
    </section>
  }
  return (
    <div className="view-stack">
      <section className={`panel outcome-card outcome-${assessment.outcome.toLowerCase()}`} aria-labelledby="restoration-title">
        <div className="panel-heading"><div><span className="eyebrow">Alternate-supply decision</span><h2 id="restoration-title">{humanise(assessment.outcome)}</h2></div><span className={`status-badge outcome-${assessment.outcome.toLowerCase()}`}>{assessment.outcome}</span></div>
        <p className="outcome-meaning">{outcomeMeaning[assessment.outcome]} {assessment.outcome === 'NO_CANDIDATE' && projection.run.configuration_version === '1.0' && <span>(This is the correct restoration outcome based on the currently configured topology.)</span>}</p>
        <dl className="identity-grid"><div><dt>Assessed at</dt><dd>{formatTime(assessment.scenario_time)}</dd></div><div><dt>Network version</dt><dd>{projection.run.configuration_id} · v{projection.run.configuration_version}</dd></div></dl>
        <details className="technical-details"><summary>Technical traceability</summary><dl className="identity-grid"><div><dt>Run ID</dt><dd>{projection.run.scenario_run_id}</dd></div><div><dt>Assessment ID</dt><dd>{assessment.assessment_id}</dd></div><div><dt>Assessment sequence</dt><dd>{assessment.assessment_sequence}</dd></div><div><dt>State revision</dt><dd>{assessment.state_revision}</dd></div><div><dt>Telemetry record fingerprint</dt><dd>{assessment.telemetry_snapshot_sha256}</dd></div>{assessment.candidate !== null && <><div><dt>Candidate ID</dt><dd>{assessment.candidate.candidate_id}</dd></div><div><dt>Switching-path record IDs</dt><dd>{assessment.candidate.proposed_path_edge_ids.join(' → ')}</dd></div></>}</dl></details>
        {invalidation !== undefined && <div className="callout danger"><strong>INVALIDATED:</strong> {humanise(invalidation.reason_code)} at revision {invalidation.superseding_state_revision}. Event {invalidation.event_id}. The preserved assessment cannot authorise execution.</div>}
      </section>
      <section className="panel" aria-labelledby="candidate-title">
        <div className="panel-heading"><div><span className="eyebrow">Proposed restoration</span><h2 id="candidate-title">Sections, alternate feeder and switching path</h2></div></div>
        {assessment.candidate === null ? <p className="empty-state">No candidate record exists for this topology.</p> : <div className="candidate-grid">
          <dl><div><dt>Affected feeder</dt><dd>{assessment.candidate.affected_feeder_id}</dd></div><div><dt>Alternate feeder/source</dt><dd>{assessment.candidate.alternate_feeder_id} / {assessment.candidate.alternate_source_id}</dd></div><div><dt>Tie action</dt><dd>{assessment.candidate.tie_device_id} → {assessment.candidate.requested_tie_state}</dd></div></dl>
          <dl><div><dt>Proposed sections</dt><dd>{assessment.candidate.proposed_section_ids.join(', ')}</dd></div><div><dt>Transferable load</dt><dd>{formatKw(assessment.candidate.transferable_load_kw)}</dd></div><div><dt>Proposed restored customers</dt><dd>{assessment.candidate.proposed_restored_customer_count}</dd></div></dl>
        </div>}
      </section>
      <section className="panel" aria-labelledby="permissive-title">
        <div className="panel-heading"><div><span className="eyebrow">Safety and network checks</span><h2 id="permissive-title">Why this restoration is permitted, rejected or blocked</h2></div></div>
        {assessment.permissives.length === 0
          ? <p className="empty-state">No candidate path was available, so no candidate-specific safety, switching or capacity checks were required. The assessment stopped at the topology search and did not authorise an operation.</p>
          : <div className="permissive-grid">{assessment.permissives.map((item) => <article className={`permissive-${item.status.toLowerCase()}`} key={item.criterion}><span className="status-badge">{item.status}</span><h3>{humanise(item.criterion)}</h3><p>{item.reason_codes.map(humanise).join(' · ') || 'No deficiency recorded'}</p><small>Evidence: {item.evidence_point_ids.join(', ') || 'Derived topology/configuration records'}</small></article>)}</div>}
      </section>
      <section className="panel" aria-labelledby="calculation-title">
        <div className="panel-heading"><div><span className="eyebrow">Feeder capacity check</span><h2 id="calculation-title">Present load plus the proposed transferred load</h2></div></div>
        {assessment.calculation === null ? <div className="callout warning"><strong>No calculation presented.</strong> Current feeder load could not be defensibly attributed; zero has not been fabricated.</div> : <div className="calculation-trace">
          <div><span>Load currently supplied</span><strong>{formatKw(assessment.calculation.existing_supplied_load_kw)}</strong></div><span>+</span><div><span>Load proposed for transfer</span><strong>{formatKw(assessment.calculation.transferable_load_kw)}</strong></div><span>=</span><div><span>Load after restoration</span><strong>{formatKw(assessment.calculation.resulting_load_kw)}</strong></div><span>of</span><div><span>Feeder rated capacity</span><strong>{formatKw(assessment.calculation.feeder_capacity_kw)}</strong></div><div className="calculation-result"><span>Resulting feeder loading</span><strong>{Number(assessment.calculation.resulting_loading_percent).toFixed(1)}%</strong></div>
        </div>}
      </section>
      <section className="panel" aria-labelledby="assessment-evidence-title">
        <div className="panel-heading"><div><span className="eyebrow">Telemetry used for this decision</span><h2 id="assessment-evidence-title">Device values, quality and timestamp age</h2></div><p>Saved record {shortId(assessment.telemetry_snapshot_sha256)}…</p></div>
        <div className="table-scroll"><table><thead><tr><th>Point</th><th>Value</th><th>Quality</th><th>Age</th><th>Freshness</th><th>Validity / reasons</th></tr></thead><tbody>{assessment.telemetry_evidence.map((row) => <tr key={row.point_id}><th scope="row">{row.point_id}</th><td>{row.value}</td><td>{row.quality}</td><td>{formatAge(row.age_ms)}</td><td>{row.freshness}</td><td>{row.overall_valid ? 'VALID' : row.reason_codes.map(humanise).join(' · ')}</td></tr>)}</tbody></table></div>
      </section>
      <section className="panel execution-panel"><span className="eyebrow">Reviewer decision</span><h2>{projection.run.network_state_label === 'N5' ? 'Restoration completed' : canExecuteRestoration ? 'Apply the permitted restoration' : 'No alternate restoration action is available'}</h2>
        {formalEvidenceRequired && projection.run.mode === 'FORMAL' && projection.run.network_state_label === 'N4' && !assessmentEvidenceSaved && <><p>The assessment and its supporting telemetry are being saved automatically before restoration can proceed.</p><button type="button" className="primary-action" disabled={validationBusy || busyActionId !== null || saveAssessmentAction?.available !== true} onClick={() => saveAssessmentAction !== undefined && onSaveEvidence(saveAssessmentAction)}>{validationBusy || busyActionId !== null ? 'Preparing restoration action…' : 'Retry saving assessment evidence'}</button>{saveAssessmentAction !== undefined && !saveAssessmentAction.available && <p className="reason-box">{saveAssessmentAction.reason}</p>}</>}
        {(!formalEvidenceRequired || projection.run.mode !== 'FORMAL' || assessmentEvidenceSaved) && projection.run.network_state_label !== 'N5' && canExecuteRestoration && executeAction !== undefined && <><p>{assessmentEvidenceSaved ? 'Assessment evidence saved. The permitted switching action is ready.' : 'The permitted switching action is ready.'}</p><button type="button" className="primary-action" disabled={busyActionId !== null} onClick={() => onExecute(executeAction)}>Apply alternate supply restoration</button><p className="reason-box">This closes {assessment.candidate?.tie_device_id ?? 'the tie switch'} and restores only the eligible healthy sections listed above.</p></>}
        {projection.run.network_state_label === 'N4' && !canExecuteRestoration && <><p>The assessment produced <strong>{humanise(assessment.outcome)}</strong>. No alternate-supply switching action has been authorised.</p>{reviewAvailableAtAssessment && <button type="button" className="primary-action" onClick={onViewEvidence}>Review assurance and validation results</button>}</>}
        {projection.run.network_state_label === 'N5' && <><p>The eligible healthy sections are now supplied from the alternate feeder and the final state has been saved automatically.</p><button type="button" className="primary-action" disabled={busyActionId !== null || validationBusy} onClick={onViewEvidence}>{busyActionId !== null ? 'Completing evidence record…' : 'Review assurance and validation results'}</button></>}
      </section>
    </div>
  )
}
