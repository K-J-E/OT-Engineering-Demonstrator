import { useCallback, useEffect, useRef, useState } from 'react'
import type { ReactNode } from 'react'
import type { InvestigationWorkspace as InvestigationModel, ValidationWorkspaceAction, WorkspaceAction, WorkspaceBootstrap, WorkspaceProjection } from './api/contracts'
import { workspaceApi, type WorkspaceApi } from './api/client'
import { ContextRibbon } from './features/operational/ContextRibbon'
import { OperationalWorkspace } from './features/operational/OperationalWorkspace'
import { RestorationView } from './features/restoration/RestorationView'
import { RunSetup } from './features/run-setup/RunSetup'
import { EventTimeline } from './features/telemetry-events/EventTimeline'
import { TelemetryView } from './features/telemetry-events/TelemetryView'
import { EvidenceLibrary } from './features/validation/EvidenceLibrary'
import { ValidationView } from './features/validation/ValidationView'
import { SafetyValidationResult } from './features/validation/SafetyValidationResult'
import { InvestigationWorkspace } from './features/investigation/InvestigationWorkspace'
import { CorrectedRunResult, DefectResults } from './features/investigation/DefectWorkflow'
import { EngineeringBasis } from './features/engineering/EngineeringBasis'
import { ControlledSurface } from './components/ControlledSurface'
import controlledSurfaces from './controlled-surfaces.v1.json'

type View = 'operational' | 'telemetry' | 'events' | 'restoration' | 'validation' | 'investigation' | 'corrected' | 'engineering'
type Experience = 'exploration' | 'investigation' | 'safety'
const RUN_STORAGE_KEY = 'ot-demo-current-run-id'
const INVESTIGATION_STORAGE_KEY = 'ot-demo-investigation-failure-id'
const EXPERIENCE_STORAGE_KEY = 'ot-demo-current-experience'

const experienceLabels: Record<Experience, string> = {
  exploration: 'Reviewer-driven trial',
  investigation: 'Validation · DEF-001 investigation',
  safety: 'Stale-telemetry safety case',
}

const navigationByExperience: Record<Experience, Array<{ id: View; label: string }>> = {
  exploration: [
    { id: 'operational', label: 'Operational' },
    { id: 'events', label: 'Events' },
    { id: 'restoration', label: 'Restoration' },
    { id: 'validation', label: 'Results & evidence' },
  ],
  investigation: [
    { id: 'operational', label: 'Defect operation' },
    { id: 'events', label: 'Events' },
    { id: 'restoration', label: 'Restoration' },
    { id: 'validation', label: 'Failed result' },
    { id: 'investigation', label: 'Investigation' },
    { id: 'corrected', label: 'Corrected repeat' },
  ],
  safety: [
    { id: 'operational', label: 'Safety case' },
    { id: 'events', label: 'Alarm review' },
    { id: 'telemetry', label: 'Telemetry evidence' },
    { id: 'validation', label: 'Safety result' },
  ],
}

