import { useEffect, useState } from 'react'
import type { InvestigationWorkspace as InvestigationModel } from '../../api/contracts'
import type { WorkspaceApi } from '../../api/client'
import { shortId } from '../../components/format'

export function InvestigationWorkspace({ api, failureExecutionId, actor, initial, onUpdate }: { api: WorkspaceApi; failureExecutionId: string; actor: string; initial?: InvestigationModel | null; onUpdate: (workspace: InvestigationModel) => void }) {
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
  const allReviewed = revealed >= workspace.steps.length
  const repeat = workspace.direct_repeat?.execution
  const regression = workspace.regression

  return <div className="investigation-layout">
    <section className="panel investigation-lead">
      <span className="eyebrow">Consequence-to-source review</span><h2>DEF-001 controlled investigation</h2>
      <p>{workspace.conceptual_boundary_notice}</p>
      <dl className="summary-grid"><div><dt>Original execution</dt><dd>{shortId(workspace.original_failure.execution.validation_execution_id)}…</dd></div><div><dt>Configuration</dt><dd>v{workspace.original_failure.execution.configuration_version}</dd></div><div><dt>Source catalogue</dt><dd>v{workspace.original_failure.execution.catalogue_version} · {workspace.original_failure.execution.catalogue_sha256}</dd></div><div><dt>Observed consequence</dt><dd>{String(workspace.original_failure.execution.observed_result?.affected_customer_count)} affected</dd></div><div><dt>Validation verdict</dt><dd className="status-fail">{workspace.original_failure.execution.verdict}</dd></div></dl>
    </section>

    <section className="investigation-steps" aria-label="Investigation evidence sequence">
      {workspace.steps.slice(0, revealed).map((step) => <article className="panel investigation-step" key={step.step_id}><span className="step-id">{step.step_id}</span><h3>{step.title}</h3><dl>{step.facts.map((fact) => <div key={`${step.step_id}-${fact.label}`}><dt>{fact.label}</dt><dd>{fact.value}</dd></div>)}</dl><details><summary>Source record references</summary><ul>{step.source_record_references.map((reference) => <li key={reference}>{reference}</li>)}</ul></details></article>)}
    </section>
    {!allReviewed && <button type="button" className="secondary-action" onClick={() => setRevealed((current) => current + 1)}>Review next evidence step</button>}

    {revealed >= 6 && <section className="panel"><span className="eyebrow">Read-only package comparison</span><h2>Configured difference → topology consequence</h2>{workspace.configuration_comparison.differences.map((difference) => <dl className="comparison-grid" key={difference.path}><div><dt>Field</dt><dd>{difference.path}</dd></div><div><dt>v1.0 defective</dt><dd>{difference.before}</dd></div><div><dt>v1.1 corrected</dt><dd>{difference.after}</dd></div></dl>)}<p>No endpoint is editable. Both package identities and hashes remain preserved.</p></section>}

    <section className="panel"><span className="eyebrow">Engineering records</span><h2>Failure → defect → correction → repeat → regression</h2>
      {workspace.defect_record === null ? <button type="button" className="primary-action" disabled={!allReviewed || busy || !action('RECORD_DEFECT').available} onClick={() => mutate(() => api.recordDefect(failureExecutionId, actor, workspace.steps.map((step) => step.step_id)))}>Record DEF-001 after evidence review</button> : <div className="record-card"><strong>{workspace.defect_record.defect_id}</strong><p>{workspace.defect_record.root_cause}</p><small>Immutable record {workspace.defect_record.defect_record_id}</small></div>}
      {workspace.correction_record === null ? <button type="button" disabled={busy || !action('RECORD_CORRECTION').available} onClick={() => mutate(() => api.recordCorrection(failureExecutionId, actor))}>Record controlled v1.1 selection</button> : <div className="record-card"><strong>{workspace.correction_record.correction_id}</strong><p>{workspace.correction_record.engineering_effect}</p><small>Immutable record {workspace.correction_record.correction_record_id}</small></div>}
      {repeat === undefined ? <button type="button" disabled={busy || !action('RUN_DIRECT_REPEAT').available} onClick={() => mutate(() => api.runDirectRepeat(failureExecutionId, actor))}>Run same-build v1.1 direct repeat</button> : <div className="record-card"><strong>Direct repeat {repeat.verdict}</strong><p>v{repeat.configuration_version} · {String(repeat.observed_result?.affected_customer_count)} affected · build {shortId(repeat.application_build_id)}…</p><small>Execution {repeat.validation_execution_id}</small></div>}
      {regression === null ? <button type="button" disabled={busy || !action('RUN_REGRESSION').available} onClick={() => mutate(() => api.runRegression(failureExecutionId, actor))}>Run corrected full N0–N5 regression</button> : <div className="record-card"><strong>Corrected N0–N5 evidence preserved</strong><p>{regression.evidence_snapshots.length} immutable checkpoints · formal verdict NOT DETERMINED under the accepted I5 comparison boundary.</p><small>Execution {regression.execution.validation_execution_id}</small></div>}
      {workspace.same_build_proven && <p className="callout success" data-testid="same-build-proof">{regression === null ? 'Same backend-controlled application build proven across v1.0 failure and v1.1 direct repeat.' : 'Same backend-controlled application build proven across v1.0 failure, v1.1 direct repeat and corrected regression.'}</p>}
      {error !== null && <p role="alert" className="global-error">{error}</p>}
    </section>
  </div>
}
