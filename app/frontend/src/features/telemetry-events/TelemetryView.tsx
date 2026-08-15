import type { WorkspaceProjection } from '../../api/contracts'
import { formatAge, formatTime, humanise } from '../../components/format'

export function TelemetryView({ projection, focusEntityIds, onContinue }: { projection: WorkspaceProjection; focusEntityIds?: string[]; onContinue?: () => void }) {
  const telemetryRows = focusEntityIds === undefined
    ? projection.telemetry
    : projection.telemetry.filter((row) => focusEntityIds.includes(row.entity_id))
  return (
    <div className="view-stack">
      <section className="panel telemetry-panel" aria-labelledby="telemetry-title">
        <div className="panel-heading">
          <div><span className="eyebrow">Latest simulated device signals</span><h2 id="telemetry-title">Can these telemetry readings be trusted?</h2></div>
          <p>Current scenario time: <strong>{formatTime(projection.run.scenario_time)}</strong></p>
        </div>
        <div className="callout neutral"><strong>Quality and age answer different questions.</strong> GOOD means the signal arrived without a quality warning. FRESH means its timestamp is recent enough for the decision. A GOOD reading can therefore still be unusable when it is STALE.</div>
        <div className="table-scroll"><table>
          <thead><tr><th>Point / device</th><th>Observed value</th><th>Quality</th><th>Timestamp</th><th>Age</th><th>Freshness</th><th>Overall validity</th><th>Reason / deficiency</th></tr></thead>
          <tbody>{telemetryRows.map((row) => <tr key={row.point_id}>
            <th scope="row">{row.point_id}{row.entity_id !== row.point_id && <small>{row.entity_id}</small>}</th>
            <td>{row.value}</td>
            <td><span className={`status-badge quality-${row.quality.toLowerCase()}`}>{row.quality}</span></td>
            <td>{formatTime(row.timestamp)}</td><td>{formatAge(row.age_ms)}</td>
            <td><span className={`status-badge freshness-${row.freshness.toLowerCase()}`}>{humanise(row.freshness)}</span></td>
            <td>{row.overall_valid ? 'VALID' : 'INSUFFICIENT'}</td>
            <td>{row.reason_codes.length === 0 ? 'None' : row.reason_codes.map(humanise).join(' · ')}</td>
          </tr>)}</tbody>
        </table></div>
        {onContinue !== undefined && <div className="guided-continuation"><div><strong>Telemetry evidence reviewed</strong><p>Continue to see whether withholding the switching authority was the expected validated behaviour.</p></div><button type="button" className="primary-action" onClick={onContinue}>Review safety result</button></div>}
      </section>
      <section className="panel" aria-labelledby="alarm-title">
        <div className="panel-heading"><div><span className="eyebrow">Alarm status</span><h2 id="alarm-title">Current alarms</h2></div><p>Acknowledging an alarm records that it was seen; it does not change network connectivity.</p></div>
        {projection.alarms.length === 0 ? <p className="empty-state">No alarm records exist in this run.</p> : <div className="record-list">{projection.alarms.map((alarm) => <article key={alarm.alarm_id}>
          <div><span className="status-badge warning">{alarm.active ? 'ACTIVE' : 'INACTIVE'}</span><span className="status-badge neutral">{alarm.acknowledgement_state}</span></div>
          <h3>{humanise(alarm.alarm_type)} · {alarm.entity_id}</h3>
          <dl><div><dt>Alarm ID</dt><dd>{alarm.alarm_id}</dd></div><div><dt>Generated</dt><dd>{formatTime(alarm.generated_scenario_time)}</dd></div><div><dt>Acknowledged</dt><dd>{alarm.acknowledged_scenario_time === null ? 'Not acknowledged' : `${formatTime(alarm.acknowledged_scenario_time)} by ${alarm.acknowledged_by}`}</dd></div></dl>
        </article>)}</div>}
      </section>
    </div>
  )
}
