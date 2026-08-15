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
        <h3>From approved design to evidence</h3>
        <p>Project decisions → requirements → network and workflow design → application functions → validation definitions and saved evidence.</p>
        <p>Governing artefacts define the approved behavior; implementation modules realise that behavior in the local demonstrator.</p>
        <p>Authoritative artefact versions and SHA-256 identities remain controlled in <code>CURRENT-BASELINE-MANIFEST.json</code>, the immutable configuration manifests and generated evidence packages.</p>
        <dl className="key-value-grid">
          <div><dt>Requirements</dt><dd>v0.4 · 124 stable IDs</dd></div>
          <div><dt>Network Model</dt><dd>v0.4 · explicit v1.0 defect and v1.1 correction</dd></div>
          <div><dt>Validation Plan</dt><dd>v1.5 · 24 tests / 286 RTM relationships</dd></div>
          <div><dt>Machine catalogue</dt><dd>v1.2 · 35 methods / 214 criteria</dd></div>
        </dl>
      </section>
      <section className="panel basis-columns">
        <article><h3>What this demonstrates</h3><ul><li>Configuration-driven topology, outage and source attribution.</li><li>Telemetry quality/freshness gates and conservative restoration decisions.</li><li>Immutable defect, correction, validation and export provenance.</li><li>Separate controlled-validation and trial evidence classes.</li></ul></article>
        <article><h3>Deliberate boundaries</h3><ul><li>Fictional network and deterministic local simulation.</li><li>No real SCADA, ADMS, OMS, GIS or field-equipment connection.</li><li>No production switching or autonomous control capability.</li><li>Not a commercial ADMS or protection-study product.</li></ul></article>
      </section>
    </div>
  )
}
