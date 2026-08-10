import { useState } from 'react'
import type { WorkspaceBootstrap } from '../../api/contracts'
import { shortId } from '../../components/format'

export function RunSetup({ bootstrap, busy, onStart, onStartInvestigation }: { bootstrap: WorkspaceBootstrap; busy: boolean; onStart: (actor: string) => void; onStartInvestigation: (actor: string) => void }) {
  const [actor, setActor] = useState(bootstrap.default_actor)
  return <main className="start-page">
    <section className="start-hero">
      <div><span className="eyebrow">TasGrid East · fictional utility context</span><h1>OT engineering review workspace</h1><p>Review topology, outage, telemetry, restoration and validation evidence through one controlled local demonstrator.</p></div>
      <div className="boundary-card"><span className="boundary-icon" aria-hidden="true">◇</span><div><strong>Local and simulated</strong><p>{bootstrap.conceptual_boundary_notice}</p></div></div>
    </section>
    <section className="run-setup-grid">
      <article className="panel setup-card">
        <span className="eyebrow">Approved formal run</span><h2>Start VT-FML-N0-N5-001</h2>
        <p>The formal path is fixed to corrected Network Configuration v1.1 and the controlled SEC-A2 scenario. Exploration selection is reserved for I8.</p>
        <label>Actor / reviewer<input value={actor} onChange={(event) => setActor(event.target.value)} maxLength={120} /></label>
        <button type="button" className="primary-action" disabled={busy || actor.trim().length === 0} onClick={() => onStart(actor.trim())}>{busy ? 'Creating controlled run…' : 'Start formal v1.1 run'}</button>
      </article>
      <article className="panel setup-card">
        <span className="eyebrow">Controlled defect workflow</span><h2>Begin DEF-001 investigation</h2>
        <p>Execute the preserved v1.0 post-trip test first, then investigate its real topology and outage consequence before recording any root-cause judgement.</p>
        <button type="button" className="secondary-action" disabled={busy || actor.trim().length === 0} onClick={() => onStartInvestigation(actor.trim())}>{busy ? 'Creating controlled run…' : 'Run v1.0 test and investigate'}</button>
      </article>
      <article className="panel setup-preview">
        <span className="eyebrow">Backend-controlled identity</span><h2>Run-start context</h2>
        <dl><div><dt>Mode</dt><dd>{bootstrap.default_mode}</dd></div><div><dt>Evidence class</dt><dd>{bootstrap.default_evidence_class}</dd></div><div><dt>Configuration</dt><dd>{bootstrap.default_configuration_id}</dd></div><div><dt>Fault section</dt><dd>SEC-A2 · controlled formal input</dd></div><div><dt>Scenario epoch</dt><dd>{bootstrap.default_scenario_time}</dd></div><div><dt>Application build</dt><dd title={bootstrap.application_build_id}>{shortId(bootstrap.application_build_id)}…</dd></div><div><dt>Catalogue</dt><dd>{bootstrap.definition_count} accepted definitions; no execution status assumed</dd></div></dl>
      </article>
      <article className="panel lifecycle-card"><span className="eyebrow">Engineering lifecycle</span><h2>How this workspace is used</h2><ol><li>Load controlled configuration and observed telemetry separately.</li><li>Review backend-derived topology and outage consequences.</li><li>Use only backend-authorised simulated actions.</li><li>Capture immutable evidence at controlled checkpoints.</li><li>Compare expected and observed only through the accepted validation model.</li></ol></article>
    </section>
  </main>
}
