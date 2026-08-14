import type { WorkspaceAction } from '../../api/contracts'
import { formatTime } from '../../components/format'
import { actionDestination, actionExplanation, actionTitle } from '../../components/scenario-language'

export function ActionPanel({
  actions,
  faultSectionId,
  busyActionId,
  onExecute,
  onNavigate,
}: {
  actions: WorkspaceAction[]
  faultSectionId: string
  busyActionId: string | null
  onExecute: (action: WorkspaceAction) => void
  onNavigate: (view: 'events' | 'restoration') => void
}) {
  const guidedActions = actions.filter((action) => action.command_type !== 'RESET_RUN')
  return (
    <section className="panel action-panel" aria-labelledby="actions-title">
      <div className="panel-heading">
        <div><span className="eyebrow">Scenario control</span><h2 id="actions-title">Operational actions</h2></div>
        <p>Select the next available action. Review actions open the relevant evidence page before any simulated operation is applied.</p>
      </div>
      <div className="action-list">
        {guidedActions.map((action, index) => {
          const destination = actionDestination(action)
          const title = actionTitle(action, faultSectionId)
          const target = action.target_entity_id
          const cta = destination === 'events'
            ? 'Review alarm →'
            : destination === 'restoration'
              ? 'Review restoration →'
              : 'Perform action →'
          return (
            <button
              type="button"
              className={`action-card ${action.available ? 'available' : 'unavailable'}`}
              key={action.action_id}
              aria-label={title}
              disabled={!action.available || busyActionId !== null}
              onClick={() => destination === null ? onExecute(action) : onNavigate(destination)}
            >
              <span className="action-step-number" aria-hidden="true">{index + 1}</span>
              <span className="action-card-content">
                <h3>{title}</h3>
                {target !== null && <p className="action-target">Equipment: {target}{action.requested_state === null ? '' : ` · requested position ${action.requested_state}`}</p>}
                <p>{actionExplanation(action)}</p>
                <span className="action-time">Scenario time {formatTime(action.proposed_scenario_time)}</span>
              </span>
              <span className="action-card-cta" aria-hidden="true">{busyActionId === action.action_id ? 'Applying…' : action.available ? cta : 'Not available yet'}</span>
            </button>
          )
        })}
      </div>
    </section>
  )
}
