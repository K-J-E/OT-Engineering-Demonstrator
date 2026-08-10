import type { WorkspaceProjection } from '../../api/contracts'
import { formatTime, shortId } from '../../components/format'

export function EvidenceLibrary({ projection }: { projection: WorkspaceProjection }) {
  return <section className="panel" aria-labelledby="evidence-library-title">
    <div className="panel-heading"><div><span className="eyebrow">Preserved I5 source records</span><h2 id="evidence-library-title">Evidence library</h2></div><span className="status-badge formal">{projection.run.evidence_class}</span></div>
    <div className="callout neutral">This view reads immutable execution and checkpoint records. It does not reconstruct evidence from current live state, alter determinations or export ZIP packages; export remains I8.</div>
    {projection.validation.run_executions.length === 0 ? <p className="empty-state">No validation execution records are linked to this run.</p> : <div className="record-list">{projection.validation.run_executions.map((summary) => <article key={summary.execution.validation_execution_id}>
      <div><span className="status-badge neutral">{summary.execution.status}</span><span className="status-badge formal">{summary.execution.evidence_class}</span>{summary.execution.verdict !== null && <span className={`status-badge ${summary.execution.verdict === 'PASS' ? 'success' : 'danger'}`}>{summary.execution.verdict}</span>}</div>
      <h3>{summary.execution.test_id}</h3><p>{summary.execution.expected_result_statement}</p>
      <dl><div><dt>Execution</dt><dd>{summary.execution.validation_execution_id}</dd></div><div><dt>Configuration</dt><dd>{summary.execution.configuration_id}</dd></div><div><dt>Build</dt><dd>{summary.execution.application_build_id}</dd></div><div><dt>Started</dt><dd>{formatTime(summary.execution.started_scenario_time)}</dd></div></dl>
      <div className="evidence-grid">{summary.evidence_snapshots.map((evidence) => <article key={evidence.evidence_snapshot_id}><strong>{evidence.checkpoint_id}</strong><span>Revision {evidence.state_revision}</span><small title={evidence.evidence_snapshot_id}>Evidence {shortId(evidence.evidence_snapshot_id)} · {evidence.content_categories.length} categories</small></article>)}</div>
    </article>)}</div>}
  </section>
}
