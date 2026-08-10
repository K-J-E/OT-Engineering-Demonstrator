import type { WorkspaceAction } from '../../api/contracts'
import { formatTime, humanise } from '../../components/format'

const actionLabels: Record<WorkspaceAction['command_type'], string> = {
  INITIATE_FAULT: 'Initiate controlled fault',
  ACKNOWLEDGE_ALARM: 'Acknowledge feeder-trip alarm',
  OPERATE_ISOLATION_DEVICE: 'Open isolation device',
  RESTORE_NORMAL_SOURCE: 'Restore normal source',
  ASSESS_RESTORATION: 'Assess alternate restoration',
  EXECUTE_RESTORATION: 'Execute permitted restoration',
  RESET_RUN: 'Reset into a new run',
}

export function ActionPanel({
  actions,
  busyActionId,
  onExecute,
}: {
  actions: WorkspaceAction[]
  busyActionId: string | null
  onExecute: (action: WorkspaceAction) => void
}) {
  return (
    <section className="panel action-panel" aria-labelledby="actions-title">
      <div className="panel-heading">
        <div><span className="eyebrow">Scenario Control authority</span><h2 id="actions-title">Backend-owned actions</h2></div>
        <p>Disabled controls show the current backend reason; the browser does not evaluate eligibility.</p>
      </div>
      <div className="action-list">
        {actions.map((action) => {
          const target = action.target_entity_id ?? action.alarm_id ?? action.assessment_id
          return (
            <article className={`action-row ${action.available ? 'available' : 'unavailable'}`} key={action.action_id}>
              <div>
                <h3>{actionLabels[action.command_type]}</h3>
                <p className="action-target">
                  {target === null ? 'Run-level action' : `Target ${target}`}
                  {action.requested_state === null ? '' : ` · ${action.requested_state}`}
                </p>
                <p>{action.reason}</p>
                <span className="reason-code">{humanise(action.reason_code)}</span>
                <span className="action-time">Controlled time {formatTime(action.proposed_scenario_time)}</span>
              </div>
              <button
                type="button"
                aria-label={`${actionLabels[action.command_type]}${target === null ? '' : ` ${target}`}`}
                disabled={!action.available || busyActionId !== null}
                onClick={() => onExecute(action)}
              >
                {busyActionId === action.action_id ? 'Submitting…' : actionLabels[action.command_type]}
              </button>
            </article>
          )
        })}
      </div>
    </section>
  )
}
