import type { RestorationAssessment, WorkspaceAction, WorkspaceProjection } from '../../api/contracts'
import { formatAge, formatKw, formatTime, humanise, shortId } from '../../components/format'

const outcomeMeaning: Record<RestorationAssessment['outcome'], string> = {
  NO_CANDIDATE: 'No healthy de-energised group and valid alternate path were identified.',
  BLOCKED: 'Required operational evidence is missing, stale, invalid or otherwise untrustworthy. This is not an engineering rejection.',
  REJECTED: 'The evidence is sufficient, but one or more defined engineering criteria failed.',
  PERMITTED: 'A candidate exists and every applicable evidence and engineering permissive passed.',
}

export function RestorationView({
  projection,
  busyActionId,
  onExecute,
}: {
  projection: WorkspaceProjection
  busyActionId: string | null
  onExecute: (action: WorkspaceAction) => void
}) {
  const assessment = projection.restoration_assessments.at(-1)
  const invalidation = assessment === undefined ? undefined : projection.restoration_invalidations.find((item) => item.assessment_id === assessment.assessment_id)
  const assessAction = projection.allowed_actions.find((item) => item.command_type === 'ASSESS_RESTORATION')
  const executeAction = projection.allowed_actions.find((item) => item.command_type === 'EXECUTE_RESTORATION')
  if (assessment === undefined) {
    return <section className="panel empty-assessment" aria-labelledby="restoration-title">
      <span className="eyebrow">ADMS Restoration Assessment</span><h2 id="restoration-title">Not assessed</h2>
      <p>No assessment record exists. Candidate discovery, permissives and calculations will be produced by the backend only when the current workflow makes assessment available.</p>
      {assessAction !== undefined && <button type="button" disabled={!assessAction.available || busyActionId !== null} onClick={() => onExecute(assessAction)}>Assess alternate restoration</button>}
      {assessAction !== undefined && !assessAction.available && <p className="reason-box">{assessAction.reason}</p>}
    </section>
  }
  return (
    <div className="view-stack">
      <section className={`panel outcome-card outcome-${assessment.outcome.toLowerCase()}`} aria-labelledby="restoration-title">
        <div className="panel-heading"><div><span className="eyebrow">Operational assessment outcome</span><h2 id="restoration-title">{humanise(assessment.outcome)}</h2></div><span className={`status-badge outcome-${assessment.outcome.toLowerCase()}`}>{assessment.outcome}</span></div>
        <p className="outcome-meaning">{outcomeMeaning[assessment.outcome]}</p>
        <dl className="identity-grid"><div><dt>Assessment ID</dt><dd>{assessment.assessment_id}</dd></div><div><dt>Sequence</dt><dd>{assessment.assessment_sequence}</dd></div><div><dt>State revision binding</dt><dd>{assessment.state_revision}</dd></div><div><dt>Scenario time</dt><dd>{formatTime(assessment.scenario_time)}</dd></div></dl>
        {invalidation !== undefined && <div className="callout danger"><strong>INVALIDATED:</strong> {humanise(invalidation.reason_code)} at revision {invalidation.superseding_state_revision}. Event {invalidation.event_id}. The preserved assessment cannot authorise execution.</div>}
      </section>
      <section className="panel" aria-labelledby="candidate-title">
        <div className="panel-heading"><div><span className="eyebrow">Configuration-driven candidate</span><h2 id="candidate-title">Candidate and path</h2></div></div>
        {assessment.candidate === null ? <p className="empty-state">No candidate record exists for this topology.</p> : <div className="candidate-grid">
          <dl><div><dt>Candidate ID</dt><dd>{assessment.candidate.candidate_id}</dd></div><div><dt>Affected feeder</dt><dd>{assessment.candidate.affected_feeder_id}</dd></div><div><dt>Alternate feeder/source</dt><dd>{assessment.candidate.alternate_feeder_id} / {assessment.candidate.alternate_source_id}</dd></div><div><dt>Tie action</dt><dd>{assessment.candidate.tie_device_id} → {assessment.candidate.requested_tie_state}</dd></div></dl>
          <dl><div><dt>Proposed sections</dt><dd>{assessment.candidate.proposed_section_ids.join(', ')}</dd></div><div><dt>Proposed path edges</dt><dd>{assessment.candidate.proposed_path_edge_ids.join(' → ')}</dd></div><div><dt>Transferable load</dt><dd>{formatKw(assessment.candidate.transferable_load_kw)}</dd></div><div><dt>Proposed restored customers</dt><dd>{assessment.candidate.proposed_restored_customer_count}</dd></div></dl>
        </div>}
      </section>
      <section className="panel" aria-labelledby="permissive-title">
        <div className="panel-heading"><div><span className="eyebrow">Engineering decision trace</span><h2 id="permissive-title">Permissives and reasons</h2></div></div>
        <div className="permissive-grid">{assessment.permissives.map((item) => <article className={`permissive-${item.status.toLowerCase()}`} key={item.criterion}><span className="status-badge">{item.status}</span><h3>{humanise(item.criterion)}</h3><p>{item.reason_codes.map(humanise).join(' · ') || 'No deficiency recorded'}</p><small>Evidence: {item.evidence_point_ids.join(', ') || 'Derived topology/configuration records'}</small></article>)}</div>
      </section>
      <section className="panel" aria-labelledby="calculation-title">
        <div className="panel-heading"><div><span className="eyebrow">Capacity calculation</span><h2 id="calculation-title">Configured capacity and derived supplied load</h2></div></div>
        {assessment.calculation === null ? <div className="callout warning"><strong>No calculation presented.</strong> Current feeder load could not be defensibly attributed; zero has not been fabricated.</div> : <div className="calculation-trace">
          <div><span>Existing derived supplied load</span><strong>{formatKw(assessment.calculation.existing_supplied_load_kw)}</strong></div><span>+</span><div><span>Transferable load</span><strong>{formatKw(assessment.calculation.transferable_load_kw)}</strong></div><span>=</span><div><span>Resulting load</span><strong>{formatKw(assessment.calculation.resulting_load_kw)}</strong></div><span>of</span><div><span>Configured capacity</span><strong>{formatKw(assessment.calculation.feeder_capacity_kw)}</strong></div><div className="calculation-result"><span>Derived loading</span><strong>{Number(assessment.calculation.resulting_loading_percent).toFixed(1)}%</strong></div>
        </div>}
      </section>
      <section className="panel" aria-labelledby="assessment-evidence-title">
        <div className="panel-heading"><div><span className="eyebrow">Bound observed evidence</span><h2 id="assessment-evidence-title">Required telemetry snapshot</h2></div><p>Snapshot hash {shortId(assessment.telemetry_snapshot_sha256)}…</p></div>
        <div className="table-scroll"><table><thead><tr><th>Point</th><th>Value</th><th>Quality</th><th>Age</th><th>Freshness</th><th>Validity / reasons</th></tr></thead><tbody>{assessment.telemetry_evidence.map((row) => <tr key={row.point_id}><th scope="row">{row.point_id}</th><td>{row.value}</td><td>{row.quality}</td><td>{formatAge(row.age_ms)}</td><td>{row.freshness}</td><td>{row.overall_valid ? 'VALID' : row.reason_codes.map(humanise).join(' · ')}</td></tr>)}</tbody></table></div>
      </section>
      <section className="panel execution-panel"><span className="eyebrow">Backend action binding</span><h2>Simulated execution</h2>
        {executeAction !== undefined && <><button type="button" disabled={!executeAction.available || busyActionId !== null} onClick={() => onExecute(executeAction)}>Execute permitted restoration</button><p className="reason-box">{executeAction.reason}</p></>}
      </section>
    </div>
  )
}
