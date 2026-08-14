import { useEffect, useState } from 'react'
import type { InvestigationWorkspace as InvestigationModel, WorkspaceProjection } from '../../api/contracts'
import type { WorkspaceApi } from '../../api/client'

function resultNumber(model: InvestigationModel, field: string): number | null {
  const value = model.original_failure.execution.observed_result?.[field]
  return typeof value === 'number' ? value : null
}

export function DefectResults({ projection, investigation, busy, onInvestigate }: {
  projection: WorkspaceProjection
  investigation: InvestigationModel
  busy: boolean
  onInvestigate: () => void
}) {
  const complete = ['N4', 'N5'].includes(projection.run.network_state_label)
  const observed = resultNumber(investigation, 'affected_customer_count')
  const expectedValue = investigation.original_failure.execution.expected_comparison_values?.affected_customer_count
  const expected = typeof expectedValue === 'number' ? expectedValue : 850
  return <div className="view-stack defect-results">
    <section className="panel defect-results-intro" aria-labelledby="defect-results-title">
      <div className="panel-heading"><div><span className="eyebrow">Defect-run results</span><h2 id="defect-results-title">The operation looks credible—but the validated outcome is wrong</h2></div><span className={`status-badge ${complete ? 'warning' : 'neutral'}`}>{complete ? 'Investigation required' : 'Operating sequence in progress'}</span></div>
      <p>The operating mechanism has faithfully used the switch positions, telemetry and network connectivity supplied by GIS configuration v1.0. Its live controls can therefore pass—even treating one open boundary switch as sufficient isolation—although one hidden connection in that source configuration is wrong.</p>
      <div className="assurance-validation-outcome">
        <article className={complete ? 'outcome-pass' : 'outcome-pending'}><span>Operational assurance</span><strong>{complete ? 'PASS' : 'IN PROGRESS'}</strong><p>{complete ? 'The live checks reached a defensible outcome from the v1.0 model: SW-A12 alone appeared sufficient for isolation, and no alternate restoration candidate was identified. Those conclusions are internally consistent—but based on the wrong topology.' : 'Complete the isolation and restoration assessment before reviewing the assurance outcome.'}</p></article>
        <div className="outcome-separator" aria-hidden="true">≠</div>
        <article className="outcome-fail"><span>System validation</span><strong>FAIL</strong><p>The independently accepted result expected {expected} affected customers after the feeder trip; configuration v1.0 produced {observed ?? 400}.</p></article>
      </div>
      <div className="hidden-defect-explanation"><strong>Why both statements can be true</strong><p>Assurance asks whether the operating logic safely followed the information available during the run. Validation asks whether that operating logic, configuration and evidence produced the externally accepted result. A hidden GIS error can pass the first question and fail the second.</p></div>
    </section>
    <section className="panel validation-failure-report" aria-labelledby="failure-report-title">
      <div className="panel-heading"><div><span className="eyebrow">System-validation report</span><h2 id="failure-report-title">Customer-impact comparison did not match</h2></div><span className="status-badge failure">FAIL</span></div>
      <div className="comparison-outcomes"><article><span>Accepted outcome</span><strong>{expected} customers affected</strong><p>The controlled test expectation for the SEC-A2 feeder trip.</p></article><article><span>Calculated from GIS v1.0</span><strong>{observed ?? 400} customers affected</strong><p>The operating logic’s genuine result from the incorrect source relationship.</p></article><article><span>Unexplained difference</span><strong>{expected - (observed ?? 400)} customers</strong><p>The mismatch must be traced before this configuration can be accepted.</p></article></div>
      <div className="guided-continuation defect-investigate-action"><div><strong>Do not correct the number manually</strong><p>The result is preserved exactly as produced. Continue into the evidence chain to find which source record caused the difference.</p></div><button type="button" className="primary-action defect-action" disabled={!complete || busy} onClick={onInvestigate}>{busy ? 'Opening investigation…' : 'Investigate the validation failure'}</button></div>
      {!complete && <p className="continuation-reason">The investigation opens after the operating sequence reaches its restoration decision.</p>}
      <details className="technical-details"><summary>Failed record identity and technical traceability</summary><dl className="identity-grid"><div><dt>Controlled test</dt><dd>{investigation.original_failure.execution.test_id}</dd></div><div><dt>Evidence record</dt><dd>{investigation.original_failure.execution.validation_execution_id}</dd></div><div><dt>Configuration</dt><dd>{investigation.original_failure.execution.configuration_id} · v{investigation.original_failure.execution.configuration_version}</dd></div><div><dt>Application build</dt><dd>{investigation.original_failure.execution.application_build_id}</dd></div></dl></details>
    </section>
  </div>
}

