import { useEffect, useState } from 'react'
import type { InvestigationStep, InvestigationWorkspace as InvestigationModel } from '../../api/contracts'
import type { WorkspaceApi } from '../../api/client'

type InvestigationPhase = { title: string; question: string; conclusion: string; steps: InvestigationStep[] }

function phases(workspace: InvestigationModel): InvestigationPhase[] {
  return [
    { title: 'Confirm the discrepancy', question: 'What did validation find?', conclusion: 'The feeder trip should affect 850 customers, but the v1.0 calculation reports only 400. The result is preserved as a genuine failure.', steps: workspace.steps.slice(0, 1) },
    { title: 'Rule out bad operating evidence', question: 'Were the alarm, telemetry and outage arithmetic trustworthy?', conclusion: 'The breaker indication is open, good and fresh. Topology and outage calculations consistently follow the data they received, so the mismatch is not caused by stale telemetry or arithmetic.', steps: workspace.steps.slice(1, 4) },
    { title: 'Trace the missing outage sections', question: 'Why did 450 customers disappear from the calculated outage?', conclusion: 'SEC-A3 and SEC-A4 incorrectly remain attributed to Riverbend Feeder through a path that crosses SW-A23. The same false path makes the model treat SW-A12 alone as the incident boundary, explaining both the incomplete isolation sequence and understated outage.', steps: workspace.steps.slice(4, 5) },
    { title: 'Determine the configuration fault', question: 'Which controlled source record created that path?', conclusion: 'GIS configuration v1.0 connects the SW-A23 edge to SEC-B3 instead of SEC-A2. Changing that one endpoint removes the false source path; the operating algorithms do not change.', steps: workspace.steps.slice(5, 7) },
  ]
}

function EvidencePhase({ phase, number }: { phase: InvestigationPhase; number: number }) {
  return <article className="panel investigation-phase">
    <div className="investigation-phase-heading"><span>{number}</span><div><small>{phase.question}</small><h3>{phase.title}</h3></div></div>
    <p className="phase-conclusion">{phase.conclusion}</p>
    <details className="technical-details"><summary>Review supporting evidence</summary>{phase.steps.map((step) => <section className="phase-source" key={step.step_id}><h4>{step.title}</h4><dl>{step.facts.map((fact) => <div key={`${step.step_id}-${fact.label}`}><dt>{fact.label}</dt><dd>{fact.value}</dd></div>)}</dl><details><summary>Source record identities</summary><ul>{step.source_record_references.map((reference) => <li key={reference}>{reference}</li>)}</ul></details></section>)}</details>
  </article>
}

