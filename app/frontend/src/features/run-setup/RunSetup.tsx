import { useState } from 'react'
import type { WorkspaceBootstrap } from '../../api/contracts'
import { shortId } from '../../components/format'
import { defaultExplorationSection, explorationSectionLabel } from './exploration-options'

export function RunSetup({ bootstrap, busy, existingInvestigation, onStartDefectInvestigation, onStart, onResumeInvestigation, onStartSafetyWalkthrough }: { bootstrap: WorkspaceBootstrap; busy: boolean; existingInvestigation: boolean; onStartDefectInvestigation: (actor: string) => void; onStart: (actor: string, mode?: 'FORMAL' | 'EXPLORATION', faultSectionId?: string) => void; onResumeInvestigation: (actor: string) => void; onStartSafetyWalkthrough: (actor: string) => void }) {
  const actor = bootstrap.default_actor
  const [explorationSection, setExplorationSection] = useState(defaultExplorationSection(bootstrap.exploration_section_ids))
  return <main className="start-page">
    <section className="start-hero">
      <div><span className="eyebrow">TasGrid East · fictional utility context</span><h1>OT systems review workspace</h1><p>Review topology, outage, telemetry, restoration and validation evidence through one controlled local demonstrator.</p></div>
      <div className="boundary-card"><span className="boundary-icon" aria-hidden="true">◇</span><div><strong>Local and simulated</strong><p>{bootstrap.conceptual_boundary_notice}</p></div></div>
    </section>
    <section className="panel walkthrough-introduction" aria-labelledby="walkthrough-introduction-title">
      <span className="eyebrow">Guided walkthroughs</span><h2 id="walkthrough-introduction-title">Choose a walkthrough to begin</h2><p>Start with a reviewer-driven trial to understand the operating sequence, then use the configuration-defect and stale-evidence cases to examine independent validation and conservative safety blocking.</p>
    </section>
    <section className="run-setup-grid">
      <article className="panel setup-card exploration-setup">
        <span className="eyebrow">Reviewer-driven trials</span><h2>Test a selected fault location</h2>
        <p>Select one represented section as this scenario’s fault location. The application then calculates the affected feeder, isolation boundaries, outage and any restoration option from the same network rules used throughout the demonstrator.</p>
        <label>Fault section<select aria-label="Trial fault section" value={explorationSection} onChange={(event) => setExplorationSection(event.target.value)}>{bootstrap.exploration_section_ids.map((sectionId) => <option key={sectionId} value={sectionId}>{explorationSectionLabel(sectionId)}</option>)}</select></label>
        <button type="button" className="primary-action" disabled={busy || actor.trim().length === 0 || explorationSection.length === 0} onClick={() => onStart(actor.trim(), 'EXPLORATION', explorationSection)}>{busy ? 'Creating trial…' : 'Start trial'}</button>
        <p className="evidence-boundary-note"><strong>Trials:</strong> saved results remain separate from the defect-investigation validation record.</p>
      </article>
      <article className="panel setup-card">
        <span className="eyebrow">Validation and defect investigation</span><h2>Expose a seeded configuration defect—and prove its correction</h2>
        <p>Run the isolation-to-restoration sequence directly against preserved GIS configuration v1.0. Live assurance can pass because the supplied information is internally coherent; independent validation detects the wrong customer-impact result, opening the investigation, correction and controlled repeat.</p>
        <button type="button" className="primary-action" disabled={busy || actor.trim().length === 0} onClick={() => existingInvestigation ? onResumeInvestigation(actor.trim()) : onStartDefectInvestigation(actor.trim())}>{busy ? 'Opening defect walkthrough…' : existingInvestigation ? 'Resume preserved defect investigation' : 'Start defect walkthrough'}</button>
      </article>
      <article className="panel setup-card safety-setup">
        <span className="eyebrow">Safety-oriented negative case</span><h2>Review stale-telemetry blocking</h2>
        <p>Run the controlled fault with deliberately old boundary-switch timestamps. Although the signal quality remains GOOD, the stale readings cannot prove isolation, so the unsafe switching actions remain unavailable.</p>
        <button type="button" className="secondary-action" disabled={busy || actor.trim().length === 0} onClick={() => onStartSafetyWalkthrough(actor.trim())}>{busy ? 'Creating controlled run…' : 'Start stale-evidence walkthrough'}</button>
      </article>
      <article className="panel setup-preview">
        <span className="eyebrow">Scenario identity</span><h2>Run-start context</h2>
        <dl><div><dt>Validation mode</dt><dd>CONTROLLED / VALIDATION</dd></div><div><dt>Validation path</dt><dd>VT-TOP-DEF-001 → {bootstrap.formal_test_id}</dd></div><div><dt>Trial configuration</dt><dd>{bootstrap.default_configuration_id}</dd></div><div><dt>Defect starting configuration</dt><dd>network-configuration-v1.0</dd></div><div><dt>Controlled fault section</dt><dd>SEC-A2 · controlled input</dd></div><div><dt>Scenario epoch</dt><dd>{bootstrap.default_scenario_time}</dd></div><div><dt>Application build</dt><dd title={bootstrap.application_build_id}>{shortId(bootstrap.application_build_id)}…</dd></div><div><dt>Catalogue</dt><dd>v{bootstrap.formal_definition.catalogue_version} · {bootstrap.formal_definition.catalogue_sha256} · {bootstrap.definition_count} accepted definitions; no execution status assumed</dd></div></dl>
      </article>
      <article className="panel lifecycle-card"><span className="eyebrow">Guided review</span><h2>How this workspace is used</h2><ol><li>Load the network record and telemetry as separate information sources.</li><li>Review the calculated network state and customer impact.</li><li>Use only the simulated actions that are currently available.</li><li>Save evidence at each named scenario checkpoint.</li><li>Compare the saved result with the approved test expectation.</li></ol></article>
    </section>
  </main>
}
