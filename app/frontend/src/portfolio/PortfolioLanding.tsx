import type { ReactNode } from 'react'
import { portfolioConfig, type PortfolioConfig } from './config'
import './portfolio.css'

const operationalFlow = [
  ['Configured source data', 'Network configuration', 'Conceptual GIS connectivity and equipment records'],
  ['Operational observation', 'State · quality · time', 'SCADA-like values kept separate from their trustworthiness'],
  ['Calculated network state', 'Topology and energisation', 'Calculated source paths and supplied sections'],
  ['Operational consequence', 'Outage and customers', 'Affected sections translated into customer impact'],
  ['Controlled decision', 'Restoration assessment', 'Telemetry, isolation, radiality and capacity checks'],
  ['Independent record', 'Validation and evidence', 'Accepted expectations compared with preserved results'],
]

const lifecycle = [
  'Domain investigation', 'Bounded network model', 'Requirements and validation', 'Controlled increments and review',
  'Failed evidence', 'Investigation and change', 'Repeat validation', 'Reviewable demonstrator',
]

const technicalStories = [
  { marker: '01', title: 'The outcome is calculated—not scripted', body: 'Customer impact and restoration results are derived from network connectivity, switch state and observations rather than selected from a hard-coded answer table. The demonstrator therefore exposes the consequence of its source information.', takeaway: 'Configuration + observations → calculated consequence' },
  { marker: '02', title: 'A coherent run can still be wrong', body: 'A seeded GIS endpoint creates a false source path. The inputs remain internally coherent, so run-time assurance can allow the sequence; independent validation exposes the wrong result—400 customers affected instead of the accepted 850.', takeaway: 'Assurance PASS · Validation FAIL · Investigation opened' },
  { marker: '03', title: 'Failure is preserved—not overwritten', body: 'The failed v1.0 result remains evidence. The corrected v1.1 network configuration is a separate locked baseline, and the repeat keeps the operating logic unchanged so configuration is the only changed variable.', takeaway: 'One changed variable: network configuration' },
  { marker: '04', title: 'The safety boundary is exact', body: 'The negative case proves the first stale value at 60,001 ms rather than using an arbitrary old timestamp. It also shows why GOOD signal quality does not make an out-of-date observation usable for switching.', takeaway: 'GOOD quality + stale time = unusable input' },
  { marker: '05', title: 'Validation stopped before it overclaimed', body: 'Individual runs were calculable, but the first evidence model could not truthfully express one overall multi-run determination. Work stopped until the model preserved each constituent result and its provenance in a composite record.', takeaway: 'No truthful aggregate verdict → no verdict' },
  { marker: '06', title: 'Operational blocking is not a failed test', body: 'Unsafe operating conditions cause an action to be withheld. Insufficient evidence causes validation to be suspended—not passed or failed. Keeping those states separate prevents missing evidence from being mistaken for a network decision.', takeaway: 'Withhold an action ≠ suspend a validation' },
]

function SectionHeading({ eyebrow, title, children }: { eyebrow: string; title: string; children?: ReactNode }) {
  return <div className="portfolio-section-heading"><span>{eyebrow}</span><h2>{title}</h2>{children}</div>
}

function ConfiguredLink({ href, children, className = '', download = false }: { href: string | null; children: ReactNode; className?: string; download?: boolean }) {
  if (href === null) return <span className={`portfolio-resource-link pending ${className}`} aria-disabled="true">{children}<small>Asset pending</small></span>
  return <a className={`portfolio-resource-link ${className}`} href={href} target="_blank" rel="noreferrer" download={download || undefined}>{children}<small>Open resource ↗</small></a>
}

