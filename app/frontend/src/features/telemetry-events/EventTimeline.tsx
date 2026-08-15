import type { OperationalEvent, WorkspaceAction, WorkspaceProjection } from '../../api/contracts'
import { formatTime, humanise, shortId } from '../../components/format'

const journeySteps = [
  { label: 'Walkthrough started', checkpoint: 0 },
  { label: 'Fault applied and feeder tripped', checkpoint: 1 },
  { label: 'Feeder-trip alarm reviewed', checkpoint: 1, acknowledgement: true },
  { label: 'Fault isolated from supply', checkpoint: 2 },
  { label: 'Healthy upstream section restored', checkpoint: 3 },
  { label: 'Alternate supply assessed', checkpoint: 4 },
  { label: 'Eligible healthy sections restored', checkpoint: 5 },
]

const visibleEventTypes = new Set([
  'SCENARIO_INITIALISED', 'FAULT_INITIATED', 'ALARM_GENERATED', 'ALARM_ACKNOWLEDGED',
  'SWITCHING_ACTION', 'RESTORATION_ASSESSED', 'RESTORATION_ASSESSMENT_INVALIDATED', 'SCENARIO_RESET',
])

function eventTitle(event: OperationalEvent): string {
  switch (event.event_type) {
    case 'SCENARIO_INITIALISED': return 'Walkthrough started'
    case 'FAULT_INITIATED': return 'Simulated fault applied'
    case 'ALARM_GENERATED': return 'Feeder-trip alarm created'
    case 'ALARM_ACKNOWLEDGED': return 'Feeder-trip alarm acknowledged'
    case 'SWITCHING_ACTION': return event.new_value === 'OPEN' ? `Opened ${event.affected_entity_id}` : `Closed ${event.affected_entity_id}`
    case 'RESTORATION_ASSESSED': return 'Alternate supply assessed'
    case 'RESTORATION_ASSESSMENT_INVALIDATED': return 'Earlier restoration assessment expired'
    case 'SCENARIO_RESET': return 'New scenario run started'
    default: return humanise(event.event_type)
  }
}

export function EventTimeline({ projection, busyActionId, onExecute, onContinue, continueLabel = 'Continue to fault isolation' }: { projection: WorkspaceProjection; busyActionId: string | null; onExecute: (action: WorkspaceAction) => void; onContinue: () => void; continueLabel?: string }) {
  const acknowledgeAction = projection.allowed_actions.find((item) => item.command_type === 'ACKNOWLEDGE_ALARM')
  const activeAlarm = projection.alarms.find((alarm) => alarm.active)
  const alarmAcknowledged = projection.alarms.some((alarm) => alarm.acknowledgement_state === 'ACKNOWLEDGED')
  const checkpoint = Number(projection.run.network_state_label.slice(1)) || 0
  const milestoneEvents = projection.events.filter((event) => visibleEventTypes.has(event.event_type))
  const technicalEvents = projection.events.filter((event) => !visibleEventTypes.has(event.event_type))
  return (
    <div className="view-stack">
      <section className="panel alarm-review" aria-labelledby="alarm-review-title">
        <div className="panel-heading"><div><span className="eyebrow">Feeder-trip alarm</span><h2 id="alarm-review-title">Review before acknowledging</h2></div><span className={`status-badge ${activeAlarm?.acknowledgement_state === 'ACKNOWLEDGED' ? 'success' : 'warning'}`}>{activeAlarm?.acknowledgement_state ?? 'NO ACTIVE ALARM'}</span></div>
        {activeAlarm === undefined ? <p>No active feeder-trip alarm exists for this scenario.</p> : <>
          <p>The simulated fault tripped <strong>{activeAlarm.entity_id}</strong> and created this alarm at <strong>{formatTime(activeAlarm.generated_scenario_time)}</strong>. Acknowledging confirms that the reviewer has seen the alarm; it does not restore supply or change any switch position.</p>
          <dl className="identity-grid"><div><dt>Alarm</dt><dd>{humanise(activeAlarm.alarm_type)}</dd></div><div><dt>Equipment</dt><dd>{activeAlarm.entity_id}</dd></div><div><dt>Status</dt><dd>{humanise(activeAlarm.acknowledgement_state)}</dd></div></dl>
        </>}
        {acknowledgeAction?.available && <button type="button" className="primary-action" disabled={busyActionId !== null} onClick={() => onExecute(acknowledgeAction)}>Acknowledge this feeder-trip alarm</button>}
        {activeAlarm?.acknowledgement_state === 'ACKNOWLEDGED' && <button type="button" className="primary-action" onClick={onContinue}>{continueLabel}</button>}
      </section>

      <section className="panel" aria-labelledby="journey-title">
        <div className="panel-heading"><div><span className="eyebrow">Scenario progress</span><h2 id="journey-title">What has happened so far</h2></div><p>Completed steps are coloured; later steps are grey.</p></div>
        <ol className="journey-timeline">{journeySteps.map((step, index) => {
          const complete = step.acknowledgement ? alarmAcknowledged : checkpoint >= step.checkpoint
          const previousComplete = index === 0 || (journeySteps[index - 1]?.acknowledgement ? alarmAcknowledged : checkpoint >= (journeySteps[index - 1]?.checkpoint ?? 0))
          const status = complete ? 'completed' : previousComplete ? 'current' : 'pending'
          return <li className={status} key={step.label}><span aria-hidden="true">{complete ? '✓' : index + 1}</span><div><strong>{step.label}</strong><small>{complete ? 'Completed' : status === 'current' ? 'Next step' : 'Not reached yet'}</small></div></li>
        })}</ol>
      </section>

      <section className="panel" aria-labelledby="event-title">
        <div className="panel-heading"><div><span className="eyebrow">Operator-visible history</span><h2 id="event-title">Actions and decisions already recorded</h2></div><p>{milestoneEvents.length} completed records · earliest to latest</p></div>
        {milestoneEvents.length === 0 ? <p className="empty-state">No operator-visible actions have occurred yet.</p> : <ol className="event-timeline">{milestoneEvents.map((event, index) => <li key={event.event_id}>
          <div className="event-sequence">{index + 1}</div>
          <article>
            <div className="event-meta"><span>{formatTime(event.scenario_time)}</span><span>{event.actor === null ? 'System record' : `Performed by ${event.actor}`}</span></div>
            <h3>{eventTitle(event)}</h3><p>{event.description}</p>
            {event.affected_entity_id !== null && <div className="event-values"><span>Equipment: {event.affected_entity_id}</span>{event.previous_value !== null && <span>{event.previous_value} → {event.new_value ?? '—'}</span>}</div>}
          </article>
        </li>)}</ol>}
        {technicalEvents.length > 0 && <details className="technical-details"><summary>{technicalEvents.length} supporting system records</summary><p>These topology, telemetry and outage recalculations happened automatically in support of the completed actions above.</p><ul>{technicalEvents.map((event) => <li key={event.event_id}><strong>{humanise(event.event_type)}</strong> · {formatTime(event.scenario_time)} · sequence {event.event_sequence} · revision {event.state_revision} · source {humanise(event.source)} · record {shortId(event.event_id)}</li>)}</ul></details>}
      </section>
    </div>
  )
}
