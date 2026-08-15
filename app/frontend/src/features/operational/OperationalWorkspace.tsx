import { useCallback, useMemo, useState } from 'react'
import type { WorkspaceAction, WorkspaceProjection } from '../../api/contracts'
import { NetworkOneLine } from '../../components/network/NetworkOneLine'
import { formatKw, humanise } from '../../components/format'
import { ActionPanel } from './ActionPanel'
import { EntityInspector } from './EntityInspector'
import { ExplorationRunSelector } from './ExplorationRunSelector'

export function OperationalWorkspace({
  projection,
  busyActionId,
  onExecute,
  onStartNewRun,
  runControlLabel = 'Start a new clean scenario',
  runControlDescription,
  correctedRepeatReady = false,
  alarmReviewPending = false,
  safetyEvidenceBlocked = false,
  onRunCorrectedScenario,
  explorationSectionIds,
  onStartExploration,
  onNavigate,
}: {
  projection: WorkspaceProjection
  busyActionId: string | null
  onExecute: (action: WorkspaceAction) => void
  onStartNewRun: () => void
  runControlLabel?: string
  runControlDescription?: string
  correctedRepeatReady?: boolean
  alarmReviewPending?: boolean
  safetyEvidenceBlocked?: boolean
  onRunCorrectedScenario?: () => void
  explorationSectionIds?: string[]
  onStartExploration?: (sectionId: string) => void
  onNavigate: (view: 'events' | 'restoration' | 'telemetry') => void
}) {
  const [selectedEntityId, setSelectedEntityId] = useState<string | null>(projection.run.fault_section_id)
  const onSelect = useCallback((entityId: string) => setSelectedEntityId(entityId), [])
  const selected = useMemo(
    () => projection.network_nodes.find((node) => node.entity_id === selectedEntityId) ?? null,
    [projection.network_nodes, selectedEntityId],
  )
  const resetAction = projection.allowed_actions.find((action) => action.command_type === 'RESET_RUN')
  const canStartNewRun = resetAction?.available === true || projection.run.status === 'CLOSED'
  return (
    <div className="view-stack">
      <section className="summary-grid" aria-label="Current network summary">
        <article><span className="eyebrow">Affected customers</span><strong data-testid="affected-customers">{projection.summary.affected_customer_count}</strong><small>{projection.summary.de_energised_section_ids.join(', ') || 'No de-energised sections'}</small></article>
        <article><span className="eyebrow">Customers just restored</span><strong data-testid="restored-customers">{projection.summary.restored_customer_delta}</strong><small>Change since the previous scenario step</small></article>
        <article><span className="eyebrow">Active alarms</span><strong>{projection.summary.active_alarm_count}</strong><small>{projection.summary.unacknowledged_alarm_count} awaiting acknowledgement</small></article>
        <article><span className="eyebrow">Alternate-supply check</span><strong>{humanise(projection.summary.current_assessment_status)}</strong><small>{projection.summary.current_assessment_id ?? 'Not yet run'}</small></article>
        {resetAction !== undefined && <article className="summary-run-control"><span className="eyebrow">Run control</span>{correctedRepeatReady && onRunCorrectedScenario !== undefined ? <><button type="button" className="corrected-run-action" disabled={busyActionId !== null} onClick={onRunCorrectedScenario}>{busyActionId === 'RUN_CORRECTED_SCENARIO' ? 'Running corrected scenario…' : 'Run corrected full scenario'}</button><small>Repeats the complete six-stage sequence automatically, then opens the assurance and validation result. Or continue the sequence manually using the action cards below.</small></> : explorationSectionIds !== undefined && onStartExploration !== undefined ? <><ExplorationRunSelector sectionIds={explorationSectionIds} currentSectionId={projection.run.fault_section_id} busy={busyActionId !== null} onStart={onStartExploration} idPrefix="operational-exploration" /><small>Starts a separate clean run and preserves this run in history. Select {projection.run.fault_section_id} again to repeat the same scenario.</small></> : <><button type="button" disabled={!canStartNewRun || busyActionId !== null} onClick={onStartNewRun}>{busyActionId === resetAction.action_id || busyActionId === 'INITIALISE_RUN' ? 'Opening walkthrough selection…' : runControlLabel}</button><small>{runControlDescription ?? (projection.run.status === 'CLOSED' ? 'Starts a fresh run; this completed run remains preserved in history.' : 'Preserves this run, then returns the network to a separate clean starting state.')}</small></>}</article>}
      </section>

      {correctedRepeatReady && <section className="panel corrected-network-banner" aria-labelledby="corrected-network-title"><div><span className="eyebrow">Corrected configuration loaded</span><h2 id="corrected-network-title">Review the v1.1 topology before the full repeat</h2><p>The focused post-trip comparison passed at 850 affected customers. The diagram below now uses the corrected GIS endpoint. Continue manually with the available action cards, or use “Run corrected full scenario” to complete all six stages automatically.</p></div><span className="status-badge success">Focused check PASS</span></section>}

      <section className="operational-workbench" aria-label="Network and guided actions">
        <NetworkOneLine nodes={projection.network_nodes} edges={projection.network_edges} selectedEntityId={selectedEntityId} onSelect={onSelect} />
        <ActionPanel actions={projection.allowed_actions} faultSectionId={projection.run.fault_section_id} busyActionId={busyActionId} alarmReviewPending={alarmReviewPending} safetyEvidenceBlocked={safetyEvidenceBlocked} onExecute={onExecute} onNavigate={onNavigate} />
      </section>

      <EntityInspector node={selected} />

      {projection.isolation_proof !== null && <section className="panel isolation-panel" aria-labelledby="isolation-title">
        <div className="panel-heading"><div><span className="eyebrow">Fault isolation check</span><h2 id="isolation-title">Can the faulted section be safely separated from supply?</h2></div><span className={`status-badge ${projection.isolation_proof.isolated ? 'success' : 'warning'}`}>{projection.isolation_proof.isolated ? 'FAULT ISOLATED' : 'ISOLATION NOT YET CONFIRMED'}</span></div>
        <p>Each boundary switch must indicate <strong>OPEN</strong>, the signal must have acceptable <strong>quality</strong>, and its timestamp must be <strong>fresh</strong> enough to trust for switching decisions.</p>
        <div className="boundary-grid">{projection.isolation_proof.boundary_evaluations.map((item) => <article key={item.boundary_device_id}>
          <h3>{item.boundary_device_id} · boundary switch</h3>
          <strong>{item.proof_status === 'PROVEN_OPEN' ? 'Open position confirmed' : 'Open position not confirmed'}</strong>
          <dl>
            <div><dt>Switch position</dt><dd>{item.observed_state ?? 'No telemetry value'} — {item.observed_state === 'OPEN' ? 'the electrical boundary is open' : 'does not establish an open boundary'}</dd></div>
            <div><dt>Signal quality</dt><dd>{item.quality ?? 'Unavailable'} — {item.quality === 'GOOD' ? 'no telemetry-quality warning is present' : 'the value cannot be fully trusted'}</dd></div>
            <div><dt>Timestamp</dt><dd>{humanise(item.freshness_status ?? 'Unavailable')} — {item.freshness_status === 'FRESH' ? 'the reading is within the permitted age limit' : 'the reading is too old or invalid for this decision'}</dd></div>
          </dl>
          <p className="boundary-conclusion"><strong>Conclusion:</strong> {item.proof_status === 'PROVEN_OPEN' ? 'This open indication can be trusted for the isolation check.' : 'This switch does not yet provide trustworthy proof of an open boundary.'}</p>
        </article>)}</div>
        <p><strong>No energised path reaches the fault:</strong> {projection.isolation_proof.zero_active_source_paths ? 'Yes' : 'No'}. <strong>Every required boundary switch is confirmed open:</strong> {projection.isolation_proof.all_boundaries_proven_open ? 'Yes' : 'No'}.</p>
      </section>}

      <section className="panel feeder-panel" aria-labelledby="feeder-load-title">
        <div className="panel-heading"><div><span className="eyebrow">Feeder loading</span><h2 id="feeder-load-title">Normal rating compared with present supply</h2></div><p>Planned normal load and rated capacity remain separate from the load the current switch arrangement is supplying.</p></div>
        <div className="table-scroll"><table>
          <thead><tr><th>Feeder</th><th>Normal planned load</th><th>Rated capacity</th><th>Load currently supplied</th><th>Sections currently supplied</th><th>Calculation status</th></tr></thead>
          <tbody>{projection.feeders.map((feeder) => <tr key={feeder.feeder_id}>
            <th scope="row">{feeder.feeder_id}<small>{feeder.name}</small></th>
            <td>{formatKw(feeder.configured_normal_load_kw)}</td><td>{formatKw(feeder.configured_capacity_kw)}</td>
            <td>{formatKw(feeder.derived_currently_supplied_load_kw)}</td><td>{feeder.derived_supplied_section_ids.join(', ') || 'None'}</td>
            <td>{feeder.derived_load_attribution_complete ? 'All supplied sections accounted for' : 'Incomplete — no load value assumed'}</td>
          </tr>)}</tbody>
        </table></div>
      </section>
    </div>
  )
}
