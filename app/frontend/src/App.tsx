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
type Experience = 'formal' | 'exploration' | 'investigation' | 'safety'
const RUN_STORAGE_KEY = 'ot-demo-current-run-id'
const INVESTIGATION_STORAGE_KEY = 'ot-demo-investigation-failure-id'
const EXPERIENCE_STORAGE_KEY = 'ot-demo-current-experience'

const experienceLabels: Record<Experience, string> = {
  formal: 'Formal validation and defect challenge',
  exploration: 'Configuration exploration',
  investigation: 'Formal validation · DEF-001 investigation',
  safety: 'Stale-telemetry safety case',
}

const navigationByExperience: Record<Experience, Array<{ id: View; label: string }>> = {
  formal: [
    { id: 'operational', label: 'Operational' },
    { id: 'restoration', label: 'Restoration' },
    { id: 'events', label: 'Events' },
    { id: 'validation', label: 'Results & evidence' },
  ],
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
    { id: 'telemetry', label: 'Telemetry evidence' },
    { id: 'validation', label: 'Safety result' },
  ],
}

const guidance: Record<Experience, Partial<Record<View, { title: string; purpose: string; notice: string }>>> = {
  formal: {
    operational: { title: 'Operate the SEC-A2 fault scenario', purpose: 'Follow the available action cards while the network diagram, customer impact and equipment information update together.', notice: 'The application calculates the affected sections and allowed actions from the current connectivity, switch positions and telemetry.' },
    restoration: { title: 'Review the alternate-supply decision', purpose: 'Check which healthy de-energised sections could be supplied from the other feeder, then review every safety and capacity check before acting.', notice: 'PERMITTED means every required check passed; REJECTED means a network criterion failed; BLOCKED means the evidence was not trustworthy enough to decide.' },
    validation: { title: 'Separate operating assurance from system validation', purpose: 'Review the live assurance checks first, then see how the secondary validation layer tests the complete operating mechanism against the accepted formal result.', notice: 'A successful operating run is the baseline. Continue into DEF-001 to see the validation process expose a real configuration-driven error.' },
    events: { title: 'Review and acknowledge the feeder-trip alarm', purpose: 'Read the alarm and event sequence before acknowledging that the simulated trip has been seen.', notice: 'Acknowledging an alarm records reviewer awareness; it does not restore supply or change a switch.' },
    engineering: { title: 'Engineering basis reference', purpose: 'Use this reference when you want the approved boundaries and source hierarchy behind the walkthrough.', notice: 'This is supporting context, not another action in the formal sequence.' },
  },
  exploration: {
    operational: { title: 'Explore the selected fault section', purpose: 'Operate the same network sequence with the selected section used as this scenario’s fault location.', notice: 'The application calculates feeder roles, isolation boundaries and outage impact for this selection; a restorable outcome is not guaranteed.' },
    events: { title: 'Review and acknowledge the feeder-trip alarm', purpose: 'Read the alarm and event sequence before acknowledging that the simulated trip has been seen.', notice: 'Acknowledging an alarm records reviewer awareness; it does not restore supply or change a switch.' },
    restoration: { title: 'Inspect the exploration restoration outcome', purpose: 'Review any alternate path and safety, telemetry and capacity checks after running the assessment.', notice: 'Exploration can legitimately produce PERMITTED, REJECTED, BLOCKED or no restoration candidate.' },
    validation: { title: 'Understand and export the exploration result', purpose: 'See how the selected fault was checked through each operating stage, review the calculated customer and network outcomes, and create its separate evidence package.', notice: 'Exploration uses the same operating checks, while its records remain visibly separate from the approved formal walkthrough.' },
    engineering: { title: 'Engineering basis reference', purpose: 'Use this reference to review the configuration-driven model and Exploration boundaries.', notice: 'This supporting reference does not turn the selected section into formal validation evidence.' },
  },
  investigation: {
    operational: { title: 'Operate with the hidden GIS configuration error', purpose: 'Continue the fault-isolation and restoration sequence using the v1.0 network record exactly as supplied to the operating mechanism.', notice: 'The actions can still look correct because assurance checks the current data and network model; the hidden configured connection is exposed later by independent validation.' },
    events: { title: 'Review the defect-run feeder trip', purpose: 'Inspect and acknowledge the event generated from the v1.0 run before continuing the isolation sequence.', notice: 'The alarm and telemetry are genuine and trustworthy—the defect is hidden in the configured network connection.' },
    restoration: { title: 'Complete the defect-run restoration assessment', purpose: 'Review the alternate-supply assessment produced from configuration v1.0 and preserve whether the model permits, rejects or cannot identify a restoration action.', notice: 'A defensible operating decision can still be based on a defective topology model; independent validation tests whether the overall result is actually correct.' },
    validation: { title: 'Compare live assurance with independent validation', purpose: 'See why the completed operating sequence can pass its live checks while the accepted customer-impact comparison fails.', notice: 'The mismatch is preserved rather than corrected on screen, creating the starting point for a traceable investigation.' },
    investigation: { title: 'Trace the wrong result back to its source', purpose: 'Follow the customer mismatch through trusted telemetry, topology attribution and outage arithmetic until the single GIS connection error is established.', notice: 'The investigation moves from consequence to cause; raw identities remain available only under technical traceability.' },
    corrected: { title: 'Repeat the scenario after the controlled correction', purpose: 'Use configuration v1.1 with the same application build and operating logic, then compare assurance and validation with the failed v1.0 result.', notice: 'Changing only the controlled GIS configuration demonstrates that the source record—not a hard-coded presentation—caused the original failure.' },
    engineering: { title: 'Engineering basis reference', purpose: 'Use this reference to review the accepted seeded-defect and validation boundaries.', notice: 'This is supporting context, not an editable investigation surface.' },
  },
  safety: {
    operational: { title: 'See unsafe switching withheld', purpose: 'Review the post-fault state and the disabled isolation actions created by stale boundary-switch telemetry.', notice: 'GOOD signal quality is not enough when the timestamp is too old; the switching action remains unavailable.' },
    telemetry: { title: 'Inspect the stale evidence', purpose: 'Compare value, quality, age and freshness for the required boundary devices.', notice: 'Notice that quality and freshness remain independent and both switches are classified STALE / INSUFFICIENT.' },
    validation: { title: 'Confirm the conservative safety response', purpose: 'Separate the operating outcome—switching authority withheld—from the validation verdict that confirms this was the required behaviour.', notice: 'A stopped operation can be a successful safety outcome when the evidence is insufficient.' },
    engineering: { title: 'Engineering basis reference', purpose: 'Use this reference to review the conservative telemetry and switching rules.', notice: 'This is supporting context, not another safety-case action.' },
  },
}

