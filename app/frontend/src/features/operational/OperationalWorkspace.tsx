import { useCallback, useMemo, useState } from 'react'
import type { WorkspaceAction, WorkspaceProjection } from '../../api/contracts'
import { NetworkOneLine } from '../../components/network/NetworkOneLine'
import { formatKw, humanise } from '../../components/format'
import { ActionPanel } from './ActionPanel'
import { EntityInspector } from './EntityInspector'

export function OperationalWorkspace({
  projection,
  busyActionId,
  onExecute,
}: {
  projection: WorkspaceProjection
  busyActionId: string | null
  onExecute: (action: WorkspaceAction) => void
}) {
  const [selectedEntityId, setSelectedEntityId] = useState<string | null>(null)
  const onSelect = useCallback((entityId: string) => setSelectedEntityId(entityId), [])
  const selected = useMemo(
    () => projection.network_nodes.find((node) => node.entity_id === selectedEntityId) ?? null,
    [projection.network_nodes, selectedEntityId],
  )
  return (
    <div className="view-stack">
      <section className="summary-grid" aria-label="Current engineering summary">
        <article><span className="eyebrow">Affected customers</span><strong data-testid="affected-customers">{projection.summary.affected_customer_count}</strong><small>{projection.summary.de_energised_section_ids.join(', ') || 'No de-energised sections'}</small></article>
        <article><span className="eyebrow">Restored this revision</span><strong data-testid="restored-customers">{projection.summary.restored_customer_delta}</strong><small>Identity-derived customer-zone transition</small></article>
        <article><span className="eyebrow">Topology</span><strong>{humanise(projection.summary.radiality_status)}</strong><small>Derived by ADMS Topology function</small></article>
        <article><span className="eyebrow">Alarms</span><strong>{projection.summary.active_alarm_count}</strong><small>{projection.summary.unacknowledged_alarm_count} unacknowledged</small></article>
        <article><span className="eyebrow">Restoration assessment</span><strong>{humanise(projection.summary.current_assessment_status)}</strong><small>{projection.summary.current_assessment_id ?? 'No assessment ID'}</small></article>
      </section>
      <NetworkOneLine nodes={projection.network_nodes} edges={projection.network_edges} selectedEntityId={selectedEntityId} onSelect={onSelect} />
      <section className="panel feeder-panel" aria-labelledby="feeder-load-title">
        <div className="panel-heading"><div><span className="eyebrow">QA-003 information separation</span><h2 id="feeder-load-title">Configured and derived feeder loading</h2></div><p>Configured normal load is never relabelled as currently supplied load.</p></div>
        <div className="table-scroll"><table>
          <thead><tr><th>Feeder</th><th>Configured normal load</th><th>Configured capacity</th><th>Derived currently supplied load</th><th>Derived supplied sections</th><th>Attribution</th></tr></thead>
          <tbody>{projection.feeders.map((feeder) => <tr key={feeder.feeder_id}>
            <th scope="row">{feeder.feeder_id}<small>{feeder.name}</small></th>
            <td>{formatKw(feeder.configured_normal_load_kw)}</td><td>{formatKw(feeder.configured_capacity_kw)}</td>
            <td>{formatKw(feeder.derived_currently_supplied_load_kw)}</td><td>{feeder.derived_supplied_section_ids.join(', ') || 'None'}</td>
            <td>{feeder.derived_load_attribution_complete ? 'Complete' : 'Incomplete — no fabricated load'}</td>
          </tr>)}</tbody>
        </table></div>
      </section>
      <EntityInspector node={selected} />
      {projection.isolation_proof !== null && <section className="panel isolation-panel" aria-labelledby="isolation-title">
        <div className="panel-heading"><div><span className="eyebrow">DC-003 backend proof</span><h2 id="isolation-title">Active-fault incident boundaries</h2></div><span className={`status-badge ${projection.isolation_proof.isolated ? 'success' : 'warning'}`}>{projection.isolation_proof.isolated ? 'ISOLATED' : 'NOT PROVEN'}</span></div>
        <div className="boundary-grid">{projection.isolation_proof.boundary_evaluations.map((item) => <article key={item.boundary_device_id}>
          <h3>{item.boundary_device_id}</h3><strong>{humanise(item.proof_status)}</strong><p>{item.observed_state ?? 'No observed value'} · {item.quality ?? 'No quality'} · {item.freshness_status ?? 'No freshness'}</p><small>{item.reason_codes.map(humanise).join(' · ')}</small>
        </article>)}</div>
        <p>Zero active source paths: <strong>{projection.isolation_proof.zero_active_source_paths ? 'YES' : 'NO'}</strong>. All boundaries proven open: <strong>{projection.isolation_proof.all_boundaries_proven_open ? 'YES' : 'NO'}</strong>.</p>
      </section>}
      <ActionPanel actions={projection.allowed_actions} busyActionId={busyActionId} onExecute={onExecute} />
    </div>
  )
}
