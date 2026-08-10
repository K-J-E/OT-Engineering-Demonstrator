import { useCallback, useEffect, useState } from 'react'
import type { ValidationWorkspaceAction, WorkspaceAction, WorkspaceBootstrap, WorkspaceProjection } from './api/contracts'
import { workspaceApi, type WorkspaceApi } from './api/client'
import { ContextRibbon } from './features/operational/ContextRibbon'
import { OperationalWorkspace } from './features/operational/OperationalWorkspace'
import { RestorationView } from './features/restoration/RestorationView'
import { RunSetup } from './features/run-setup/RunSetup'
import { EventTimeline } from './features/telemetry-events/EventTimeline'
import { TelemetryView } from './features/telemetry-events/TelemetryView'
import { EvidenceLibrary } from './features/validation/EvidenceLibrary'
import { ValidationView } from './features/validation/ValidationView'

type View = 'operational' | 'telemetry' | 'events' | 'restoration' | 'validation' | 'evidence'
const RUN_STORAGE_KEY = 'ot-demo-current-run-id'
const navigation: Array<{ id: View; label: string }> = [
  { id: 'operational', label: 'Operational' },
  { id: 'telemetry', label: 'Telemetry' },
  { id: 'events', label: 'Events' },
  { id: 'restoration', label: 'Restoration' },
  { id: 'validation', label: 'Validation' },
  { id: 'evidence', label: 'Evidence' },
]

export function App({ api = workspaceApi }: { api?: WorkspaceApi }) {
  const [bootstrap, setBootstrap] = useState<WorkspaceBootstrap | null>(null)
  const [projection, setProjection] = useState<WorkspaceProjection | null>(null)
  const [runId, setRunId] = useState<string | null>(() => localStorage.getItem(RUN_STORAGE_KEY))
  const [actor, setActor] = useState('Graduate Engineer')
  const [view, setView] = useState<View>('operational')
  const [busyActionId, setBusyActionId] = useState<string | null>(null)
  const [validationBusy, setValidationBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => { api.bootstrap().then(setBootstrap).catch((cause: unknown) => setError(cause instanceof Error ? cause.message : 'Unable to load controlled workspace context.')) }, [api])

  const loadProjection = useCallback(async (identity: string) => {
    const current = await api.projection(identity)
    setProjection(current)
    setRunId(identity)
    localStorage.setItem(RUN_STORAGE_KEY, identity)
  }, [api])

  useEffect(() => {
    if (runId !== null) loadProjection(runId).catch((cause: unknown) => { setError(cause instanceof Error ? cause.message : 'Unable to reload the preserved run.'); localStorage.removeItem(RUN_STORAGE_KEY); setRunId(null) })
  }, [loadProjection, runId])

  async function startRun(requestedActor: string) {
    if (bootstrap === null) return
    setError(null); setBusyActionId('INITIALISE_RUN'); setActor(requestedActor)
    try {
      const result = await api.initialise(bootstrap, requestedActor)
      await loadProjection(result.snapshot.run.scenario_run_id)
    } catch (cause) { setError(cause instanceof Error ? cause.message : 'Run initialisation failed.') } finally { setBusyActionId(null) }
  }

  async function executeAction(action: WorkspaceAction) {
    if (projection === null) return
    if (action.confirmation_required && !window.confirm(action.confirmation_text ?? 'Confirm simulated action.')) return
    setError(null); setBusyActionId(action.action_id)
    try {
      const result = await api.execute(projection.run.scenario_run_id, actor, action)
      await loadProjection(result.snapshot.run.scenario_run_id)
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Controlled command failed.')
      await loadProjection(projection.run.scenario_run_id)
    } finally { setBusyActionId(null) }
  }

  async function executeValidationAction(action: ValidationWorkspaceAction) {
    if (projection === null) return
    setError(null); setValidationBusy(true)
    try { await api.validationAction(action, projection.run.scenario_run_id); await loadProjection(projection.run.scenario_run_id) }
    catch (cause) { setError(cause instanceof Error ? cause.message : 'Validation action failed.') }
    finally { setValidationBusy(false) }
  }

  if (bootstrap === null) return <main className="loading-page"><h1>OT Graduate Demonstrator</h1><p>{error ?? 'Loading backend-controlled workspace context…'}</p></main>
  if (runId === null || projection === null) return <><RunSetup bootstrap={bootstrap} busy={busyActionId !== null} onStart={startRun} />{error !== null && <div className="global-error" role="alert">{error}</div>}</>

  return <div className="app-shell">
    <header className="app-header"><div><span className="eyebrow">TasGrid East · fictional engineering demonstrator</span><h1>OT Graduate Demonstrator</h1></div><div className="safety-label"><span aria-hidden="true">◇</span><strong>LOCAL · SIMULATED · NO REAL CONTROL</strong></div></header>
    <ContextRibbon projection={projection} />
    <nav className="primary-nav" aria-label="Workspace views">{navigation.map((item) => <button type="button" key={item.id} className={view === item.id ? 'active' : ''} aria-current={view === item.id ? 'page' : undefined} onClick={() => setView(item.id)}>{item.label}</button>)}</nav>
    {error !== null && <div className="global-error" role="alert">{error}</div>}
    <main className="workspace-main">
      {view === 'operational' && <OperationalWorkspace projection={projection} busyActionId={busyActionId} onExecute={executeAction} />}
      {view === 'telemetry' && <TelemetryView projection={projection} />}
      {view === 'events' && <EventTimeline projection={projection} />}
      {view === 'restoration' && <RestorationView projection={projection} busyActionId={busyActionId} onExecute={executeAction} />}
      {view === 'validation' && <ValidationView projection={projection} busy={validationBusy} onAction={executeValidationAction} />}
      {view === 'evidence' && <EvidenceLibrary projection={projection} />}
    </main>
    <footer><p>{projection.conceptual_boundary_notice}</p><p>Conceptual GIS · SCADA · ADMS Topology · ADMS Restoration · OMS functions within one local demonstrator.</p></footer>
  </div>
}