const surfaceById = Object.fromEntries(controlledSurfaces.surfaces.map((surface) => [surface.surface_id, surface]))

function Surface({ id, children }: { id: string; children: ReactNode }) {
  const surface = surfaceById[id]
  if (surface === undefined) throw new Error(`Controlled surface is not registered: ${id}`)
  return <ControlledSurface surfaceId={surface.surface_id} identityProfile={surface.required_identity_profile} fixedNotice={surface.fixed_notice}>{children}</ControlledSurface>
}

function DefectStoryContinuation({ ready, existingInvestigation, busy, onStart, onResume }: { ready: boolean; existingInvestigation: boolean; busy: boolean; onStart: () => void; onResume: () => void }) {
  return <section className="panel defect-story-continuation" aria-labelledby="defect-story-title">
    <div className="panel-heading"><div><span className="eyebrow">Next: test whether validation finds a defect</span><h2 id="defect-story-title">Challenge the operating logic with DEF-001</h2></div><span className={`status-badge ${ready ? 'formal' : 'neutral'}`}>{ready ? 'Formal baseline complete' : 'Complete the formal baseline first'}</span></div>
    <p>The successful SEC-A2 result establishes how the operating mechanism should behave. The next part runs the same logic against the preserved v1.0 network configuration, where an incorrect source relationship produces the wrong topology and outage result.</p>
    <div className="defect-story-steps"><article><span>1</span><strong>Preserve the incorrect result</strong><p>Run the real v1.0 calculation and retain its failed validation evidence.</p></article><article><span>2</span><strong>Trace consequence to source</strong><p>Follow the affected-customer mismatch back through topology evidence to the configuration defect.</p></article><article><span>3</span><strong>Correct and repeat</strong><p>Use v1.1 with the same application build, repeat the test and preserve the corrected regression result.</p></article></div>
    <button type="button" className="primary-action" disabled={!ready || busy} onClick={existingInvestigation ? onResume : onStart}>{busy ? 'Opening defect investigation…' : existingInvestigation ? 'Continue preserved DEF-001 investigation' : 'Continue to DEF-001 investigation'}</button>
    {!ready && <p className="continuation-reason">This continuation becomes available after all six formal states have been preserved and the accepted comparison has produced PASS.</p>}
  </section>
}