const guidance: Record<Experience, Partial<Record<View, { title: string; purpose: string; notice: string }>>> = {
  exploration: {
    operational: { title: 'Run the selected fault-section trial', purpose: 'Operate the same network sequence with the selected section used as this scenario’s fault location.', notice: 'The application calculates feeder roles, isolation boundaries and outage impact for this selection; a restorable outcome is not guaranteed.' },
    events: { title: 'Review and acknowledge the feeder-trip alarm', purpose: 'Read the alarm and event sequence before acknowledging that the simulated trip has been seen.', notice: 'Acknowledging an alarm records reviewer awareness; it does not restore supply or change a switch.' },
    restoration: { title: 'Inspect the trial restoration outcome', purpose: 'Review any alternate path and safety, telemetry and capacity checks after running the assessment.', notice: 'A trial can legitimately produce PERMITTED, REJECTED, BLOCKED or no restoration candidate.' },
    validation: { title: 'Understand and export the trial result', purpose: 'See how the selected fault was checked through each operating stage, review the calculated customer and network outcomes, and create its separate evidence package.', notice: 'Trials use the same operating checks, while their records remain visibly separate from the defect-investigation validation record.' },
    engineering: { title: 'Engineering basis reference', purpose: 'Use this reference to review the configuration-driven model and trial boundaries.', notice: 'This supporting reference does not turn the selected section into controlled validation evidence.' },
  },
  investigation: {
    operational: { title: 'Operate with the seeded GIS configuration error', purpose: 'Continue the fault-isolation and restoration sequence using the v1.0 network record exactly as supplied to the operating mechanism.', notice: 'The actions can still look correct because assurance checks the current data and network model; the seeded configured connection is exposed later by independent validation.' },
    events: { title: 'Review the defect-run feeder trip', purpose: 'Inspect and acknowledge the event generated from the v1.0 run before continuing the isolation sequence.', notice: 'The alarm and telemetry are genuine and trustworthy—the defect is seeded in the configured network connection.' },
    restoration: { title: 'Complete the defect-run restoration assessment', purpose: 'Review the alternate-supply assessment produced from configuration v1.0 and preserve whether the model permits, rejects or cannot identify a restoration action.', notice: 'A defensible operating decision can still be based on a defective topology model; independent validation tests whether the overall result is actually correct.' },
    validation: { title: 'Compare live assurance with independent validation', purpose: 'See why the completed operating sequence can pass its live checks while the accepted customer-impact comparison fails.', notice: 'The mismatch is preserved rather than corrected on screen, creating the starting point for a traceable investigation.' },
    investigation: { title: 'Trace the wrong result back to its source', purpose: 'Follow the customer mismatch through trusted telemetry, topology attribution and outage arithmetic until the single GIS connection error is established.', notice: 'The investigation moves from consequence to cause; raw identities remain available only under technical traceability.' },
    corrected: { title: 'Repeat the scenario after the controlled correction', purpose: 'Use configuration v1.1 with the same application build and operating logic, then compare assurance and validation with the failed v1.0 result.', notice: 'Changing only the controlled GIS configuration demonstrates that the source record—not a hard-coded presentation—caused the original failure.' },
    engineering: { title: 'Engineering basis reference', purpose: 'Use this reference to review the accepted seeded-defect and validation boundaries.', notice: 'This is supporting context, not an editable investigation surface.' },
  },
  safety: {
    operational: { title: 'Run until stale evidence withholds switching', purpose: 'Begin from the normal network, initiate the feeder fault and acknowledge its alarm before reviewing the resulting isolation authority.', notice: 'The boundary readings retain GOOD quality but are deliberately aged during the alarm review; once STALE, they cannot authorise the isolation actions.' },
    events: { title: 'Review and acknowledge the feeder-trip alarm', purpose: 'Confirm the simulated feeder trip before the stale boundary evidence is assessed.', notice: 'Acknowledging the alarm records reviewer awareness; it does not make the stale switch indications trustworthy.' },
    telemetry: { title: 'Inspect the stale evidence', purpose: 'Compare value, quality, age and freshness for the required boundary devices.', notice: 'Quality and freshness remain independent, and both switches are classified STALE / INSUFFICIENT.' },
    validation: { title: 'Confirm the conservative safety response', purpose: 'Separate the operating outcome—switching authority withheld—from the validation verdict that confirms this was the required behaviour.', notice: 'A stopped operation can be a successful safety outcome when the evidence is insufficient.' },
    engineering: { title: 'Engineering basis reference', purpose: 'Use this reference to review the conservative telemetry and switching rules.', notice: 'This is supporting context, not another safety-case action.' },
  },
}

const surfaceById = Object.fromEntries(controlledSurfaces.surfaces.map((surface) => [surface.surface_id, surface]))
const isMissingStoredRecord = (cause: unknown) => cause instanceof Error && cause.message.toLowerCase().includes('not found')

function Surface({ id, children }: { id: string; children: ReactNode }) {
  const surface = surfaceById[id]
  if (surface === undefined) throw new Error(`Controlled surface is not registered: ${id}`)
  return <ControlledSurface surfaceId={surface.surface_id} identityProfile={surface.required_identity_profile} fixedNotice={surface.fixed_notice}>{children}</ControlledSurface>
}