export function InvestigationWorkspace({ api, failureExecutionId, actor, initial, onUpdate, onContinue }: { api: WorkspaceApi; failureExecutionId: string; actor: string; initial?: InvestigationModel | null; onUpdate: (workspace: InvestigationModel) => void; onContinue?: () => void }) {
  const [workspace, setWorkspace] = useState<InvestigationModel | null>(initial ?? null)
  const [revealed, setRevealed] = useState(1)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (initial !== undefined && initial !== null) { setWorkspace(initial); return }
    api.investigation(failureExecutionId).then(setWorkspace).catch((cause: unknown) => setError(cause instanceof Error ? cause.message : 'Unable to load investigation.'))
  }, [api, failureExecutionId, initial])

  async function mutate(operation: () => Promise<InvestigationModel>) {
    setBusy(true); setError(null)
    try { const next = await operation(); setWorkspace(next); onUpdate(next) }
    catch (cause) { setError(cause instanceof Error ? cause.message : 'Controlled investigation action failed.') }
    finally { setBusy(false) }
  }

  if (workspace === null) return <section className="panel"><h2>Investigation</h2><p>{error ?? 'Loading preserved evidence…'}</p></section>
  const action = (type: string) => workspace.actions.find((item) => item.action_type === type)!
  const evidencePhases = phases(workspace)
  const allReviewed = revealed >= evidencePhases.length
  const repeat = workspace.direct_repeat?.execution
  const difference = workspace.configuration_comparison.differences[0]

  return <div className="investigation-layout polished-investigation">
    <section className="panel investigation-lead">
      <div className="panel-heading"><div><span className="eyebrow">Consequence-to-source investigation</span><h2>Why did a safe-looking run produce the wrong result?</h2></div><span className="status-badge failure">Validation failed</span></div>
      <p>The operating sequence is not being rerun or rewritten here. This page follows the preserved 450-customer mismatch backwards through the evidence until the hidden GIS source error is identified.</p>
      <div className="investigation-summary"><article><span>Accepted impact</span><strong>850 customers</strong></article><article><span>v1.0 calculated impact</span><strong>400 customers</strong></article><article><span>Difference to explain</span><strong>450 customers</strong></article></div>
    </section>

    <section className="investigation-progress" aria-label="Investigation sequence">{evidencePhases.slice(0, revealed).map((phase, index) => <EvidencePhase key={phase.title} phase={phase} number={index + 1} />)}</section>
    {!allReviewed && <div className="investigation-next"><p><strong>Next:</strong> {evidencePhases[revealed].question}</p><button type="button" className="primary-action defect-action" onClick={() => setRevealed((current) => current + 1)}>Continue investigation</button></div>}

    {allReviewed && <section className="panel root-cause-determination" aria-labelledby="root-cause-title">
      <div className="panel-heading"><div><span className="eyebrow">Engineering determination</span><h2 id="root-cause-title">The fault is in one GIS connectivity endpoint</h2></div><span className="status-badge warning">Cause identified</span></div>
      <div className="connection-correction"><article><span>v1.0 · incorrect</span><strong>SW-A23 connected to SEC-B3</strong><p>This creates a false alternate source path and makes SEC-A3 and SEC-A4 appear energised after BRK-A trips.</p></article><div aria-hidden="true">→</div><article><span>v1.1 · corrected</span><strong>SW-A23 connected to SEC-A2</strong><p>The false path disappears and the calculated outage returns to the accepted 850 customers.</p></article></div>
      <p className="callout warning"><strong>Everything can look internally consistent and still be wrong.</strong> The telemetry was trustworthy and the algorithms followed their inputs correctly. The hidden topology relationship in the authoritative GIS package made the coherent-looking answer incorrect.</p>
      <details className="technical-details"><summary>Exact controlled package difference and integrity records</summary><dl className="comparison-grid"><div><dt>Changed field</dt><dd>{difference?.path}</dd></div><div><dt>v1.0 value</dt><dd>{difference?.before}</dd></div><div><dt>v1.1 value</dt><dd>{difference?.after}</dd></div></dl><p>Assets, loads, customer mappings, switch states, schema and application algorithms are unchanged.</p></details>
    </section>}

    <section className="panel correction-workflow" aria-labelledby="correction-title"><div className="panel-heading"><div><span className="eyebrow">Controlled disposition and correction</span><h2 id="correction-title">Preserve the finding, select the correction, then test it</h2></div></div>
      <div className="correction-steps">
        <article className={workspace.defect_record === null ? 'current' : 'complete'}><span>1</span><div><h3>Record the engineering defect</h3><p>Bind the identified GIS cause to the preserved validation failure without replacing either record.</p>{workspace.defect_record === null ? <button type="button" className="primary-action defect-action" disabled={!allReviewed || busy || !action('RECORD_DEFECT').available} onClick={() => mutate(() => api.recordDefect(failureExecutionId, actor, workspace.steps.map((step) => step.step_id)))}>Confirm and record the identified fault</button> : <strong className="completed-action">Recorded as DEF-001</strong>}</div></article>
        <article className={workspace.correction_record === null ? workspace.defect_record === null ? '' : 'current' : 'complete'}><span>2</span><div><h3>Select the corrected GIS record</h3><p>Use immutable configuration v1.1, where the endpoint is corrected. No live package editing occurs in this interface.</p>{workspace.correction_record === null ? <button type="button" className="primary-action defect-action" disabled={busy || !action('RECORD_CORRECTION').available} onClick={() => mutate(() => api.recordCorrection(failureExecutionId, actor))}>Select corrected GIS configuration v1.1</button> : <strong className="completed-action">Correction COR-001 recorded</strong>}</div></article>
        <article className={repeat === undefined ? workspace.correction_record === null ? '' : 'current' : 'complete'}><span>3</span><div><h3>Repeat the failed post-trip check</h3><p>Run the same focused comparison with the same application build and corrected configuration.</p>{repeat === undefined ? <button type="button" className="primary-action defect-action" disabled={busy || !action('RUN_DIRECT_REPEAT').available} onClick={() => mutate(() => api.runDirectRepeat(failureExecutionId, actor))}>Run focused corrected check</button> : <strong className="completed-action">PASS · 850 affected customers</strong>}</div></article>
      </div>
      {repeat !== undefined && <div className="guided-continuation corrected-continuation"><div><strong>The focused correction check passed</strong><p>Continue to repeat the entire isolation-to-restoration sequence and prove both operational assurance and system validation.</p></div><button type="button" className="primary-action defect-action" onClick={onContinue}>Continue to corrected full run</button></div>}
      {workspace.same_build_proven && <p className="callout success" data-testid="same-build-proof">The v1.0 failure and v1.1 focused repeat used the same application version; only the network configuration changed.</p>}
      {error !== null && <p role="alert" className="global-error">{error}</p>}
    </section>
  </div>
}
