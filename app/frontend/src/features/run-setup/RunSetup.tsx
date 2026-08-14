import { useState } from 'react'
import type { WorkspaceBootstrap } from '../../api/contracts'
import { shortId } from '../../components/format'

export function RunSetup({ bootstrap, busy, existingInvestigation, onStart, onResumeInvestigation, onStartSafetyWalkthrough }: { bootstrap: WorkspaceBootstrap; busy: boolean; existingInvestigation: boolean; onStart: (actor: string, mode?: 'FORMAL' | 'EXPLORATION', faultSectionId?: string) => void; onResumeInvestigation: (actor: string) => void; onStartSafetyWalkthrough: (actor: string) => void }) {
  const [actor, setActor] = useState(bootstrap.default_actor)
  const [explorationSection, setExplorationSection] = useState(bootstrap.exploration_section_ids[0] ?? '')
  return <main className="start-page">
    <section className="start-hero">
      <div><span className="eyebrow">TasGrid East · fictional utility context</span><h1>OT engineering review workspace</h1><p>Review topology, outage, telemetry, restoration and validation evidence through one controlled local demonstrator.</p></div>
      <div className="boundary-card"><span className="boundary-icon" aria-hidden="true">◇</span><div><strong>Local and simulated</strong><p>{bootstrap.conceptual_boundary_notice}</p></div></div>
    </section>
    <section className="panel reviewer-identity" aria-labelledby="reviewer-title">
      <div><span className="eyebrow">Applies to the selected walkthrough</span><h2 id="reviewer-title">Reviewer identity</h2><p>Choose one guided story below. The selected name is recorded as the simulated actor for that story.</p></div>
      <label>Actor / reviewer<input value={actor} onChange={(event) => setActor(event.target.value)} maxLength={120} /></label>
    </section>
    <section className="run-setup-grid">
      <article className="panel setup-card">
        <span className="eyebrow">Formal validation and defect investigation</span><h2>Prove the operating logic—and show it detecting a defect</h2>
        <p>First run the accepted SEC-A2 isolation-to-restoration walkthrough and validate its result. Then challenge the same operating logic with the preserved DEF-001 configuration error, trace the wrong outcome to its source, apply the correction and repeat the test.</p>
        <button type="button" className="primary-action" disabled={busy || actor.trim().length === 0} onClick={() => onStart(actor.trim())}>{busy ? 'Creating walkthrough…' : 'Start formal validation walkthrough'}</button>
        {existingInvestigation && <button type="button" className="secondary-action setup-secondary-action" disabled={busy || actor.trim().length === 0} onClick={() => onResumeInvestigation(actor.trim())}>Resume preserved defect investigation</button>}
      </article>
      <article className="panel setup-card exploration-setup">
        <span className="eyebrow">Reviewer-driven exploration</span><h2>Try a different fault location</h2>
        <p>Select one represented section as this scenario’s fault location. The application then calculates the affected feeder, isolation boundaries, outage and any restoration option from the same network rules used by the formal run.</p>
        <label>Fault section<select aria-label="Exploration fault section" value={explorationSection} onChange={(event) => setExplorationSection(event.target.value)}>{bootstrap.exploration_section_ids.map((sectionId) => <option key={sectionId} value={sectionId}>{sectionId}</option>)}</select></label>
        <button type="button" className="primary-action" disabled={busy || actor.trim().length === 0 || explorationSection.length === 0} onClick={() => onStart(actor.trim(), 'EXPLORATION', explorationSection)}>{busy ? 'Creating walkthrough…' : 'Start exploration'}</button>
        <p className="evidence-boundary-note"><strong>Exploration only:</strong> saved results remain separate from the approved formal walkthrough.</p>
      </article>
      <article className="panel setup-card safety-setup">
        <span className="eyebrow">Safety-oriented negative case</span><h2>Review stale-telemetry blocking</h2>
        <p>Run the formal fault with deliberately old boundary-switch timestamps. Although the signal quality remains GOOD, the stale readings cannot prove isolation, so the unsafe switching actions remain unavailable.</p>
        <button type="button" className="secondary-action" disabled={busy || actor.trim().length === 0} onClick={() => onStartSafetyWalkthrough(actor.trim())}>{busy ? 'Creating controlled run…' : 'Start stale-evidence walkthrough'}</button>
      </article>
      <article className="panel setup-preview">
        <span className="eyebrow">Scenario identity</span><h2>Run-start context</h2>
        <dl><div><dt>Formal mode</dt><dd>{bootstrap.default_mode} / {bootstrap.default_evidence_class}</dd></div><div><dt>Formal test reference</dt><dd>{bootstrap.formal_test_id}</dd></div><div><dt>Exploration mode</dt><dd>EXPLORATION / EXPLORATORY</dd></div><div><dt>Configuration</dt><dd>{bootstrap.default_configuration_id}</dd></div><div><dt>Formal fault section</dt><dd>SEC-A2 · controlled input</dd></div><div><dt>Scenario epoch</dt><dd>{bootstrap.default_scenario_time}</dd></div><div><dt>Application build</dt><dd title={bootstrap.application_build_id}>{shortId(bootstrap.application_build_id)}…</dd></div><div><dt>Catalogue</dt><dd>v{bootstrap.formal_definition.catalogue_version} · {bootstrap.formal_definition.catalogue_sha256} · {bootstrap.definition_count} accepted definitions; no execution status assumed</dd></div></dl>
      </article>
      <article className="panel lifecycle-card"><span className="eyebrow">Guided review</span><h2>How this workspace is used</h2><ol><li>Load the network record and telemetry as separate information sources.</li><li>Review the calculated network state and customer impact.</li><li>Use only the simulated actions that are currently available.</li><li>Save evidence at each named scenario checkpoint.</li><li>Compare the saved result with the approved test expectation.</li></ol></article>
    </section>
  </main>
}
