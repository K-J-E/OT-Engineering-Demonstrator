import type { WorkspaceProjection } from '../../api/contracts'

export function EngineeringBasis({ projection }: { projection: WorkspaceProjection }) {
  return (
    <div className="panel-stack">
      <section className="panel">
        <span className="eyebrow">Read-only engineering basis</span>
        <h2>Approved implementation traceability</h2>
        <p>This view identifies the controlled engineering baseline implemented by the local demonstrator. It provides no operational action or configuration-editing control.</p>
        <dl className="key-value-grid">
          <div><dt>Application build</dt><dd><code>{projection.run.application_build_id}</code></dd></div>
          <div><dt>Network Configuration</dt><dd>{projection.run.configuration_id} · v{projection.run.configuration_version}</dd></div>
          <div><dt>Evidence class</dt><dd>{projection.run.evidence_class}</dd></div>
          <div><dt>Scenario run</dt><dd><code>{projection.run.scenario_run_id}</code></dd></div>
        </dl>
      </section>
      <section className="panel">
        <h3>Authority chain</h3>
        <p>Governing artefacts → requirements → network/system/workflow/demonstrator design → implementation modules → validation definitions and preserved evidence.</p>
        <p>Authoritative artefact versions and SHA-256 identities remain controlled in the repository baseline manifest and evidence packages.</p>
      </section>
    </div>
  )
}