export function App({ api = workspaceApi }: { api?: WorkspaceApi }) {
  const [bootstrap, setBootstrap] = useState<WorkspaceBootstrap | null>(null)
  const [projection, setProjection] = useState<WorkspaceProjection | null>(null)
  const [runId, setRunId] = useState<string | null>(() => {
    if (localStorage.getItem(EXPERIENCE_STORAGE_KEY) === 'formal') {
      localStorage.removeItem(RUN_STORAGE_KEY)
      localStorage.removeItem(EXPERIENCE_STORAGE_KEY)
      return null
    }
    return localStorage.getItem(RUN_STORAGE_KEY)
  })
  const [actor, setActor] = useState('Simulated Reviewer')
  const [failureExecutionId, setFailureExecutionId] = useState<string | null>(() => localStorage.getItem(INVESTIGATION_STORAGE_KEY))
  const [initialInvestigation, setInitialInvestigation] = useState<InvestigationModel | null>(null)
  const [experience, setExperience] = useState<Experience>(() => {
    const stored = localStorage.getItem(EXPERIENCE_STORAGE_KEY)
    return stored === 'exploration' || stored === 'investigation' || stored === 'safety' ? stored : 'investigation'
  })
  const [view, setView] = useState<View>('operational')
  const [busyActionId, setBusyActionId] = useState<string | null>(null)
  const [validationBusy, setValidationBusy] = useState(false)
  const [evidenceRefreshKey, setEvidenceRefreshKey] = useState(0)
  const [error, setError] = useState<string | null>(null)
  const explorationEvidenceTasks = useRef(new Map<string, Promise<WorkspaceProjection>>())
  const guidedNavRef = useRef<HTMLElement | null>(null)

  useEffect(() => { api.bootstrap().then(setBootstrap).catch((cause: unknown) => setError(cause instanceof Error ? cause.message : 'Unable to load controlled workspace context.')) }, [api])
  useEffect(() => {
    if (experience !== 'investigation' || failureExecutionId === null || initialInvestigation !== null) return
    api.investigation(failureExecutionId).then(setInitialInvestigation).catch((cause: unknown) => {
      if (isMissingStoredRecord(cause)) {
        localStorage.removeItem(INVESTIGATION_STORAGE_KEY)
        setFailureExecutionId(null)
        setInitialInvestigation(null)
        setError(null)
        return
      }
      setError(cause instanceof Error ? cause.message : 'Unable to reload the preserved investigation.')
    })
  }, [api, experience, failureExecutionId, initialInvestigation])
  useEffect(() => {
    const frame = window.requestAnimationFrame(() => guidedNavRef.current?.scrollIntoView({ block: 'start' }))
    return () => window.cancelAnimationFrame(frame)
  }, [view, runId, experience])

  const loadProjection = useCallback(async (identity: string) => {
    const current = await api.projection(identity)
    setProjection(current)
    setRunId(identity)
    localStorage.setItem(RUN_STORAGE_KEY, identity)
    return current
  }, [api])

  async function saveExplorationEvidenceOnce(current: WorkspaceProjection, captureResult: boolean): Promise<WorkspaceProjection> {
    if (current.run.mode !== 'EXPLORATION') return current
    const testId = 'VT-EXP-ALL-001'
    let latest = current
    let summary = latest.validation.run_executions.find((item) => item.execution.test_id === testId)
    if (summary === undefined) {
      const start = latest.validation.actions.find((item) => item.test_id === testId && item.action_type === 'START_EXECUTION' && item.available)
      if (start === undefined) return latest
      await api.validationAction(start, latest.run.scenario_run_id)
      latest = await loadProjection(latest.run.scenario_run_id)
      summary = latest.validation.run_executions.find((item) => item.execution.test_id === testId)
    }
    if (!captureResult || summary === undefined) return latest
    const alreadySaved = summary.evidence_snapshots.some((item) => item.checkpoint_id === 'CONTROLLED_RESULT')
    if (!alreadySaved) {
      const capture = latest.validation.actions.find((item) => item.test_id === testId && item.action_type === 'CAPTURE_CHECKPOINT' && item.checkpoint_id === 'CONTROLLED_RESULT' && item.available)
      if (capture === undefined) return latest
      await api.validationAction(capture, latest.run.scenario_run_id)
      latest = await loadProjection(latest.run.scenario_run_id)
    }
    const finalise = latest.validation.actions.find((item) => item.test_id === testId && item.action_type === 'FINALISE_EXECUTION' && item.available)
    if (finalise !== undefined) {
      await api.validationAction(finalise, latest.run.scenario_run_id)
      latest = await loadProjection(latest.run.scenario_run_id)
    }
    return latest
  }

  function saveExplorationEvidence(current: WorkspaceProjection, captureResult: boolean): Promise<WorkspaceProjection> {
    const key = `${current.run.scenario_run_id}:${captureResult ? 'result' : 'setup'}`
    const existing = explorationEvidenceTasks.current.get(key)
    if (existing !== undefined) return existing
    const task = saveExplorationEvidenceOnce(current, captureResult).finally(() => explorationEvidenceTasks.current.delete(key))
    explorationEvidenceTasks.current.set(key, task)
    return task
  }

  async function generateClosedRunEvidence(sourceRunId: string): Promise<void> {
    const [candidates, packages] = await Promise.all([api.evidenceExportCandidates(), api.evidencePackages()])
    const packagedExecutionIds = new Set(packages.map((item) => item.validation_execution_id))
    const ready = candidates.filter((item) => item.scenario_run_id === sourceRunId && item.export_available && !packagedExecutionIds.has(item.validation_execution_id))
    for (const candidate of ready) await api.generateEvidencePackage(candidate.validation_execution_id)
    if (ready.length > 0) setEvidenceRefreshKey((current) => current + 1)
  }

  useEffect(() => {
    if (runId !== null) loadProjection(runId)
      .catch((cause: unknown) => {
        if (isMissingStoredRecord(cause)) {
          setError(null)
          setProjection(null)
          localStorage.removeItem(RUN_STORAGE_KEY)
          setRunId(null)
          return
        }
        setError(cause instanceof Error ? cause.message : 'Unable to reload the preserved run.')
      })
  }, [api, loadProjection, runId])

  async function startRun(requestedActor: string, _mode: 'FORMAL' | 'EXPLORATION' = 'EXPLORATION', faultSectionId?: string) {
    if (bootstrap === null) return
    const previousExplorationRunId = projection?.run.mode === 'EXPLORATION' ? projection.run.scenario_run_id : null
    setError(null); setBusyActionId('INITIALISE_RUN'); setActor(requestedActor)
    try {
      const result = await api.initialise(bootstrap, requestedActor, 'EXPLORATION', faultSectionId)
      setExperience('exploration'); localStorage.setItem(EXPERIENCE_STORAGE_KEY, 'exploration')
      setView('operational')
      const current = await loadProjection(result.snapshot.run.scenario_run_id)
      await saveExplorationEvidence(current, false)
      if (previousExplorationRunId !== null && previousExplorationRunId !== current.run.scenario_run_id) await generateClosedRunEvidence(previousExplorationRunId)
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Run initialisation failed.')
    } finally { setBusyActionId(null) }
  }

  async function startInvestigation(requestedActor: string) {
    setError(null); setBusyActionId('START_INVESTIGATION'); setActor(requestedActor)
    try {
      const investigation = await api.startInvestigation(requestedActor)
      const failureId = investigation.original_failure.execution.validation_execution_id
      setFailureExecutionId(failureId); setInitialInvestigation(investigation)
      localStorage.setItem(INVESTIGATION_STORAGE_KEY, failureId)
      setExperience('investigation'); localStorage.setItem(EXPERIENCE_STORAGE_KEY, 'investigation')
      await loadProjection(investigation.original_failure.execution.scenario_run_id)
      setView('operational')
    } catch (cause) { setError(cause instanceof Error ? cause.message : 'Investigation start failed.') }
    finally { setBusyActionId(null) }
  }

  async function restartDefectWalkthrough() {
    setError(null); setBusyActionId('RESTART_DEFECT_WALKTHROUGH')
    try {
      await api.resetLocalShowcase()
      localStorage.removeItem(RUN_STORAGE_KEY)
      localStorage.removeItem(INVESTIGATION_STORAGE_KEY)
      localStorage.removeItem(EXPERIENCE_STORAGE_KEY)
      explorationEvidenceTasks.current.clear()
      setProjection(null); setRunId(null); setFailureExecutionId(null); setInitialInvestigation(null)
      const investigation = await api.startInvestigation(actor)
      const failureId = investigation.original_failure.execution.validation_execution_id
      setFailureExecutionId(failureId); setInitialInvestigation(investigation)
      localStorage.setItem(INVESTIGATION_STORAGE_KEY, failureId)
      setExperience('investigation'); localStorage.setItem(EXPERIENCE_STORAGE_KEY, 'investigation')
      await loadProjection(investigation.original_failure.execution.scenario_run_id)
      setEvidenceRefreshKey((current) => current + 1)
      setView('operational')
    } catch (cause) { setError(cause instanceof Error ? cause.message : 'Unable to restart the local defect demonstration.') }
    finally { setBusyActionId(null) }
  }

  async function startSafetyWalkthrough(requestedActor: string) {
    setError(null); setBusyActionId('START_STALE_WALKTHROUGH'); setActor(requestedActor)
    try {
      if (bootstrap === null) return
      const result = await api.startStaleTelemetryWalkthrough(bootstrap, requestedActor)
      setExperience('safety'); localStorage.setItem(EXPERIENCE_STORAGE_KEY, 'safety')
      await loadProjection(result.snapshot.run.scenario_run_id)
      setView('operational')
    } catch (cause) { setError(cause instanceof Error ? cause.message : 'Safety walkthrough start failed.') }
    finally { setBusyActionId(null) }
  }

  function returnToRunSetup() {
    localStorage.removeItem(RUN_STORAGE_KEY)
    localStorage.removeItem(EXPERIENCE_STORAGE_KEY)
    setProjection(null)
    setRunId(null)
    setView('operational')
    setError(null)
  }

  async function resumeInvestigation(requestedActor: string) {
    if (failureExecutionId === null) return
    setError(null); setBusyActionId('RESUME_INVESTIGATION'); setActor(requestedActor)
    try {
      const investigation = await api.investigation(failureExecutionId)
      setInitialInvestigation(investigation)
      setExperience('investigation'); localStorage.setItem(EXPERIENCE_STORAGE_KEY, 'investigation')
      const currentRunId = investigation.regression?.execution.scenario_run_id
        ?? investigation.direct_repeat?.execution.scenario_run_id
        ?? investigation.original_failure.execution.scenario_run_id
      await loadProjection(currentRunId)
      setView(investigation.regression?.execution.status === 'FINALISED' ? 'corrected' : 'operational')
    } catch (cause) {
      localStorage.removeItem(INVESTIGATION_STORAGE_KEY)
      setFailureExecutionId(null)
      setError(cause instanceof Error ? cause.message : 'Unable to resume the preserved investigation.')
    } finally { setBusyActionId(null) }
  }

  async function investigationUpdated(investigation: InvestigationModel) {
    setInitialInvestigation(investigation)
    const currentRunId = investigation.regression?.execution.scenario_run_id
      ?? investigation.direct_repeat?.execution.scenario_run_id
      ?? investigation.original_failure.execution.scenario_run_id
    await loadProjection(currentRunId)
  }

  async function applyTopologyCorrection(workspace: InvestigationModel): Promise<InvestigationModel> {
    if (failureExecutionId === null) throw new Error('The preserved validation failure is unavailable.')
    let next = workspace
    if (next.correction_record === null) next = await api.recordCorrection(failureExecutionId, actor)
    if (next.direct_repeat === null) next = await api.runDirectRepeat(failureExecutionId, actor)
    if (next.regression === null) next = await api.startRegression(failureExecutionId, actor)
    const correctedRunId = next.regression?.execution.scenario_run_id
    if (correctedRunId !== undefined && next.regression?.execution.status === 'ACTIVE') {
      const correctedStart = await api.projection(correctedRunId)
      const initiateFault = correctedStart.allowed_actions.find((action) => action.command_type === 'INITIATE_FAULT' && action.available)
      if (initiateFault !== undefined) {
        await api.execute(correctedRunId, actor, initiateFault)
        const correctedFault = await api.projection(correctedRunId)
        const captureFaultCheckpoint = correctedFault.validation.actions.find((action) =>
          action.validation_execution_id === next.regression?.execution.validation_execution_id
          && action.action_type === 'CAPTURE_CHECKPOINT'
          && action.checkpoint_id === 'N1'
          && action.available,
        )
        if (captureFaultCheckpoint === undefined) throw new Error('The corrected fault checkpoint is unavailable.')
        await api.validationAction(captureFaultCheckpoint, correctedRunId)
        next = await api.investigation(failureExecutionId)
      }
    }
    return next
  }

  async function saveCorrectedCheckpoint(current: WorkspaceProjection): Promise<WorkspaceProjection> {
    const regression = initialInvestigation?.regression
    if (experience !== 'investigation' || regression?.execution.status !== 'ACTIVE' || regression.execution.scenario_run_id !== current.run.scenario_run_id) return current
    let latest = current
    let summary = latest.validation.run_executions.find((item) => item.execution.validation_execution_id === regression.execution.validation_execution_id)
    if (summary === undefined) return latest
    const checkpointId = latest.run.network_state_label
    if (!summary.evidence_snapshots.some((item) => item.checkpoint_id === checkpointId)) {
      const capture = latest.validation.actions.find((item) => item.validation_execution_id === regression.execution.validation_execution_id && item.action_type === 'CAPTURE_CHECKPOINT' && item.checkpoint_id === checkpointId && item.available)
      if (capture !== undefined) {
        await api.validationAction(capture, latest.run.scenario_run_id)
        latest = await loadProjection(latest.run.scenario_run_id)
        summary = latest.validation.run_executions.find((item) => item.execution.validation_execution_id === regression.execution.validation_execution_id)
      }
    }
    if (latest.run.network_state_label === 'N5' && summary?.execution.status === 'ACTIVE' && summary.evidence_snapshots.length === 6) {
      await api.completeValidationDetermination(summary)
      latest = await loadProjection(latest.run.scenario_run_id)
      if (failureExecutionId !== null) setInitialInvestigation(await api.investigation(failureExecutionId))
    }
    return latest
  }

  async function runCorrectedScenario() {
    if (failureExecutionId === null) return
    setError(null); setBusyActionId('RUN_CORRECTED_SCENARIO')
    try {
      let investigation = await api.runRegression(failureExecutionId, actor)
      if (investigation.regression?.execution.status === 'ACTIVE') {
        await api.completeValidationDetermination(investigation.regression)
        investigation = await api.investigation(failureExecutionId)
      }
      setInitialInvestigation(investigation)
      await investigationUpdated(investigation)
      setView('corrected')
    } catch (cause) { setError(cause instanceof Error ? cause.message : 'The corrected full scenario could not be completed.') }
    finally { setBusyActionId(null) }
  }

  async function executeAction(action: WorkspaceAction) {
    if (projection === null) return
    setError(null); setBusyActionId(action.action_id)
    let resultingRunId = projection.run.scenario_run_id
    try {
      const effectiveAction = experience === 'safety' && action.command_type === 'ACKNOWLEDGE_ALARM'
        ? { ...action, proposed_scenario_time: new Date(new Date(projection.run.initial_scenario_time).getTime() + 71_000).toISOString() }
        : action
      const result = await api.execute(projection.run.scenario_run_id, actor, effectiveAction)
      resultingRunId = result.snapshot.run.scenario_run_id
      let current = await loadProjection(result.snapshot.run.scenario_run_id)
      if (action.command_type === 'ACKNOWLEDGE_ALARM') setView('events')
      if (action.command_type === 'ASSESS_RESTORATION' || action.command_type === 'EXECUTE_RESTORATION') setView('restoration')
      if (experience === 'investigation' && initialInvestigation?.regression != null) current = await saveCorrectedCheckpoint(current)
      if (projection.run.mode === 'EXPLORATION' && ['RESET_RUN', 'ASSESS_RESTORATION', 'EXECUTE_RESTORATION'].includes(action.command_type)) {
        const restorationCanBeApplied = current.allowed_actions.some((item) => item.command_type === 'EXECUTE_RESTORATION' && item.available)
        const controlledResultReady = action.command_type === 'EXECUTE_RESTORATION'
          || (action.command_type === 'ASSESS_RESTORATION' && !restorationCanBeApplied)
        current = await saveExplorationEvidence(current, controlledResultReady)
        if (action.command_type === 'RESET_RUN') await generateClosedRunEvidence(projection.run.scenario_run_id)
      }
    } catch (cause) {
      const duplicateCheckpoint = cause instanceof Error && cause.message.includes('validation checkpoint identity already exists')
      setError(duplicateCheckpoint ? null : cause instanceof Error ? cause.message : 'Controlled command failed.')
      await loadProjection(resultingRunId)
    } finally { setBusyActionId(null) }
  }

  async function startCleanScenario() {
    if (projection === null) return
    if (experience !== 'exploration') {
      returnToRunSetup()
      return
    }
    const reset = projection.allowed_actions.find((item) => item.command_type === 'RESET_RUN' && item.available)
    if (reset !== undefined) {
      await executeAction(reset)
      return
    }
    if (projection.run.status === 'CLOSED') {
      await startRun(actor, projection.run.mode, projection.run.mode === 'EXPLORATION' ? projection.run.fault_section_id : undefined)
    }
  }

  async function executeValidationAction(action: ValidationWorkspaceAction) {
    if (projection === null) return
    setError(null); setValidationBusy(true)
    try { await api.validationAction(action, projection.run.scenario_run_id); await loadProjection(projection.run.scenario_run_id) }
    catch (cause) { setError(cause instanceof Error ? cause.message : 'Validation action failed.') }
    finally { setValidationBusy(false) }
  }

  if (bootstrap === null) return <main className="loading-page"><h1>OT Systems Demonstrator</h1><p>{error ?? 'Loading the scenario workspace…'}</p></main>
  if (runId === null || projection === null) return <><Surface id="Start / Run Setup"><RunSetup bootstrap={bootstrap} busy={busyActionId !== null} existingInvestigation={failureExecutionId !== null} onStartDefectInvestigation={startInvestigation} onStart={startRun} onResumeInvestigation={resumeInvestigation} onStartSafetyWalkthrough={startSafetyWalkthrough} /></Surface>{error !== null && <div className="global-error" role="alert">{error}</div>}</>

  const navigation = navigationByExperience[experience]
  const correctedRepeatReady = experience === 'investigation' && initialInvestigation?.regression?.execution.status === 'ACTIVE'
  const alarmReviewPending = projection.alarms.some((alarm) => alarm.active && alarm.acknowledgement_state !== 'ACKNOWLEDGED')
  const isolationActions = projection.allowed_actions.filter((action) => action.command_type === 'OPERATE_ISOLATION_DEVICE')
  const safetyEvidenceBlocked = experience === 'safety'
    && projection.alarms.some((alarm) => alarm.acknowledgement_state === 'ACKNOWLEDGED')
    && ['SW-A12', 'SW-A23'].every((entityId) => projection.telemetry.some((item) => item.entity_id === entityId && item.freshness === 'STALE'))
    && isolationActions.length > 0
    && isolationActions.every((action) => !action.available)
  const activeGuidance = correctedRepeatReady && view === 'operational'
    ? { title: 'Review the corrected topology and repeat the operation', purpose: 'Configuration v1.1 is loaded with the SEC-A2 fault active, matching the starting point of the original defect run. Continue the sequence manually or use the automatic run control.', notice: 'The application build and operating logic are unchanged; the corrected GIS endpoint is the controlled difference from the failed run.' }
    : safetyEvidenceBlocked && view === 'operational'
      ? { title: 'Review why isolation authority was withheld', purpose: 'The fault and alarm review are complete, but neither boundary-switch indication is recent enough to authorise isolation.', notice: 'The grey switching cards are the intended safe result—not unfinished operations. Continue through the active telemetry-evidence review below.' }
    : guidance[experience][view] ?? guidance[experience].operational!
  const guidedView = safetyEvidenceBlocked && view === 'operational' ? 'telemetry' : view
  return <div className="app-shell">
    <header className="app-header">
      <div className="header-brand"><span className="eyebrow">TasGrid East · fictional operational technology demonstrator</span><h1>OT Systems Demonstrator</h1></div>
      <div className="workflow-identity"><span className="eyebrow">Current walkthrough</span><strong>{experienceLabels[experience]}</strong></div>
      <div className="header-actions"><div className="safety-label"><span aria-hidden="true">◇</span><strong>LOCAL · SIMULATED · NO REAL CONTROL</strong></div><div className="header-buttons"><button type="button" className="header-button" onClick={returnToRunSetup}>Start another review</button></div></div>
    </header>
    <ContextRibbon projection={projection} />
    <nav ref={guidedNavRef} className="primary-nav" aria-label="Workspace views"><span className="nav-context">Guided steps</span>{navigation.map((item, index) => <button type="button" key={item.id} className={`${guidedView === item.id ? 'active' : ''}${experience === 'investigation' && index >= 4 ? ' defect-stage' : ''}`} aria-label={item.label} aria-current={guidedView === item.id ? 'page' : undefined} onClick={() => setView(item.id)}><span aria-hidden="true">{index + 1}</span>{item.label}</button>)}</nav>
    {error !== null && <div className="global-error" role="alert">{error}</div>}
    <main className="workspace-main">
      <section className="workflow-guide" aria-labelledby="workflow-guide-title"><div><span className="eyebrow">{view === 'engineering' ? 'Reference' : `${experienceLabels[experience]} · ${Math.max(1, navigation.findIndex((item) => item.id === guidedView) + 1)} of ${navigation.length}`}</span><h2 id="workflow-guide-title">{activeGuidance.title}</h2></div><div><p>{activeGuidance.purpose}</p><p><strong>What to notice:</strong> {activeGuidance.notice}</p></div></section>
      {view === 'operational' && <Surface id="Operational Workspace"><OperationalWorkspace projection={projection} busyActionId={busyActionId} onExecute={executeAction} onStartNewRun={startCleanScenario} runControlLabel={experience === 'exploration' ? 'Start a new clean scenario' : 'Return to walkthrough selection'} runControlDescription={experience === 'exploration' ? undefined : 'Leaves this preserved case and returns to the three available walkthroughs.'} correctedRepeatReady={correctedRepeatReady} alarmReviewPending={alarmReviewPending} safetyEvidenceBlocked={safetyEvidenceBlocked} onRunCorrectedScenario={runCorrectedScenario} explorationSectionIds={experience === 'exploration' ? bootstrap.exploration_section_ids : undefined} onStartExploration={experience === 'exploration' ? (sectionId) => startRun(actor, 'EXPLORATION', sectionId) : undefined} onNavigate={setView} /></Surface>}
      {(view === 'telemetry' || view === 'events') && <Surface id="Telemetry & Events">{view === 'telemetry'
        ? <TelemetryView projection={projection} focusEntityIds={experience === 'safety' ? ['SW-A12', 'SW-A23'] : undefined} onContinue={experience === 'safety' ? () => setView('validation') : undefined} />
        : <EventTimeline projection={projection} busyActionId={busyActionId} onExecute={executeAction} onContinue={() => setView('operational')} continueLabel={experience === 'safety' ? 'Review the blocked isolation decision' : undefined} />}</Surface>}
      {view === 'restoration' && <Surface id="Restoration Assessment"><RestorationView projection={projection} busyActionId={busyActionId} validationBusy={validationBusy} formalEvidenceRequired={experience !== 'investigation'} reviewAvailableAtAssessment={experience !== 'safety'} onExecute={executeAction} onSaveEvidence={executeValidationAction} onViewEvidence={() => setView(experience === 'investigation' && initialInvestigation?.regression != null ? 'corrected' : 'validation')} /></Surface>}
      {view === 'validation' && <Surface id="Formal Validation">{experience === 'investigation' && initialInvestigation !== null
        ? <DefectResults projection={projection} investigation={initialInvestigation} busy={busyActionId !== null} onInvestigate={() => setView('investigation')} />
        : experience === 'safety'
          ? <SafetyValidationResult projection={projection} onReturn={() => setView('telemetry')} onExit={returnToRunSetup} />
          : <div className="view-stack validation-report"><Surface id="Evidence Library"><EvidenceLibrary projection={projection} api={api} refreshKey={evidenceRefreshKey} onReturnToOperational={() => setView('operational')} explorationSectionIds={experience === 'exploration' ? bootstrap.exploration_section_ids : undefined} explorationRestartBusy={busyActionId !== null} onStartExploration={experience === 'exploration' ? (sectionId) => startRun(actor, 'EXPLORATION', sectionId) : undefined}><ValidationView projection={projection} busy={validationBusy} onAction={executeValidationAction} onContinue={setView} /></EvidenceLibrary></Surface></div>}
      </Surface>}
      {(view === 'investigation' || view === 'corrected') && <Surface id="Defect Investigation">{view === 'investigation'
        ? failureExecutionId === null
          ? <section className="panel"><span className="eyebrow">Controlled defect workflow</span><h2>Begin DEF-001 investigation</h2><p>Run the actual immutable v1.0 post-trip test before reviewing the consequence-to-source evidence.</p><button type="button" className="primary-action" disabled={busyActionId !== null} onClick={() => startInvestigation(actor)}>Run v1.0 test and investigate</button></section>
          : <InvestigationWorkspace api={api} failureExecutionId={failureExecutionId} actor={actor} initial={initialInvestigation} onUpdate={investigationUpdated} onApplyCorrection={applyTopologyCorrection} onCorrectionApplied={() => setView('operational')} />
        : failureExecutionId !== null && initialInvestigation !== null
          ? <CorrectedRunResult initial={initialInvestigation} projection={projection} onReturnToOperational={() => setView('operational')} onReturnToSelection={returnToRunSetup} onRestartDefect={restartDefectWalkthrough} />
          : null}</Surface>}
      {view === 'engineering' && <Surface id="Engineering Basis"><EngineeringBasis projection={projection} /></Surface>}
    </main>
    <footer><p>{projection.conceptual_boundary_notice}</p><p>Conceptual GIS · SCADA · ADMS Topology · ADMS Restoration · OMS functions within one local demonstrator.</p></footer>
  </div>
}