export function PortfolioLanding({ config = portfolioConfig }: { config?: PortfolioConfig }) {
  return <div className="portfolio-page-shell">
    <header className="portfolio-header">
      <a className="portfolio-identity" href="#top" aria-label="Kenneth Ebenezer showcase home"><span>KE</span><div><strong>Kenneth Ebenezer</strong><small>Engineering control systems / Information systems</small></div></a>
      <nav aria-label="Portfolio sections"><a href="#approach">Project approach</a><a href="#automation">V2 automation opportunities</a><a href="#resources">Project resources</a></nav>
      <a className="portfolio-header-demo" href={config.demoUrl}>Open live demonstrator <span aria-hidden="true">↗</span></a>
    </header>

    <main id="top">
      <section className="portfolio-hero" aria-labelledby="portfolio-title">
        <div className="portfolio-hero-copy">
          <p className="portfolio-project-title">Engineering Demonstrator — Distribution Operations, Assurance and Defect Investigation</p>
          <h1 id="portfolio-title">A simplified, simulated OT systems project—<em>not a software product showcase.</em></h1>
          <p className="portfolio-hero-lead">Used engineering-systems and control foundations, including marine electrical-distribution exposure, together with postgraduate information-systems, Python, database and AI experience to learn how power-network meaning becomes operational-system data and behaviour.</p>
          <div className="portfolio-boundary"><span aria-hidden="true">◇</span><strong>Fictional and simulated</strong><p>No real utility data or control · not a production SCADA, ADMS or OMS</p></div>
          <div className="portfolio-hero-actions">
            <a className="portfolio-button primary" href="#approach">Explore the project approach</a>
            <a className="portfolio-button text" href={config.demoUrl}>Open the live demonstrator <span aria-hidden="true">→</span></a>
          </div>
        </div>
        <aside className="portfolio-hero-brief" aria-label="Project classification">
          <div className="portfolio-brief-header"><span>Reviewer brief</span><strong>01 / Project intent</strong></div>
          <dl><div><dt>Purpose</dt><dd>Develop an end-to-end understanding of how network information becomes operational decisions</dd></div><div><dt>Approach</dt><dd>Simplify the network and integrations so the complete information and decision chain can be examined</dd></div><div><dt>Demonstrator</dt><dd>Make the reasoning, tests and investigation inspectable</dd></div><div><dt>Positioning</dt><dd>Preparation for supervised early-career work at the power-systems and information-systems boundary</dd></div></dl>
          <div className="portfolio-signal-line" aria-hidden="true"><span></span><span></span><span></span><span></span></div>
          <p><strong>What this is meant to show:</strong> how I investigate an unfamiliar technical domain, set a disciplined scope, preserve evidence, trace a failure and recognise where experienced supervision remains essential.</p>
        </aside>
      </section>

      <section className="portfolio-section portfolio-evaluate" id="evaluate" aria-labelledby="evaluate-title">
        <SectionHeading eyebrow="Rapid review" title="What to evaluate"><p>Three evidence-led themes carry more weight here than the browser interface itself.</p></SectionHeading>
        <div className="portfolio-proof-grid">
          <article><span>01</span><h3>Cross-domain learning</h3><p>Power-network meaning is translated into controlled information ownership, deterministic processing and reviewable system behaviour.</p><strong>Power-system context → information-system discipline</strong></article>
          <article><span>02</span><h3>Configuration-defect investigation</h3><p>Incorrect connectivity produces the wrong topology and outage consequence, a preserved failure, an exact source correction and a repeat with unchanged operating logic.</p><strong>Symptom → evidence chain → controlled cause</strong></article>
          <article><span>03</span><h3>Two layers of judgement</h3><p>Run-time assurance decides whether each action may proceed. Independent validation asks whether the completed process still matches accepted expectations—even when its source information looked coherent.</p><strong>Safe to proceed ≠ proven correct</strong></article>
        </div>
      </section>

      <section className="portfolio-section portfolio-approach" id="approach" aria-labelledby="approach-title">
        <SectionHeading eyebrow="Project lifecycle" title="Learning followed a controlled, reviewable process"><p>The demonstrator appears at the end of the process, not at the beginning.</p></SectionHeading>
        <ol className="portfolio-lifecycle">{lifecycle.map((item, index) => <li key={item}><span>{String(index + 1).padStart(2, '0')}</span><strong>{item}</strong></li>)}</ol>
        <div className="portfolio-scope-statement"><div><span>Intentional simplification</span><h3>A complete mental model was more valuable than superficial scale.</h3></div><p>The network, calculations, data architecture and integrations are extremely simplified by design. That made it possible to follow the entire conceptual information and decision chain, identify which system owns each fact, and see where real network, calculation, integration, safety, cyber, availability and governance complexity enters.</p></div>
      </section>

      <section className="portfolio-section portfolio-flow" aria-labelledby="flow-title">
        <SectionHeading eyebrow="System / operational flow" title="One dependency chain, with authority kept separate"><p>Each step is named by its purpose first, with the relevant utility-system concept underneath.</p></SectionHeading>
        <div className="portfolio-flow-grid">{operationalFlow.map(([kind, title, body], index) => <article key={title}><div><span>{String(index + 1).padStart(2, '0')}</span><small>{kind}</small></div><h3>{title}</h3><p>{body}</p>{index < operationalFlow.length - 1 && <i aria-hidden="true">→</i>}</article>)}</div>
        <div className="portfolio-authority-legend"><span>Configuration inputs</span><span>Operational observations</span><span>Calculated network state</span><span>Actions and events</span><span>Evidence and determinations</span></div>
      </section>

      <section className="portfolio-section portfolio-confidence" aria-labelledby="confidence-title">
        <SectionHeading eyebrow="Assurance and validation" title="Two checks, two different questions"><p>The distinction matters because trusted inputs can be internally consistent without being correct.</p></SectionHeading>
        <div className="portfolio-confidence-model" aria-labelledby="confidence-model-title">
          <div className="portfolio-confidence-intro"><span>Core operating model</span><h3 id="confidence-model-title">A safe-looking run is not necessarily a correct result.</h3><p>The two layers answer different questions. Together they can support each action, detect an accepted-outcome mismatch, preserve the failure and provide a traceable starting point for investigation.</p></div>
          <article><span>During the run</span><h3>Assurance</h3><strong>Can the next action proceed?</strong><p>Checks that the required configuration and observations are available, and that telemetry quality, freshness and network constraints support the action. It establishes whether the current inputs are usable; it does not prove that every trusted source value is correct.</p></article>
          <article><span>Independent check</span><h3>Validation</h3><strong>Did the operating logic produce the accepted result?</strong><p>Compares preserved checkpoints and outcomes with independently defined expectations. A mismatch can expose a seeded source error that remained internally consistent during the run, while the evidence chain supports investigation, correction and repeat.</p></article>
          <p className="portfolio-confidence-outcome"><strong>Seeded-defect example:</strong> run-time assurance passes, independent validation fails, and the preserved difference leads the investigation back to the incorrect GIS connection.</p>
        </div>
      </section>

      <section className="portfolio-section" aria-labelledby="stories-title">
        <SectionHeading eyebrow="Meaningful technical cases" title="Six decisions that carry the technical value"><p>These are the points where a simple-looking demonstrator required explicit decisions about source authority, safety, validation and evidence.</p></SectionHeading>
        <div className="portfolio-story-grid">{technicalStories.map((story) => <article key={story.marker}><span>{story.marker}</span><h3>{story.title}</h3><p>{story.body}</p><strong>{story.takeaway}</strong></article>)}</div>
        <p className="portfolio-containment"><strong>Scope containment mattered:</strong> assurance and validation improvements did not become an excuse to opportunistically redesign already accepted topology or restoration behaviour.</p>
      </section>

      <section className="portfolio-section portfolio-alignment" aria-labelledby="alignment-title">
        <SectionHeading eyebrow="Role alignment" title="Working where power-network meaning becomes system behaviour"><p>This is a starting point for supervised early-career work—not a claim to specialist or client experience.</p></SectionHeading>
        <div className="portfolio-alignment-grid"><article><span>Electrical / power context</span><ul><li>Simplified radial distribution reasoning</li><li>Switching, isolation, outage and restoration concepts</li><li>Telemetry quality and freshness</li><li>Commissioning and validation mindset</li></ul></article><article><span>Computer systems / power context</span><ul><li>Information ownership and system boundaries</li><li>Database record and lifecycle separation</li><li>Deterministic processing and APIs</li><li>Configuration control, traceability and testing</li></ul></article></div>
        <blockquote>“I am not presenting this as commercial-platform experience or specialist power expertise. I am showing how I prepared to learn and contribute to early-career tasks with stronger context, under experienced supervision.”</blockquote>
      </section>

      <section className="portfolio-section portfolio-automation" id="automation" aria-labelledby="automation-title">
        <SectionHeading eyebrow="V1 retrospective / V2 opportunities" title="What V1 revealed—and where V2 could go next"><p>A review of the validation work sits alongside possible automation opportunities. The latter are not represented as implemented V1 capabilities.</p></SectionHeading>
        <div className="portfolio-automation-layout">
          <div className="portfolio-v1-friction"><span>V1 validation retrospective</span><h3>Difficulties resolved before the final validation campaign</h3><article><strong>The written test plan was not yet an executable verdict method.</strong><p>Objectives and expected results existed, but many tests still lacked exact criteria, authoritative observation sources and a controlled method for reaching PASS or FAIL. Progress stopped rather than treating implementation-test success as validation evidence.</p></article><article><strong>One result structure could not represent every test honestly.</strong><p>Single-run, multi-run and unable-to-test cases required different treatment. Composite provenance and a separate suspended-test outcome had to be designed before the final campaign could proceed.</p></article></div>
          <div className="portfolio-v2-candidates"><span>Consolidated V2 opportunities</span><h3>Where automation could reduce friction</h3><ul><li><strong>Configuration assurance</strong><small>Compare controlled GIS packages, flag connectivity changes and trace an operational symptom back towards its likely source record.</small></li><li><strong>Validation planning</strong><small>Maintain requirement-to-test traceability, identify change impact and propose the focused regression set.</small></li><li><strong>Evidence handling</strong><small>Bind run, configuration and test identities; assemble provenance-preserving packages; generate review or client summaries only from accepted evidence.</small></li><li><strong>Reviewer assistance</strong><small>Locate candidate contradictions, missing evidence and conflicts between information authorities for accountable review.</small></li></ul></div>
        </div>
        <div className="portfolio-control-principle"><span>Control principle</span><strong>Automation can collect, compare, trace and propose.</strong><p>Accountable engineers retain authority over interpretation, baseline acceptance, corrective action and final validation.</p></div>
      </section>

      <section className="portfolio-section portfolio-transparency" aria-labelledby="transparency-title">
        <div><span className="portfolio-kicker">AI transparency</span><h2 id="transparency-title">AI support accelerated the workflow</h2></div><p>Project purpose, scope, system boundaries, validation approach and direction were deliberately set and controlled throughout. AI-supported tools accelerated parts of research organisation, drafting, implementation and review; they did not define the project or act as technical authority. Every technical result or conclusion presented here had to be supported by controlled requirements, configuration, test definitions and preserved evidence. Responsibility for the design, decisions, limitations and final presentation was not delegated.</p>
      </section>

      <section className="portfolio-section portfolio-materials" id="resources" aria-labelledby="resources-title">
        <SectionHeading eyebrow="Project resources" title="Review the common project artefact and its supporting records"><p>Supporting records include investigation and research, design brief, network model, requirements, system architecture, workflow and validation plans, controlled changes and preserved evidence. Together they make the planning, technical reasoning and review behind the demonstrator visible.</p></SectionHeading>
        <div className="portfolio-resource-grid"><ConfiguredLink href={config.releaseUrl ?? config.githubUrl}>GitHub / reviewed release</ConfiguredLink><ConfiguredLink href={config.evidenceUrl}>Evidence and technical documentation</ConfiguredLink><a className="portfolio-resource-link demo" href={config.demoUrl}>Open live demonstrator<small>Enter the simulated workspace →</small></a></div>
      </section>

      <section className="portfolio-section portfolio-limitations" aria-labelledby="limitations-title">
        <SectionHeading eyebrow="Limitations and next learning" title="What this work does not claim"><p>The value is context for learning—not equivalence to professional utility experience.</p></SectionHeading>
        <div className="portfolio-limitations-grid"><ul><li>Production-system or utility-platform equivalence</li><li>Utility-scale network, power-flow, protection, fault-level, voltage or stability fidelity</li><li>Commercial platform configuration knowledge</li></ul><ul><li>Real protocols, field devices, cyber-security accreditation or availability architecture</li><li>Control-room, commissioning or real client experience</li><li>Knowledge of any specific utility/client implementation</li></ul></div>
        <p className="portfolio-final-position">The outcome is an introductory end-to-end foundation: enough context to understand where a specific early-career task fits, ask better questions, and learn the real system, procedures and engineering judgement under experienced supervision.</p>
      </section>
    </main>

    <footer className="portfolio-footer"><div><strong>Kenneth Joshua Ebenezer</strong><p>Engineering control systems / Information systems</p></div><div><span>Fictional and simulated</span><p>No real utility data · no equipment control</p></div><a href="#top">Return to top ↑</a></footer>
  </div>
}
