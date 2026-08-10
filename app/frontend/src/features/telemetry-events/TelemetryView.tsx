import type { WorkspaceProjection } from '../../api/contracts'
import { formatAge, formatTime, humanise } from '../../components/format'

export function TelemetryView({ projection }: { projection: WorkspaceProjection }) {
  return (
    <div className="view-stack">
      <section className="panel telemetry-panel" aria-labelledby="telemetry-title">
        <div className="panel-heading">
          <div><span className="eyebrow">Observed SCADA evidence</span><h2 id="telemetry-title">Telemetry trustworthiness</h2></div>
          <p>Controlled scenario time: <strong>{formatTime(projection.run.scenario_time)}</strong></p>
        </div>
        <div className="callout neutral"><strong>Independent dimensions:</strong> quality and freshness remain separate. A GOOD value can still be STALE; future timestamps are INVALID_TIMESTAMP rather than silently clamped.</div>
        <div className="table-scroll"><table>
          <thead><tr><th>Point / device</th><th>Observed value</th><th>Quality</th><th>Timestamp</th><th>Age</th><th>Freshness</th><th>Overall validity</th><th>Reason / deficiency</th></tr></thead>
          <tbody>{projection.telemetry.map((row) => <tr key={row.point_id}>
            <th scope="row">{row.point_id}<small>{row.entity_id}</small></th>
            <td>{row.value}</td>
            <td><span className={`status-badge quality-${row.quality.toLowerCase()}`}>{row.quality}</span></td>
            <td>{formatTime(row.timestamp)}</td><td>{formatAge(row.age_ms)}</td>
            <td><span className={`status-badge freshness-${row.freshness.toLowerCase()}`}>{humanise(row.freshness)}</span></td>
            <td>{row.overall_valid ? 'VALID' : 'INSUFFICIENT'}</td>
            <td>{row.reason_codes.length === 0 ? 'None' : row.reason_codes.map(humanise).join(' · ')}</td>
          </tr>)}</tbody>
        </table></div>
      </section>
      <section className="panel" aria-labelledby="alarm-title">
        <div className="panel-heading"><div><span className="eyebrow">Alarm lifecycle</span><h2 id="alarm-title">Current alarms</h2></div><p>Acknowledgement is a controlled action and does not create a topology revision.</p></div>
        {projection.alarms.length === 0 ? <p className="empty-state">No alarm records exist in this run.</p> : <div className="record-list">{projection.alarms.map((alarm) => <article key={alarm.alarm_id}>
          <div><span className="status-badge warning">{alarm.active ? 'ACTIVE' : 'INACTIVE'}</span><span className="status-badge neutral">{alarm.acknowledgement_state}</span></div>
          <h3>{humanise(alarm.alarm_type)} · {alarm.entity_id}</h3>
          <dl><div><dt>Alarm ID</dt><dd>{alarm.alarm_id}</dd></div><div><dt>Generated</dt><dd>{formatTime(alarm.generated_scenario_time)}</dd></div><div><dt>Acknowledged</dt><dd>{alarm.acknowledged_scenario_time === null ? 'Not acknowledged' : `${formatTime(alarm.acknowledged_scenario_time)} by ${alarm.acknowledged_by}`}</dd></div></dl>
        </article>)}</div>}
      </section>
    </div>
  )
}
