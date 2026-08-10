import type { WorkspaceProjection } from '../../api/contracts'
import { formatTime, humanise, shortId } from '../../components/format'

export function EventTimeline({ projection }: { projection: WorkspaceProjection }) {
  return (
    <section className="panel" aria-labelledby="event-title">
      <div className="panel-heading">
        <div><span className="eyebrow">Append-only operational chronology</span><h2 id="event-title">Operational events</h2></div>
        <p>{projection.events.length} records · backend event_sequence order</p>
      </div>
      <div className="callout neutral">Validation PASS/FAIL, DEF-001 and engineering-review judgement are deliberately outside this operational stream.</div>
      {projection.events.length === 0 ? <p className="empty-state">No operational events exist.</p> : <ol className="event-timeline">{projection.events.map((event) => <li key={event.event_id}>
        <div className="event-sequence">{event.event_sequence}</div>
        <article>
          <div className="event-meta"><span>{formatTime(event.scenario_time)}</span><span>Revision {event.state_revision}</span><span>{event.source}</span><span title={event.event_id}>Event {shortId(event.event_id)}</span></div>
          <h3>{humanise(event.event_type)}</h3><p>{event.description}</p>
          <div className="event-values"><span>Entity: {event.affected_entity_id ?? 'Run-level'}</span><span>{event.previous_value ?? '—'} → {event.new_value ?? '—'}</span>{event.actor !== null && <span>Actor: {event.actor}</span>}</div>
        </article>
      </li>)}</ol>}
    </section>
  )
}
