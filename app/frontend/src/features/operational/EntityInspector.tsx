import type { WorkspaceNode } from '../../api/contracts'
import { formatAge, formatKw, formatTime, humanise } from '../../components/format'

export function EntityInspector({ node }: { node: WorkspaceNode | null }) {
  if (node === null) {
    return (
      <section className="panel inspector-panel">
        <span className="eyebrow">Information authority</span>
        <h2>Entity inspector</h2>
        <p>Select an entity on the one-line to review its configured, observed and derived records separately.</p>
      </section>
    )
  }
  return (
    <section className="panel inspector-panel" aria-labelledby="inspector-title">
      <div className="panel-heading">
        <div><span className="eyebrow">Stable engineering identity</span><h2 id="inspector-title">{node.entity_id}</h2></div>
        <span className={`status-badge ${node.fault_status === 'FAULTED' ? 'danger' : 'neutral'}`}>{humanise(node.fault_status)}</span>
      </div>
      <div className="authority-columns">
        <article className="authority-card configured">
          <h3>Configured truth</h3>
          <dl>
            <div><dt>Name</dt><dd>{node.configured.name}</dd></div>
            <div><dt>Class</dt><dd>{humanise(node.configured.entity_type)}</dd></div>
            <div><dt>Feeder</dt><dd>{node.configured.feeder_id ?? 'Not feeder-owned'}</dd></div>
            <div><dt>Normal state</dt><dd>{node.configured.normal_state ?? 'Not a switching device'}</dd></div>
            <div><dt>Section load</dt><dd>{node.configured.configured_load_kw === null ? 'Not applicable' : formatKw(node.configured.configured_load_kw)}</dd></div>
            <div><dt>Customer mapping</dt><dd>{node.configured.customer_zone_id === null ? 'Not applicable' : `${node.configured.customer_zone_id} · ${node.configured.customer_count} customers`}</dd></div>
          </dl>
        </article>
        <article className="authority-card observed">
          <h3>Observed SCADA evidence</h3>
          {node.observed === null ? <p>No monitored operational point for this entity.</p> : (
            <dl>
              <div><dt>Value</dt><dd>{node.observed.value}</dd></div>
              <div><dt>Quality</dt><dd>{node.observed.quality}</dd></div>
              <div><dt>Timestamp</dt><dd>{formatTime(node.observed.timestamp)}</dd></div>
              <div><dt>Age</dt><dd>{formatAge(node.observed.age_ms)}</dd></div>
              <div><dt>Freshness</dt><dd>{node.observed.freshness}</dd></div>
              <div><dt>Validity</dt><dd>{node.observed.overall_valid ? 'VALID' : `INSUFFICIENT · ${node.observed.reason_codes.join(', ')}`}</dd></div>
            </dl>
          )}
        </article>
        <article className="authority-card derived">
          <h3>Derived engineering state</h3>
          <dl>
            <div><dt>Energisation</dt><dd>{node.derived.energised === null ? 'Not a section' : node.derived.energised ? 'ENERGISED' : 'DE-ENERGISED'}</dd></div>
            <div><dt>Source attribution</dt><dd>{node.derived.source_feeder_ids.join(', ') || node.derived.current_source_availability || 'No active source'}</dd></div>
            <div><dt>Source paths</dt><dd>{node.derived.source_path_node_ids.length === 0 ? 'None' : node.derived.source_path_node_ids.map((path) => path.join(' → ')).join(' · ')}</dd></div>
            <div><dt>Fault status</dt><dd>{humanise(node.fault_status)}</dd></div>
          </dl>
        </article>
      </div>
      <p className="evidence-boundary-note"><strong>Evidence boundary:</strong> this current projection is not an immutable validation evidence snapshot unless a controlled checkpoint captures it.</p>
    </section>
  )
}
