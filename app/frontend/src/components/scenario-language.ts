import type { WorkspaceAction } from '../api/contracts'

export const checkpointMeaning: Record<string, string> = {
  N0: 'Normal network — no active fault',
  N1: 'Fault active — affected feeder tripped',
  N2: 'Fault isolated — boundary switches open',
  N3: 'Healthy upstream section restored',
  N4: 'Alternate supply assessed',
  N5: 'Eligible healthy sections restored',
}

export function checkpointLabel(checkpoint: string): string {
  const meaning = checkpointMeaning[checkpoint]
  return meaning === undefined ? checkpoint : `${checkpoint} · ${meaning}`
}

export function actionTitle(action: WorkspaceAction, faultSectionId: string): string {
  switch (action.command_type) {
    case 'INITIATE_FAULT': return `Start simulated fault at ${faultSectionId}`
    case 'ACKNOWLEDGE_ALARM': return 'Review and acknowledge the feeder-trip alarm'
    case 'OPERATE_ISOLATION_DEVICE': return `Open ${action.target_entity_id ?? 'boundary switch'} to isolate ${faultSectionId}`
    case 'RESTORE_NORMAL_SOURCE': return `Reclose ${action.target_entity_id ?? 'the feeder breaker'} to restore the healthy upstream section`
    case 'ASSESS_RESTORATION': return 'Check alternate supply for healthy de-energised sections'
    case 'EXECUTE_RESTORATION': return 'Restore eligible healthy sections from the alternate feeder'
    case 'RESET_RUN': return 'Start a new clean scenario'
  }
}

export function actionExplanation(action: WorkspaceAction): string {
  if (action.available) {
    switch (action.command_type) {
      case 'INITIATE_FAULT': return 'Ready to create the simulated section fault and feeder trip.'
      case 'ACKNOWLEDGE_ALARM': return 'Open the event record, confirm the feeder-trip alarm, then acknowledge it.'
      case 'OPERATE_ISOLATION_DEVICE': return 'This is the next switch required to establish an open boundary around the fault.'
      case 'RESTORE_NORMAL_SOURCE': return 'Both fault boundaries are confirmed open, so the healthy upstream section can be safely resupplied.'
      case 'ASSESS_RESTORATION': return 'Review the proposed alternate path, telemetry, radiality and feeder capacity before running the assessment.'
      case 'EXECUTE_RESTORATION': return 'The assessment is permitted. Review it before closing the tie switch in the simulation.'
      case 'RESET_RUN': return 'Close this run, preserve its events and evidence, and start from the normal network state in a separate run.'
    }
  }
  switch (action.command_type) {
    case 'INITIATE_FAULT': return 'Unavailable because this scenario already has an active fault or has progressed beyond the normal starting condition.'
    case 'ACKNOWLEDGE_ALARM': return 'No active feeder-trip alarm is currently waiting for acknowledgement.'
    case 'OPERATE_ISOLATION_DEVICE': return 'Available after the fault starts, the feeder-trip alarm is acknowledged, and this switch becomes the next required isolation boundary.'
    case 'RESTORE_NORMAL_SOURCE': return 'Available after both boundary switches have trustworthy open indications and no energised path reaches the fault.'
    case 'ASSESS_RESTORATION': return 'Available after the fault is isolated and the healthy upstream section has been resupplied.'
    case 'EXECUTE_RESTORATION': return 'Available only when the current alternate-supply assessment is PERMITTED.'
    case 'RESET_RUN': return 'Available when this run can be safely closed and preserved before a separate clean run begins.'
  }
}

export function actionDestination(action: WorkspaceAction): 'events' | 'restoration' | null {
  if (action.command_type === 'ACKNOWLEDGE_ALARM') return 'events'
  if (action.command_type === 'ASSESS_RESTORATION' || action.command_type === 'EXECUTE_RESTORATION') return 'restoration'
  return null
}
