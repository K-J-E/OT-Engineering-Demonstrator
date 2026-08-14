import type { WorkspaceProjection } from '../../api/contracts'

export function SafetyValidationResult({ projection, onReturn }: { projection: WorkspaceProjection; onReturn: () => void }) {
  const staleBoundaries = projection.telemetry.filter((item) => ['SW-A12', 'SW-A23'].includes(item.entity_id) && item.freshness === 'STALE')
  const isolationAvailable = projection.allowed_actions.some((item) => item.command_type === 'OPERATE_ISOLATION_DEVICE' && item.available)
  const safe = staleBoundaries.length === 2 && !isolationAvailable
  return <div className="view-stack">
    <section className="panel" aria-labelledby="safety-result-title">
      <div className="panel-heading"><div><span className="eyebrow">Safety-case result</span><h2 id="safety-result-title">The application withheld unsafe switching authority</h2></div><span className={`status-badge ${safe ? 'success' : 'failure'}`}>{safe ? 'Expected behaviour confirmed' : 'Review required'}</span></div>
      <p>This negative case uses the same separation as the defect story. Operational assurance does not need to reach a switching action to be successful: its correct response to insufficient evidence is to stop.</p>
      <div className="assurance-validation-outcome both-pass"><article className="outcome-pass"><span>Operational assurance</span><strong>WITHHELD</strong><p>Both boundary readings report GOOD quality, but their timestamps are stale. Isolation cannot be proven, so the switching actions remain unavailable.</p></article><div className="outcome-separator" aria-hidden="true">+</div><article className={safe ? 'outcome-pass' : 'outcome-fail'}><span>System validation</span><strong>{safe ? 'PASS' : 'FAIL'}</strong><p>The accepted safety expectation requires stale evidence to prevent an isolation command from becoming available.</p></article></div>
      <div className="comparison-outcomes"><article><span>Signal quality</span><strong>GOOD</strong><p>No device-quality warning was reported.</p></article><article><span>Timestamp freshness</span><strong>STALE</strong><p>The values are too old for a current switching decision.</p></article><article><span>Switching authority</span><strong>NOT AVAILABLE</strong><p>The conservative control rule operated as designed.</p></article></div>
      <div className="hidden-defect-explanation"><strong>The important distinction</strong><p>“Blocked” is the operating outcome; “PASS” is the validation verdict on that outcome. Validation confirms that the assurance mechanism refused to act when its evidence was insufficient.</p></div>
      <button type="button" className="secondary-action" onClick={onReturn}>Return to stale telemetry evidence</button>
    </section>
  </div>
}