export function App({ api = workspaceApi }: { api?: WorkspaceApi }) {
  const [bootstrap, setBootstrap] = useState<WorkspaceBootstrap | null>(null)
  const [projection, setProjection] = useState<WorkspaceProjection | null>(null)
  const [runId, setRunId] = useState<string | null>(() => localStorage.getItem(RUN_STORAGE_KEY))
  const [actor, setActor] = useState('Graduate Engineer')
  const [failureExecutionId, setFailureExecutionId] = useState<string | null>(() => localStorage.getItem(INVESTIGATION_STORAGE_KEY))
  const [initialInvestigation, setInitialInvestigation] = useState<InvestigationModel | null>(null)
  const [experience, setExperience] = useState<Experience>(() => {
    const stored = localStorage.getItem(EXPERIENCE_STORAGE_KEY)
    return stored === 'formal' || stored === 'exploration' || stored === 'investigation' || stored === 'safety' ? stored : 'formal'
  })
  const [view, setView] = useState<View>('operational')
  const [busyActionId, setBusyActionId] = useState<string | null>(null)
  const [validationBusy, setValidationBusy] = useState(false)
  const [evidenceRefreshKey, setEvidenceRefreshKey] = useState(0)
  const [error, setError] = useState<string | null>(null)
  const formalCheckpointTasks = useRef(new Map<string, Promise<WorkspaceProjection>>())
  const explorationEvidenceTasks = useRef(new Map<string, Promise<WorkspaceProjection>>())
  const guidedNavRef = useRef<HTMLElement | null>(null)

  useEffect(() => { api.bootstrap().then(setBootstrap).catch((cause: unknown) => setError(cause instanceof Error ? cause.message : 'Unable to load controlled workspace context.')) }, [api])
  useEffect(() => {
    if (experience !== 'investigation' || failureExecutionId === null || initialInvestigation !== null) return
    api.investigation(failureExecutionId).then(setInitialInvestigation).catch((cause: unknown) => setError(cause instanceof Error ? cause.message : 'Unable to reload the preserved investigation.'))
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

  async function saveFormalCheckpointOnce(current: WorkspaceProjection): Promise<WorkspaceProjection> {
    if (current.run.mode !== 'FORMAL') return current
    const testId = 'VT-FML-N0-N5-001'
    let latest = current
    const summary = latest.validation.run_executions.find((item) => item.execution.test_id === testId)
    if (summary === undefined) {
      const start = latest.validation.actions.find((item) => item.test_id === testId && item.action_type === 'START_EXECUTION' && item.available)
      if (start === undefined) return latest
      await api.validationAction(start, latest.run.scenario_run_id)
      latest = await loadProjection(latest.run.scenario_run_id)
    }
    const alreadySaved = latest.validation.run_executions
      .find((item) => item.execution.test_id === testId)
      ?.evidence_snapshots.some((item) => item.checkpoint_id === latest.run.network_state_label) === true
    if (!alreadySaved) {
      const capture = latest.validation.actions.find((item) => item.test_id === testId && item.action_type === 'CAPTURE_CHECKPOINT' && item.checkpoint_id === latest.run.network_state_label && item.available)
      if (capture === undefined) return latest
      await api.validationAction(capture, latest.run.scenario_run_id)
      latest = await loadProjection(latest.run.scenario_run_id)
    }
    if (latest.run.network_state_label === 'N5') {
      const completed = latest.validation.run_executions.find((item) => item.execution.test_id === testId)
      if (completed?.execution.status === 'ACTIVE' && completed.evidence_snapshots.length === 6) {
        await api.completeValidationDetermination(completed)
        latest = await loadProjection(latest.run.scenario_run_id)
      }
    }
    return latest
  }

  function saveFormalCheckpoint(current: WorkspaceProjection): Promise<WorkspaceProjection> {
    const key = `${current.run.scenario_run_id}:${current.run.network_state_label}`
    const existing = formalCheckpointTasks.current.get(key)
    if (existing !== undefined) return existing
    const task = saveFormalCheckpointOnce(current).finally(() => formalCheckpointTasks.current.delete(key))
    formalCheckpointTasks.current.set(key, task)
    return task
  }

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
      .then(async (current) => {
        if (current.run.status === 'CLOSED' && current.run.mode === 'FORMAL') {
          const activeRunId = await api.latestActiveFormalRun()
          if (activeRunId !== null && activeRunId !== current.run.scenario_run_id) return loadProjection(activeRunId)
        }
        return current
      })
      .catch((cause: unknown) => { setError(cause instanceof Error ? cause.message : 'Unable to reload the preserved run.'); localStorage.removeItem(RUN_STORAGE_KEY); setRunId(null) })
  }, [api, loadProjection, runId])

  async function startRun(requestedActor: string, mode: 'FORMAL' | 'EXPLORATION' = 'FORMAL', faultSectionId?: string) {
    if (bootstrap === null) return
    setError(null); setBusyActionId('INITIALISE_RUN'); setActor(requestedActor)
    try {
      const result = await api.initialise(bootstrap, requestedActor, mode, faultSectionId)
      const nextExperience = mode === 'EXPLORATION' ? 'exploration' : 'formal'
      setExperience(nextExperience); localStorage.setItem(EXPERIENCE_STORAGE_KEY, nextExperience)
      setView('operational')
      const current = await loadProjection(result.snapshot.run.scenario_run_id)
      if (mode === 'FORMAL') await saveFormalCheckpoint(current)
      else await saveExplorationEvidence(current, false)
    } catch (cause) {
      if (cause instanceof Error && cause.message.includes('mutable run already exists')) {
        const activeRunId = await api.latestActiveFormalRun()
        if (activeRunId !== null) {
          setExperience('formal'); localStorage.setItem(EXPERIENCE_STORAGE_KEY, 'formal')
          setView('operational'); await loadProjection(activeRunId); setError(null)
          return
        }
      }
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
      setView(investigation.direct_repeat === null ? 'operational' : investigation.regression === null ? 'investigation' : 'corrected')
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

  async function executeAction(action: WorkspaceAction) {
    if (projection === null) return
    setError(null); setBusyActionId(action.action_id)
    let resultingRunId = projection.run.scenario_run_id
    try {
      const result = await api.execute(projection.run.scenario_run_id, actor, action)
      resultingRunId = result.snapshot.run.scenario_run_id
      let current = await loadProjection(result.snapshot.run.scenario_run_id)
      if (action.command_type === 'ACKNOWLEDGE_ALARM') setView('events')
      if (action.command_type === 'ASSESS_RESTORATION' || action.command_type === 'EXECUTE_RESTORATION') setView('restoration')
      if (projection.run.mode === 'FORMAL' && experience !== 'investigation' && (action.command_type === 'RESET_RUN' || ['N1', 'N2', 'N3', 'N4', 'N5'].includes(current.run.network_state_label))) {
        current = await saveFormalCheckpoint(current)
      }
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

  if (bootstrap === null) return <main className="loading-page"><h1>OT Graduate Demonstrator</h1><p>{error ?? 'Loading the scenario workspace…'}</p></main>
  if (runId === null || projection === null) return <><Surface id="Start / Run Setup"><RunSetup bootstrap={bootstrap} busy={busyActionId !== null} existingInvestigation={failureExecutionId !== null} onStart={startRun} onResumeInvestigation={resumeInvestigation} onStartSafetyWalkthrough={startSafetyWalkthrough} /></Surface>{error !== null && <div className="global-error" role="alert">{error}</div>}</>

  const navigation = navigationByExperience[experience]
  const activeGuidance = guidance[experience][view] ?? guidance[experience].operational!
  const formalSummary = projection.validation.run_executions.find((item) => item.execution.test_id === 'VT-FML-N0-N5-001')
  const formalBaselineReady = projection.run.mode === 'FORMAL' && formalSummary?.execution.status === 'FINALISED' && formalSummary.execution.verdict === 'PASS'

  return <div className="app-shell">
    <header className="app-header">
      <div className="header-brand"><span className="eyebrow">TasGrid East · fictional engineering demonstrator</span><h1>OT Graduate Demonstrator</h1></div>
      <div className="workflow-identity"><span className="eyebrow">Current walkthrough</span><strong>{experienceLabels[experience]}</strong></div>
      <div className="header-actions"><div className="safety-label"><span aria-hidden="true">◇</span><strong>LOCAL · SIMULATED · NO REAL CONTROL</strong></div><div className="header-buttons"><button type="button" className="header-button" onClick={() => setView('engineering')}>Engineering basis</button><button type="button" className="header-button" onClick={returnToRunSetup}>Start another review</button></div></div>
    </header>
    <ContextRibbon projection={projection} />
    <nav ref={guidedNavRef} className="primary-nav" aria-label="Workspace views"><span className="nav-context">Guided steps</span>{navigation.map((item, index) => <button type="button" key={item.id} className={`${view === item.id ? 'active' : ''}${experience === 'investigation' && index >= 4 ? ' defect-stage' : ''}`} aria-label={item.label} aria-current={view === item.id ? 'page' : undefined} onClick={() => setView(item.id)}><span aria-hidden="true">{index + 1}</span>{item.label}</button>)}</nav>
    {error !== null && <div className="global-error" role="alert">{error}</div>}
    <main className="workspace-main">
      <section className="workflow-guide" aria-labelledby="workflow-guide-title"><div><span className="eyebrow">{view === 'engineering' ? 'Reference' : `${experienceLabels[experience]} · ${Math.max(1, navigation.findIndex((item) => item.id === view) + 1)} of ${navigation.length}`}</span><h2 id="workflow-guide-title">{activeGuidance.title}</h2></div><div><p>{activeGuidance.purpose}</p><p><strong>What to notice:</strong> {activeGuidance.notice}</p></div></section>
      {view === 'operational' && <Surface id="Operational Workspace"><OperationalWorkspace projection={projection} busyActionId={busyActionId} onExecute={executeAction} onStartNewRun={startCleanScenario} onNavigate={setView} /></Surface>}
      {(view === 'telemetry' || view === 'events') && <Surface id="Telemetry & Events">{view === 'telemetry'
        ? <TelemetryView projection={projection} onContinue={experience === 'safety' ? () => setView('validation') : undefined} />
        : <EventTimeline projection={projection} busyActionId={busyActionId} onExecute={executeAction} onContinue={() => setView('operational')} />}</Surface>}
      {view === 'restoration' && <Surface id="Restoration Assessment"><RestorationView projection={projection} busyActionId={busyActionId} validationBusy={validationBusy} formalEvidenceRequired={experience !== 'investigation'} reviewAvailableAtAssessment={experience === 'investigation'} onExecute={executeAction} onSaveEvidence={executeValidationAction} onViewEvidence={() => setView('validation')} /></Surface>}
      {view === 'validation' && experience === 'investigation' && initialInvestigation !== null && <Surface id="Formal Validation"><DefectResults projection={projection} investigation={initialInvestigation} busy={busyActionId !== null} onInvestigate={() => setView('investigation')} /></Surface>}
      {view === 'validation' && experience === 'safety' && <Surface id="Formal Validation"><SafetyValidationResult projection={projection} onReturn={() => setView('telemetry')} /></Surface>}
      {view === 'validation' && experience !== 'investigation' && experience !== 'safety' && <div className="view-stack validation-report">
        <Surface id="Evidence Library"><EvidenceLibrary
          projection={projection}
          api={api}
          refreshKey={evidenceRefreshKey}
          onReturnToOperational={() => setView('operational')}
        >
          <Surface id="Formal Validation"><ValidationView projection={projection} busy={validationBusy} onAction={executeValidationAction} onContinue={setView} />
            {experience === 'formal' && <DefectStoryContinuation ready={formalBaselineReady} existingInvestigation={failureExecutionId !== null} busy={busyActionId !== null} onStart={() => startInvestigation(actor)} onResume={() => resumeInvestigation(actor)} />}
          </Surface>
        </EvidenceLibrary></Surface>
      </div>}
      {view === 'investigation' && <Surface id="Defect Investigation">{failureExecutionId === null
        ? <section className="panel"><span className="eyebrow">Controlled defect workflow</span><h2>Begin DEF-001 investigation</h2><p>Run the actual immutable v1.0 post-trip test before reviewing the consequence-to-source evidence.</p><button type="button" className="primary-action" disabled={busyActionId !== null} onClick={() => startInvestigation(actor)}>Run v1.0 test and investigate</button></section>
        : <InvestigationWorkspace api={api} failureExecutionId={failureExecutionId} actor={actor} initial={initialInvestigation} onUpdate={investigationUpdated} onContinue={() => setView('corrected')} />}</Surface>}
      {view === 'corrected' && failureExecutionId !== null && initialInvestigation !== null && <Surface id="Defect Investigation"><CorrectedRunResult api={api} actor={actor} failureExecutionId={failureExecutionId} initial={initialInvestigation} projection={projection} onUpdate={investigationUpdated} /></Surface>}
      {view === 'engineering' && <Surface id="Engineering Basis"><EngineeringBasis projection={projection} /></Surface>}
    </main>
    <footer><p>{projection.conceptual_boundary_notice}</p><p>Conceptual GIS · SCADA · ADMS Topology · ADMS Restoration · OMS functions within one local demonstrator.</p></footer>
  </div>
}
