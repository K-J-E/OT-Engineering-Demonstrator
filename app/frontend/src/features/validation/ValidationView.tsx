import type { ValidationWorkspaceAction, WorkspaceProjection } from '../../api/contracts'
import { formatTime, humanise, shortId } from '../../components/format'

const validationLabels: Record<ValidationWorkspaceAction['action_type'], string> = {
  START_EXECUTION: 'Start formal execution',
  CAPTURE_CHECKPOINT: 'Capture current checkpoint',
  FINALISE_EXECUTION: 'Finalise execution',
}

export function ValidationView({ projection, busy, onAction }: { projection: WorkspaceProjection; busy: boolean; onAction: (action: ValidationWorkspaceAction) => void }) {
  if (projection.run.mode === 'EXPLORATION') {
    const definitions = projection.validation.definitions.filter((item) => item.definition.evidence_class === 'EXPLORATORY')
    return <div className="view-stack">
      <section className="panel" aria-labelledby="exploration-evidence-title">
        <div className="panel-heading"><div><span className="eyebrow">Separate non-formal evidence path</span><h2 id="exploration-evidence-title">Exploration evidence controls</h2></div><span className="status-badge exploratory">EXPLORATORY</span></div>
        <div className="callout warning"><strong>Not formal validation evidence.</strong> The selected fault remains run input on corrected v1.1. Captured records cannot change the FORMAL progress totals or be relabelled FORMAL.</div>
        <dl className="identity-grid"><div><dt>Selected section</dt><dd>{projection.run.fault_section_id}</dd></div><div><dt>Configuration</dt><dd>{projection.run.configuration_id}</dd></div><div><dt>Scenario run</dt><dd>{projection.run.scenario_run_id}</dd></div><div><dt>Evidence class</dt><dd>{projection.run.evidence_class}</dd></div></dl>
      </section>
      <section className="panel" aria-labelledby="exploration-definitions-title">
        <div className="panel-heading"><div><span className="eyebrow">Accepted Step 9 verification definitions</span><h2 id="exploration-definitions-title">Exploratory definitions and preserved records</h2></div><span className="status-badge neutral">{definitions.length} definitions</span></div>
        <div className="record-list">{definitions.map((definition) => {
          const summary = projection.validation.run_executions.find((item) => item.execution.test_id === definition.definition.test_id)
          const cases = definition.definition.constituent_cases
          const directMethod = definition.definition.determination_method
          const criterionCount = directMethod?.criteria.length ?? cases.reduce((total, item) => total + (item.determination_method?.criteria.length ?? 0), 0)
          return <article key={definition.definition.test_id}><span className="status-badge exploratory">EXPLORATORY</span><h3>{definition.definition.test_id} · {definition.definition.title}</h3><p>{definition.definition.expected_result_statement}</p><p><strong>Defined determination coverage:</strong> {directMethod?.method_id ?? 'DC-004 constituent methods'} · {criterionCount} controlled criteria. Defined mappings are not achieved evidence.</p>{cases.length > 0 && <p><strong>{cases.length} controlled constituent cases.</strong> Current-section cases: {cases.filter((item) => item.selected_fault_section_id === projection.run.fault_section_id).map((item) => item.case_id).join(', ') || 'none'}.</p>}<small>{summary === undefined ? 'No execution for this run.' : `${summary.execution.status} · ${summary.execution.case_id ?? 'single-run'} · ${summary.evidence_snapshots.length} immutable checkpoint(s) · ${summary.execution.verdict ?? 'NOT DETERMINED'}`}</small></article>
        })}</div>
        <div className="validation-actions">{projection.validation.actions.map((action) => {
          const label = action.action_type === 'START_EXECUTION'
            ? `Start exploratory execution ${action.test_id}${action.case_id === null ? '' : ` · ${action.case_id}`}`
            : action.action_type === 'CAPTURE_CHECKPOINT'
              ? `Capture exploratory checkpoint ${action.test_id}`
              : `Finalise exploratory execution ${action.test_id}`
          return <article key={`${action.test_id}:${action.case_id ?? 'single'}:${action.action_type}`}><button type="button" disabled={!action.available || busy} onClick={() => onAction(action)}>{label}</button><p>{action.reason}</p><span className="reason-code">{humanise(action.reason_code)}</span></article>
        })}</div>
      </section>
      <section className="panel" aria-labelledby="composite-assurance-title">
        <div className="panel-heading"><div><span className="eyebrow">DC-004 multi-run assurance</span><h2 id="composite-assurance-title">Composite validation results</h2></div><span className="status-badge exploratory">EXPLORATORY</span></div>
        <div className="callout warning"><strong>Not one fictional run.</strong> Each linked case retains its own scenario run, execution, checkpoint time and evidence identity.</div>
        {projection.validation.composites.length === 0 ? <p className="empty-state">No composite assurance record has been assembled.</p> : <div className="record-list">{projection.validation.composites.map((composite) => <article key={composite.composite_result_id}><div><span className="status-badge exploratory">{composite.evidence_class}</span><span className="status-badge neutral">{composite.completeness.status}</span></div><h3>{composite.test_id} · {composite.determination ?? 'NOT DETERMINED'}</h3><p>{composite.determination_reason}</p><p><strong>Required:</strong> {composite.required_case_ids.join(', ')}</p><p><strong>Present:</strong> {composite.completeness.present_case_ids.join(', ') || 'none'} · <strong>Missing:</strong> {composite.completeness.missing_case_ids.join(', ') || 'none'}</p><dl className="identity-grid"><div><dt>Catalogue</dt><dd>v{composite.catalogue_version} · {composite.catalogue_sha256}</dd></div><div><dt>Build</dt><dd>{composite.application_build_id}</dd></div><div><dt>Configuration</dt><dd>{composite.configuration_id} v{composite.configuration_version}</dd></div></dl>{composite.constituent_links.map((link) => <p key={link.case_id}><strong>{link.case_id}</strong> · {link.source_kind === 'EXECUTION_RESULT' ? `execution ${link.validation_execution_id}` : `suspension ${link.suspension_record_id}`} · run {link.scenario_run_id ?? 'not created'} · {link.constituent_verdict ?? 'NOT DETERMINED'} · {link.evidence_snapshot_ids.length} execution-evidence link(s)</p>)}</article>)}</div>}
      </section>
      <section className="panel" aria-labelledby="validation-suspensions-title"><div className="panel-heading"><div><span className="eyebrow">DC-005 controlled assurance stop</span><h2 id="validation-suspensions-title">Validation suspension records</h2></div><span className="status-badge neutral">{projection.validation.suspensions.length}</span></div><div className="callout warning"><strong>BLOCKED-TEST is not an executed verdict.</strong> These immutable records preserve the trusted target, condition evidence, local authority and lifecycle position without fabricating a run or PASS/FAIL result.</div>{projection.validation.suspensions.length === 0 ? <p className="empty-state">No controlled validation suspension has been finalised.</p> : <div className="record-list">{projection.validation.suspensions.map((item) => <article key={item.suspension_record_id}><h3>{item.condition_id} · BLOCKED-TEST</h3><p>{humanise(item.lifecycle_position)} · {item.authority.authority_kind}</p><dl className="identity-grid"><div><dt>Reason</dt><dd>{item.reason_code}</dd></div><div><dt>Attempt</dt><dd>{item.validation_attempt_id}</dd></div><div><dt>Target</dt><dd>{item.target_selection_id}</dd></div><div><dt>Verifier build</dt><dd>{item.verifier_application_build_id}</dd></div><div><dt>Fingerprint</dt><dd>{item.deterministic_fingerprint}</dd></div><div><dt>Run/execution</dt><dd>{item.scenario_run_id ?? 'not created'} / {item.validation_execution_id ?? 'not created'}</dd></div></dl></article>)}</div>}</section>
      <section className="panel validation-progress" aria-labelledby="formal-progress-watch-title">
        <div className="panel-heading"><div><span className="eyebrow">QA-034 separation watch</span><h2 id="formal-progress-watch-title">Formal progress remains separate</h2></div><span className="status-badge formal">FORMAL</span></div>
        <p>{projection.validation.progress.definition_count} FORMAL definitions; {projection.validation.progress.execution_count} FORMAL executions; {projection.validation.progress.pass_count} FORMAL PASS. Exploratory records are excluded from every value.</p>
      </section>
    </div>
  }
  const definition = projection.validation.definitions.find((item) => item.definition.test_id === 'VT-FML-N0-N5-001')
  const summary = projection.validation.run_executions.find((item) => item.execution.test_id === 'VT-FML-N0-N5-001')
  const progress = projection.validation.progress
  return <div className="view-stack">
    <section className="panel validation-progress" aria-labelledby="validation-progress-title">
      <div className="panel-heading"><div><span className="eyebrow">Backend-assembled catalogue status</span><h2 id="validation-progress-title">Formal validation progress</h2></div><span className="status-badge formal">FORMAL</span></div>
      <div className="callout warning"><strong>Definitions are not executions.</strong> An accepted definition with no execution is not PASS, and operational BLOCKED/REJECTED is separate from validation determination.</div>
      <p className="progress-scope"><strong>FORMAL scope:</strong> {progress.definition_count} of {projection.validation.definitions.length} total controlled catalogue definitions.</p>
      <div className="progress-grid"><article><strong>{progress.definition_count}</strong><span>Controlled definitions</span></article><article><strong>{progress.definitions_without_execution_count}</strong><span>Without execution</span></article><article><strong>{progress.execution_count}</strong><span>Executions started</span></article><article><strong>{progress.finalised_execution_count}</strong><span>Finalised</span></article><article><strong>{progress.pass_count}</strong><span>PASS</span></article><article><strong>{progress.fail_count}</strong><span>FAIL</span></article></div>
    </section>
    {definition !== undefined && <section className="panel" aria-labelledby="definition-title">
      <div className="panel-heading"><div><span className="eyebrow">Read-only accepted definition</span><h2 id="definition-title">{definition.definition.test_id} · {definition.definition.title}</h2></div><span className="status-badge neutral">v{definition.definition.version}</span></div>
      <dl className="definition-grid"><div><dt>Objective</dt><dd>{definition.definition.objective}</dd></div><div><dt>Method</dt><dd>{definition.definition.method}</dd></div><div><dt>Evidence class</dt><dd>{definition.definition.evidence_class}</dd></div><div><dt>Validation Catalogue</dt><dd>v{definition.catalogue_version} · {definition.catalogue_sha256}</dd></div><div><dt>Definition hash</dt><dd>{definition.definition_sha256}</dd></div><div><dt>Requirements</dt><dd>{definition.definition.requirement_ids.join(', ')}</dd></div><div><dt>Expected engineering result</dt><dd>{definition.definition.expected_result_statement}</dd></div></dl>
      {definition.definition.determination_method !== undefined && definition.definition.determination_method !== null && <div className="callout neutral"><strong>Controlled determination method:</strong> {definition.definition.determination_method.method_id} · {definition.definition.determination_method.context_kind} · {definition.definition.determination_method.criteria.length} criteria. Criterion mappings show defined coverage only; PASS/FAIL requires the complete immutable finding chain.</div>}
      {definition.definition.determination_method !== undefined && definition.definition.determination_method !== null && <ul>{definition.definition.determination_method.criteria.map((criterion) => <li key={criterion.criterion_id}>{criterion.criterion_id} · {criterion.kind}</li>)}</ul>}
      <h3>Controlled checkpoints</h3><div className="checkpoint-obligations">{definition.definition.checkpoint_obligations.map((item) => <article key={item.checkpoint_id}><strong>{item.checkpoint_id}</strong><span>{item.required_content.length} required evidence categories</span></article>)}</div>
    </section>}
    <section className="panel" aria-labelledby="execution-title">
      <div className="panel-heading"><div><span className="eyebrow">Immutable I5 records</span><h2 id="execution-title">Current-run execution and evidence</h2></div></div>
      {summary === undefined ? <p className="empty-state">No VT-FML-N0-N5-001 execution exists for this run.</p> : <>
        <dl className="identity-grid"><div><dt>Execution ID</dt><dd>{summary.execution.validation_execution_id}</dd></div><div><dt>Scenario run</dt><dd>{summary.execution.scenario_run_id}</dd></div><div><dt>Status</dt><dd>{summary.execution.status}</dd></div><div><dt>Evidence class</dt><dd>{summary.execution.evidence_class}</dd></div><div><dt>Build ID</dt><dd>{summary.execution.application_build_id}</dd></div><div><dt>Configuration</dt><dd>{summary.execution.configuration_id}</dd></div><div><dt>Started</dt><dd>{formatTime(summary.execution.started_scenario_time)}</dd></div></dl>
        <div className="expected-observed-grid"><article><span className="eyebrow">Controlled expected</span><p>{summary.execution.expected_result_statement}</p></article><article><span className="eyebrow">Preserved observed</span><pre>{summary.execution.observed_result === null ? 'Not finalised — no observed result claimed.' : JSON.stringify(summary.execution.observed_result, null, 2)}</pre></article><article><span className="eyebrow">Validation determination</span><strong>{summary.execution.verdict ?? 'NOT DETERMINED'}</strong><p>{summary.execution.verdict_reason ?? 'No PASS/FAIL has been created.'}</p></article></div>
        <h3>Evidence checkpoints</h3><div className="evidence-grid">{summary.evidence_snapshots.map((evidence) => <article key={evidence.evidence_snapshot_id}><div><strong>{evidence.checkpoint_id}</strong><span className="status-badge formal">{evidence.evidence_class}</span></div><p>Revision {evidence.state_revision} · {formatTime(evidence.scenario_time)}</p><small title={evidence.evidence_snapshot_id}>Evidence {shortId(evidence.evidence_snapshot_id)} · hash {shortId(evidence.canonical_payload_sha256)}…</small></article>)}</div>
      </>}
      <div className="validation-actions">{projection.validation.actions.map((action) => <article key={`${action.action_type}:${action.checkpoint_id ?? 'run'}`}><button type="button" disabled={!action.available || busy} onClick={() => onAction(action)}>{validationLabels[action.action_type]}{action.checkpoint_id === null ? '' : ` ${action.checkpoint_id}`}</button><p>{action.reason}</p><span className="reason-code">{humanise(action.reason_code)}</span></article>)}</div>
    </section>
  </div>
}
