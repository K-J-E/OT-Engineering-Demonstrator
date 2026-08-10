import type { ValidationWorkspaceAction, WorkspaceProjection } from '../../api/contracts'
import { formatTime, humanise, shortId } from '../../components/format'

const validationLabels: Record<ValidationWorkspaceAction['action_type'], string> = {
  START_EXECUTION: 'Start formal execution',
  CAPTURE_CHECKPOINT: 'Capture current checkpoint',
  FINALISE_EXECUTION: 'Finalise execution',
}

export function ValidationView({ projection, busy, onAction }: { projection: WorkspaceProjection; busy: boolean; onAction: (action: ValidationWorkspaceAction) => void }) {
  const definition = projection.validation.definitions.find((item) => item.definition.test_id === 'VT-FML-N0-N5-001')
  const summary = projection.validation.run_executions.find((item) => item.execution.test_id === 'VT-FML-N0-N5-001')
  const progress = projection.validation.progress
  return <div className="view-stack">
    <section className="panel validation-progress" aria-labelledby="validation-progress-title">
      <div className="panel-heading"><div><span className="eyebrow">Backend-assembled catalogue status</span><h2 id="validation-progress-title">Formal validation progress</h2></div><span className="status-badge formal">FORMAL</span></div>
      <div className="callout warning"><strong>Definitions are not executions.</strong> An accepted definition with no execution is not PASS, and operational BLOCKED/REJECTED is separate from validation determination.</div>
      <div className="progress-grid"><article><strong>{progress.definition_count}</strong><span>Controlled definitions</span></article><article><strong>{progress.definitions_without_execution_count}</strong><span>Without execution</span></article><article><strong>{progress.execution_count}</strong><span>Executions started</span></article><article><strong>{progress.finalised_execution_count}</strong><span>Finalised</span></article><article><strong>{progress.pass_count}</strong><span>PASS</span></article><article><strong>{progress.fail_count}</strong><span>FAIL</span></article></div>
    </section>
    {definition !== undefined && <section className="panel" aria-labelledby="definition-title">
      <div className="panel-heading"><div><span className="eyebrow">Read-only accepted definition</span><h2 id="definition-title">{definition.definition.test_id} · {definition.definition.title}</h2></div><span className="status-badge neutral">v{definition.definition.version}</span></div>
      <dl className="definition-grid"><div><dt>Objective</dt><dd>{definition.definition.objective}</dd></div><div><dt>Method</dt><dd>{definition.definition.method}</dd></div><div><dt>Evidence class</dt><dd>{definition.definition.evidence_class}</dd></div><div><dt>Definition hash</dt><dd>{definition.definition_sha256}</dd></div><div><dt>Requirements</dt><dd>{definition.definition.requirement_ids.join(', ')}</dd></div><div><dt>Expected engineering result</dt><dd>{definition.definition.expected_result_statement}</dd></div></dl>
      <h3>Controlled checkpoints</h3><div className="checkpoint-obligations">{definition.definition.checkpoint_obligations.map((item) => <article key={item.checkpoint_id}><strong>{item.checkpoint_id}</strong><span>{item.required_content.length} required evidence categories</span></article>)}</div>
    </section>}
    <section className="panel" aria-labelledby="execution-title">
      <div className="panel-heading"><div><span className="eyebrow">Immutable I5 records</span><h2 id="execution-title">Current-run execution and evidence</h2></div></div>
      {summary === undefined ? <p className="empty-state">No VT-FML-N0-N5-001 execution exists for this run.</p> : <>
        <dl className="identity-grid"><div><dt>Execution ID</dt><dd>{summary.execution.validation_execution_id}</dd></div><div><dt>Status</dt><dd>{summary.execution.status}</dd></div><div><dt>Evidence class</dt><dd>{summary.execution.evidence_class}</dd></div><div><dt>Build ID</dt><dd>{summary.execution.application_build_id}</dd></div><div><dt>Configuration</dt><dd>{summary.execution.configuration_id}</dd></div><div><dt>Started</dt><dd>{formatTime(summary.execution.started_scenario_time)}</dd></div></dl>
        <div className="expected-observed-grid"><article><span className="eyebrow">Controlled expected</span><p>{summary.execution.expected_result_statement}</p></article><article><span className="eyebrow">Preserved observed</span><pre>{summary.execution.observed_result === null ? 'Not finalised — no observed result claimed.' : JSON.stringify(summary.execution.observed_result, null, 2)}</pre></article><article><span className="eyebrow">Validation determination</span><strong>{summary.execution.verdict ?? 'NOT DETERMINED'}</strong><p>{summary.execution.verdict_reason ?? 'No PASS/FAIL has been created.'}</p></article></div>
        <h3>Evidence checkpoints</h3><div className="evidence-grid">{summary.evidence_snapshots.map((evidence) => <article key={evidence.evidence_snapshot_id}><div><strong>{evidence.checkpoint_id}</strong><span className="status-badge formal">{evidence.evidence_class}</span></div><p>Revision {evidence.state_revision} · {formatTime(evidence.scenario_time)}</p><small title={evidence.evidence_snapshot_id}>Evidence {shortId(evidence.evidence_snapshot_id)} · hash {shortId(evidence.canonical_payload_sha256)}…</small></article>)}</div>
      </>}
      <div className="validation-actions">{projection.validation.actions.map((action) => <article key={`${action.action_type}:${action.checkpoint_id ?? 'run'}`}><button type="button" disabled={!action.available || busy} onClick={() => onAction(action)}>{validationLabels[action.action_type]}{action.checkpoint_id === null ? '' : ` ${action.checkpoint_id}`}</button><p>{action.reason}</p><span className="reason-code">{humanise(action.reason_code)}</span></article>)}</div>
    </section>
  </div>
}
