import { useState } from 'react'
import type { WorkspaceBootstrap } from '../../api/contracts'
import { shortId } from '../../components/format'

export function RunSetup({ bootstrap, busy, onStart, onStartInvestigation }: { bootstrap: WorkspaceBootstrap; busy: boolean; onStart: (actor: string, mode?: 'FORMAL' | 'EXPLORATION', faultSectionId?: string) => void; onStartInvestigation: (actor: string) => void }) {
  const [actor, setActor] = useState(bootstrap.default_actor)
  const [explorationSection, setExplorationSection] = useState(bootstrap.exploration_section_ids[0] ?? '')
  return <main className="start-page">
    <section className="start-hero">
      <div><span className="eyebrow">TasGrid East · fictional utility context</span><h1>OT engineering review workspace</h1><p>Review topology, outage, telemetry, restoration and validation evidence through one controlled local demonstrator.</p></div>
      <div className="boundary-card"><span className="boundary-icon" aria-hidden="true">◇</span><div><strong>Local and simulated</strong><p>{bootstrap.conceptual_boundary_notice}</p></div></div>
    </section>
    <section className="run-setup-grid">
      <article className="panel setup-card">
        <span className="eyebrow">Approved formal run</span><h2>Start {bootstrap.formal_test_id}</h2>
        <p>The formal path is fixed to corrected Network Configuration v1.1 and the controlled SEC-A2 scenario.</p>
        <label>Actor / reviewer<input value={actor} onChange={(event) => setActor(event.target.value)} maxLength={120} /></label>
        <button type="button" className="primary-action" disabled={busy || actor.trim().length === 0} onClick={() => onStart(actor.trim())}>{busy ? 'Creating controlled run…' : 'Start formal v1.1 run'}</button>
      </article>
      <article className="panel setup-card exploration-setup">
        <span className="eyebrow">Reviewer-driven exploration</span><h2>Start corrected-v1.1 Exploration</h2>
        <p>Select one represented section as transient run input. The backend derives feeder roles, boundaries, outage and any restoration outcome through the same engineering engine.</p>
        <label>Fault section<select aria-label="Exploration fault section" value={explorationSection} onChange={(event) => setExplorationSection(event.target.value)}>{bootstrap.exploration_section_ids.map((sectionId) => <option key={sectionId} value={sectionId}>{sectionId}</option>)}</select></label>
        <button type="button" className="primary-action" disabled={busy || actor.trim().length === 0 || explorationSection.length === 0} onClick={() => onStart(actor.trim(), 'EXPLORATION', explorationSection)}>{busy ? 'Creating controlled run…' : 'Start exploratory v1.1 run'}</button>
        <p className="evidence-boundary-note"><strong>EXPLORATORY:</strong> this run cannot satisfy formal validation automatically and cannot select defective v1.0.</p>
      </article>
      <article className="panel setup-card">
        <span className="eyebrow">Controlled defect workflow</span><h2>Begin DEF-001 investigation</h2>
        <p>Execute the preserved v1.0 post-trip test first, then investigate its real topology and outage consequence before recording any root-cause judgement.</p>
        <button type="button" className="secondary-action" disabled={busy || actor.trim().length === 0} onClick={() => onStartInvestigation(actor.trim())}>{busy ? 'Creating controlled run…' : 'Run v1.0 test and investigate'}</button>
      </article>
      <article className="panel setup-preview">
        <span className="eyebrow">Backend-controlled identity</span><h2>Run-start context</h2>
        <dl><div><dt>Formal mode</dt><dd>{bootstrap.default_mode} / {bootstrap.default_evidence_class}</dd></div><div><dt>Exploration mode</dt><dd>EXPLORATION / EXPLORATORY</dd></div><div><dt>Configuration</dt><dd>{bootstrap.default_configuration_id}</dd></div><div><dt>Formal fault section</dt><dd>SEC-A2 · controlled input</dd></div><div><dt>Scenario epoch</dt><dd>{bootstrap.default_scenario_time}</dd></div><div><dt>Application build</dt><dd title={bootstrap.application_build_id}>{shortId(bootstrap.application_build_id)}…</dd></div><div><dt>Catalogue</dt><dd>v{bootstrap.formal_definition.catalogue_version} · {bootstrap.formal_definition.catalogue_sha256} · {bootstrap.definition_count} accepted definitions; no execution status assumed</dd></div></dl>
      </article>
      <article className="panel lifecycle-card"><span className="eyebrow">Engineering lifecycle</span><h2>How this workspace is used</h2><ol><li>Load controlled configuration and observed telemetry separately.</li><li>Review backend-derived topology and outage consequences.</li><li>Use only backend-authorised simulated actions.</li><li>Capture immutable evidence at controlled checkpoints.</li><li>Compare expected and observed only through the accepted validation model.</li></ol></article>
    </section>
  </main>
}
