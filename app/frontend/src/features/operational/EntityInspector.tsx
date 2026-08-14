import type { WorkspaceNode } from '../../api/contracts'
import { formatAge, formatKw, formatTime, humanise } from '../../components/format'

export function EntityInspector({ node }: { node: WorkspaceNode | null }) {
  if (node === null) {
    return (
      <section className="panel inspector-panel">
        <span className="eyebrow">Equipment information</span>
        <h2>Selected network item</h2>
        <p>Select a section, switch, breaker or source on the diagram to compare its network record, latest telemetry and calculated operating state.</p>
      </section>
    )
  }
  return (
    <section className="panel inspector-panel" aria-labelledby="inspector-title">
      <div className="panel-heading">
        <div><span className="eyebrow">Selected network item</span><h2 id="inspector-title">{node.entity_id} · {node.configured.name}</h2></div>
        <span className={`status-badge ${node.fault_status === 'FAULTED' ? 'danger' : 'neutral'}`}>{humanise(node.fault_status)}</span>
      </div>
      <div className="authority-columns">
        <article className="authority-card configured">
          <h3>Network record</h3>
          <p>Persistent asset and connectivity information used by the network model.</p>
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
          <h3>Latest telemetry</h3>
          <p>The most recent simulated device indication, including its quality and timestamp.</p>
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
          <h3>Calculated operating state</h3>
          <p>The present energisation and supply path calculated from connectivity and switch positions.</p>
          <dl>
            <div><dt>Energisation</dt><dd>{node.derived.energised === null ? 'Not a section' : node.derived.energised ? 'ENERGISED' : 'DE-ENERGISED'}</dd></div>
            <div><dt>Source attribution</dt><dd>{node.derived.source_feeder_ids.join(', ') || node.derived.current_source_availability || 'No active source'}</dd></div>
            <div><dt>Source paths</dt><dd>{node.derived.source_path_node_ids.length === 0 ? 'None' : node.derived.source_path_node_ids.map((path) => path.join(' → ')).join(' · ')}</dd></div>
            <div><dt>Fault status</dt><dd>{humanise(node.fault_status)}</dd></div>
          </dl>
        </article>
      </div>
      <p className="evidence-boundary-note"><strong>Current view:</strong> these values update as the scenario changes. They become a saved validation record only when the reviewer captures a checkpoint.</p>
    </section>
  )
}
