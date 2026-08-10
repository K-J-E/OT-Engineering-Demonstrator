import type {
  CommandResult,
  EvidenceExportCandidate,
  EvidencePackage,
  InvestigationWorkspace,
  ValidationWorkspaceAction,
  WorkspaceAction,
  WorkspaceBootstrap,
  WorkspaceProjection,
} from './contracts'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...init?.headers },
  })
  const payload = (await response.json()) as T | { detail?: unknown }
  if (!response.ok) {
    const detail = (payload as { detail?: unknown }).detail
    const message = typeof detail === 'string'
      ? detail
      : detail === undefined
        ? `Request failed with status ${response.status}`
        : JSON.stringify(detail)
    throw new Error(message)
  }
  return payload as T
}

export interface WorkspaceApi {
  bootstrap(): Promise<WorkspaceBootstrap>
  initialise(bootstrap: WorkspaceBootstrap, actor: string, mode?: 'FORMAL' | 'EXPLORATION', faultSectionId?: string): Promise<CommandResult>
  projection(runId: string): Promise<WorkspaceProjection>
  execute(runId: string, actor: string, action: WorkspaceAction): Promise<CommandResult>
  validationAction(action: ValidationWorkspaceAction, runId: string): Promise<void>
  startInvestigation(actor: string): Promise<InvestigationWorkspace>
  investigation(failureExecutionId: string): Promise<InvestigationWorkspace>
  recordDefect(failureExecutionId: string, reviewer: string, reviewedStepIds: string[]): Promise<InvestigationWorkspace>
  recordCorrection(failureExecutionId: string, reviewer: string): Promise<InvestigationWorkspace>
  runDirectRepeat(failureExecutionId: string, actor: string): Promise<InvestigationWorkspace>
  runRegression(failureExecutionId: string, actor: string): Promise<InvestigationWorkspace>
  evidenceExportCandidates(): Promise<EvidenceExportCandidate[]>
  evidencePackages(): Promise<EvidencePackage[]>
  generateEvidencePackage(validationExecutionId: string): Promise<EvidencePackage>
}

export const workspaceApi: WorkspaceApi = {
  bootstrap: () => request<WorkspaceBootstrap>('/api/v1/workspace/bootstrap'),

  initialise: (bootstrap, actor, mode = 'FORMAL', faultSectionId) =>
    request<CommandResult>('/api/v1/runs/start', {
      method: 'POST',
      body: JSON.stringify({
        command_id: crypto.randomUUID(),
        actor,
        expected_revision: 0,
        mode,
        configuration_version: bootstrap.default_configuration_version,
        fault_section_id: mode === 'EXPLORATION' ? faultSectionId : null,
        scenario_time: bootstrap.default_scenario_time,
      }),
    }),

  projection: (runId) =>
    request<WorkspaceProjection>(`/api/v1/workspace/runs/${runId}`),

  execute: (runId, actor, action) =>
    request<CommandResult>(`/api/v1/runs/${runId}/commands`, {
      method: 'POST',
      body: JSON.stringify({
        command_id: crypto.randomUUID(),
        scenario_run_id: runId,
        actor,
        expected_revision: action.expected_revision,
        command_type: action.command_type,
        scenario_time: action.proposed_scenario_time,
        target_entity_id: action.target_entity_id,
        requested_state: action.requested_state,
        alarm_id: action.alarm_id,
        assessment_id: action.assessment_id,
      }),
    }),

  validationAction: async (action, runId) => {
    if (action.action_type === 'START_EXECUTION') {
      await request('/api/v1/validation/executions', {
        method: 'POST',
        body: JSON.stringify({ test_id: action.test_id, case_id: action.case_id, scenario_run_id: runId }),
      })
      return
    }
    if (action.validation_execution_id === null || action.checkpoint_id === null) {
      throw new Error('Backend validation action is missing its controlled identity.')
    }
    const suffix =
      action.action_type === 'CAPTURE_CHECKPOINT' ? 'checkpoints' : 'finalise'
    await request(
      `/api/v1/validation/executions/${action.validation_execution_id}/${suffix}`,
      {
        method: 'POST',
        body: JSON.stringify({ checkpoint_id: action.checkpoint_id }),
      },
    )
  },

  startInvestigation: (actor) => request<InvestigationWorkspace>('/api/v1/investigations/start', { method: 'POST', body: JSON.stringify({ actor }) }),
  investigation: (failureExecutionId) => request<InvestigationWorkspace>(`/api/v1/investigations/${failureExecutionId}`),
  recordDefect: (failureExecutionId, reviewer, reviewedStepIds) => request<InvestigationWorkspace>(`/api/v1/investigations/${failureExecutionId}/defect`, { method: 'POST', body: JSON.stringify({ reviewer, reviewed_step_ids: reviewedStepIds }) }),
  recordCorrection: (failureExecutionId, reviewer) => request<InvestigationWorkspace>(`/api/v1/investigations/${failureExecutionId}/correction`, { method: 'POST', body: JSON.stringify({ reviewer }) }),
  runDirectRepeat: (failureExecutionId, actor) => request<InvestigationWorkspace>(`/api/v1/investigations/${failureExecutionId}/direct-repeat`, { method: 'POST', body: JSON.stringify({ actor }) }),
  runRegression: (failureExecutionId, actor) => request<InvestigationWorkspace>(`/api/v1/investigations/${failureExecutionId}/regression`, { method: 'POST', body: JSON.stringify({ actor }) }),
  evidenceExportCandidates: () => request<EvidenceExportCandidate[]>('/api/v1/evidence-packages/candidates'),
  evidencePackages: () => request<EvidencePackage[]>('/api/v1/evidence-packages'),
  generateEvidencePackage: (validationExecutionId) => request<EvidencePackage>('/api/v1/evidence-packages', { method: 'POST', body: JSON.stringify({ validation_execution_id: validationExecutionId }) }),
}
