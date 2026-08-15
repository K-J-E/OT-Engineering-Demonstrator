import { useEffect, useRef } from 'react'
import type { WorkspaceAction } from '../../api/contracts'
import { formatTime } from '../../components/format'
import { actionDestination, actionExplanation, actionTitle } from '../../components/scenario-language'

export function ActionPanel({
  actions,
  faultSectionId,
  busyActionId,
  alarmReviewPending = false,
  safetyEvidenceBlocked = false,
  onExecute,
  onNavigate,
}: {
  actions: WorkspaceAction[]
  faultSectionId: string
  busyActionId: string | null
  alarmReviewPending?: boolean
  safetyEvidenceBlocked?: boolean
  onExecute: (action: WorkspaceAction) => void
  onNavigate: (view: 'events' | 'restoration' | 'telemetry') => void
}) {
  const guidedActions = actions.filter((action) => action.command_type !== 'RESET_RUN')
  const actionListRef = useRef<HTMLDivElement | null>(null)
  const actionButtonRefs = useRef(new Map<string, HTMLButtonElement>())
  const nextAvailableActionId = guidedActions.find((action) => action.available && !(alarmReviewPending && action.command_type === 'OPERATE_ISOLATION_DEVICE'))?.action_id ?? null

  useEffect(() => {
    const actionList = actionListRef.current
    const nextAction = nextAvailableActionId === null ? null : actionButtonRefs.current.get(nextAvailableActionId)
    if (actionList === null || nextAction === null || nextAction === undefined) return

    const listBounds = actionList.getBoundingClientRect()
    const actionBounds = nextAction.getBoundingClientRect()
    if (actionBounds.top < listBounds.top || actionBounds.bottom > listBounds.bottom) {
      actionList.scrollTop += actionBounds.top - listBounds.top - 4
    }
  }, [nextAvailableActionId])

  return (
    <section className="panel action-panel" aria-labelledby="actions-title">
      <div className="panel-heading">
        <div><span className="eyebrow">Scenario control</span><h2 id="actions-title">Operational actions</h2></div>
        <p>{safetyEvidenceBlocked ? 'The operating sequence has stopped safely. Review the stale evidence before confirming the result.' : 'Select the next available action. Review actions open the relevant evidence page before any simulated operation is applied.'}</p>
      </div>
      {safetyEvidenceBlocked && <div className="guided-continuation safety-blocked-continuation" role="status"><div><span className="eyebrow">Required safety review</span><h3>Isolation switching is intentionally unavailable</h3><p>Both boundary readings are too old to support a current switching decision. The grey operation cards show what has been withheld; continue to compare signal quality, timestamp and freshness.</p></div><button type="button" className="primary-action" onClick={() => onNavigate('telemetry')}>Review stale telemetry evidence</button></div>}
      <div className="action-list" ref={actionListRef}>
        {guidedActions.map((action, index) => {
          const destination = actionDestination(action)
          const title = actionTitle(action, faultSectionId)
          const target = action.target_entity_id
          const awaitingAlarmReview = alarmReviewPending && action.command_type === 'OPERATE_ISOLATION_DEVICE'
          const available = action.available && !awaitingAlarmReview
          const cta = destination === 'events'
            ? 'Review alarm →'
            : destination === 'restoration'
              ? 'Review restoration →'
              : 'Perform action →'
          return (
            <button
              type="button"
              className={`action-card ${available ? 'available' : 'unavailable'}`}
              key={action.action_id}
              ref={(element) => {
                if (element === null) actionButtonRefs.current.delete(action.action_id)
                else actionButtonRefs.current.set(action.action_id, element)
              }}
              aria-label={title}
              disabled={!available || busyActionId !== null}
              onClick={() => destination === null ? onExecute(action) : onNavigate(destination)}
            >
              <span className="action-step-number" aria-hidden="true">{index + 1}</span>
              <span className="action-card-content">
                <h3>{title}</h3>
                {target !== null && <p className="action-target">Equipment: {target}{action.requested_state === null ? '' : ` · requested position ${action.requested_state}`}</p>}
                <p>{awaitingAlarmReview ? 'Review and acknowledge the feeder-trip alarm before the boundary-switch evidence is evaluated.' : actionExplanation(action)}</p>
                <span className="action-time">Scenario time {formatTime(action.proposed_scenario_time)}</span>
              </span>
              <span className="action-card-cta" aria-hidden="true">{busyActionId === action.action_id ? 'Applying…' : awaitingAlarmReview ? 'Review alarm first' : available ? cta : 'Not available yet'}</span>
            </button>
          )
        })}
      </div>
    </section>
  )
}