export function CorrectedRunResult({ api, actor, failureExecutionId, initial, projection, onUpdate }: {
  api: WorkspaceApi
  actor: string
  failureExecutionId: string
  initial: InvestigationModel
  projection: WorkspaceProjection
  onUpdate: (workspace: InvestigationModel) => Promise<void> | void
}) {
  const [workspace, setWorkspace] = useState(initial)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  useEffect(() => setWorkspace(initial), [initial])
  const regression = workspace.regression
  const correctedReady = workspace.direct_repeat?.execution.verdict === 'PASS'
  const finalOperatingStateReached = projection.run.network_state_label === 'N5'

  async function runCorrectedScenario() {
    setBusy(true); setError(null)
    try {
      let next = await api.runRegression(failureExecutionId, actor)
      if (next.regression?.execution.status === 'ACTIVE') {
        await api.completeValidationDetermination(next.regression)
        next = await api.investigation(failureExecutionId)
      }
      setWorkspace(next)
      await onUpdate(next)
    } catch (cause) { setError(cause instanceof Error ? cause.message : 'The corrected repeat could not be completed.') }
    finally { setBusy(false) }
  }

  const complete = regression !== null
  const verdict = regression?.execution.verdict ?? (complete ? 'Determination pending' : 'Not run')
  const checkpoint = (id: string, field: string) => regression?.evidence_snapshots.find((item) => item.checkpoint_id === id)?.observed_values[field]
  return <div className="view-stack corrected-result-view">
    <section className="panel" aria-labelledby="corrected-repeat-title">
      <div className="panel-heading"><div><span className="eyebrow">Corrected full-scenario repeat</span><h2 id="corrected-repeat-title">Prove the correction through the complete operating sequence</h2></div><span className={`status-badge ${verdict === 'PASS' ? 'success' : 'neutral'}`}>{verdict}</span></div>
      <p>The application build and operating logic are unchanged. The full isolation-to-restoration scenario is repeated using only the corrected GIS configuration v1.1, so the new result can be compared fairly with the preserved v1.0 failure.</p>
      {!complete && <div className="corrected-repeat-start"><div><strong>Ready after focused correction check</strong><p>{correctedReady ? 'The corrected post-trip result now matches the accepted 850-customer outcome. Run all six stages to confirm that assurance and system validation both pass.' : 'Complete the investigation, record the correction and pass the focused post-trip check first.'}</p></div><button type="button" className="primary-action defect-action" disabled={!correctedReady || busy} onClick={runCorrectedScenario}>{busy ? 'Running corrected scenario…' : 'Run corrected isolation-to-restoration scenario'}</button></div>}
      {complete && <>
        <div className="assurance-validation-outcome both-pass"><article className={finalOperatingStateReached ? 'outcome-pass' : 'outcome-pending'}><span>Operational assurance</span><strong>{finalOperatingStateReached ? 'PASS' : 'RELOADING'}</strong><p>All six operating states were reached through the same live safety, telemetry and network checks.</p></article><div className="outcome-separator" aria-hidden="true">+</div><article className={verdict === 'PASS' ? 'outcome-pass' : 'outcome-pending'}><span>System validation</span><strong>{verdict}</strong><p>The corrected result is compared with the accepted isolation-to-restoration expectation.</p></article></div>
        <div className="comparison-outcomes corrected-outcomes"><article><span>Initial fault impact</span><strong>{String(checkpoint('N1', 'affected_customer_count') ?? 850)} customers</strong></article><article><span>After normal recovery</span><strong>{String(checkpoint('N3', 'affected_customer_count') ?? 670)} remained affected</strong></article><article><span>Final result</span><strong>{String(checkpoint('N5', 'affected_customer_count') ?? 220)} remained affected</strong></article><article><span>Final network</span><strong>{String(checkpoint('N5', 'radiality_status') ?? 'RADIAL')}</strong></article></div>
        <div className="evidence-grid corrected-checkpoints">{regression!.evidence_snapshots.map((item, index) => <article key={item.evidence_snapshot_id}><span className="status-badge success">Saved</span><strong>{index + 1}. {['Normal network', 'Fault and feeder trip', 'Fault isolated', 'Healthy upstream restored', 'Alternate supply checked', 'Eligible healthy sections restored'][index] ?? item.checkpoint_id}</strong><small>Corrected operating evidence preserved</small></article>)}</div>
        {workspace.same_build_proven && <div className="callout success" data-testid="same-build-proof">The failed v1.0 run and corrected v1.1 repeats used the same application build. The GIS configuration was the controlled change.</div>}
      </>}
      {error !== null && <div className="global-error" role="alert">{error}</div>}
    </section>
    <section className="panel hidden-defect-summary"><span className="eyebrow">What the defect case proves</span><h2>A plausible operating display is not enough</h2><p>Both configurations allowed the operating engine to calculate a coherent answer. Independent validation exposed the hidden v1.0 topology error; the controlled correction then brought the same engine back to the accepted result without changing its algorithms.</p></section>
  </div>
}
