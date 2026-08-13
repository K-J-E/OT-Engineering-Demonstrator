import type { WorkspaceProjection } from '../../api/contracts'
import { humanise, shortId } from '../../components/format'

export function ContextRibbon({ projection }: { projection: WorkspaceProjection }) {
  const { run, summary } = projection
  return (
    <section className="context-ribbon" aria-label="Persistent run context">
      <div><span className="eyebrow">Mode</span><strong>{run.mode}</strong></div>
      <div><span className="eyebrow">Evidence class</span><strong>{run.evidence_class}</strong></div>
      <div className="run-identity" title={run.scenario_run_id}>
        <span className="eyebrow">Scenario run</span><strong>{shortId(run.scenario_run_id)}</strong>
        <code data-testid="full-run-id">{run.scenario_run_id}</code>
      </div>
      <div><span className="eyebrow">Configuration</span><strong>{run.configuration_id} · v{run.configuration_version}</strong></div>
      <div><span className="eyebrow">Active fault section</span><strong>{run.fault_section_id}</strong></div>
      <div><span className="eyebrow">Workflow stage</span><strong>{humanise(run.workflow_stage)}</strong></div>
      {run.mode === 'FORMAL'
        ? <div><span className="eyebrow">Formal state</span><strong data-testid="formal-state">{run.network_state_label}</strong></div>
        : <div><span className="eyebrow">Derived stage</span><strong data-testid="exploration-stage">{humanise(run.workflow_stage)}</strong></div>}
      <div><span className="eyebrow">State revision</span><strong>{run.state_revision}</strong></div>
      <div><span className="eyebrow">Assessment</span><strong>{humanise(summary.current_assessment_status)}</strong></div>
      <div><span className="eyebrow">Backend build</span><code>{run.application_build_id}</code></div>
    </section>
  )
}
