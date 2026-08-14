import { useEffect, useMemo, useState, type ReactNode } from 'react'
import type { EvidenceExportCandidate, EvidencePackage, EvidenceSnapshot, ValidationExecutionSummary, WorkspaceProjection } from '../../api/contracts'
import type { WorkspaceApi } from '../../api/client'
import { formatKw, formatTime, humanise, shortId } from '../../components/format'

const checkpointCopy: Record<string, { title: string; description: string }> = {
  N0: { title: 'Normal network', description: 'Starting configuration and normal supply saved before the fault.' },
  N1: { title: 'Fault and feeder trip', description: 'Protection operation, loss of supply and initial customer impact saved.' },
  N2: { title: 'Fault isolated', description: 'Both incident-boundary switches proven open and the faulted section separated.' },
  N3: { title: 'Healthy upstream section restored', description: 'Normal supply restored where it does not cross the isolated fault.' },
  N4: { title: 'Alternate supply checked', description: 'Safety, telemetry, radiality and feeder-capacity checks saved.' },
  N5: { title: 'Eligible healthy sections restored', description: 'Final switching result, customer impact and network state saved.' },
  CONTROLLED_RESULT: { title: 'Controlled result', description: 'The selected exploration result and its supporting records were saved.' },
}

function checkpoint(snapshot: EvidenceSnapshot): { title: string; description: string } {
  return checkpointCopy[snapshot.checkpoint_id] ?? {
    title: humanise(snapshot.checkpoint_id),
    description: 'The supporting operational records were saved at this point.',
  }
}

function numberValue(summary: ValidationExecutionSummary, checkpointId: string, field: string): number | null {
  const value = summary.evidence_snapshots.find((item) => item.checkpoint_id === checkpointId)?.observed_values[field]
  return typeof value === 'number' ? value : null
}

function explorationValue(summary: ValidationExecutionSummary, field: string): unknown {
  return summary.evidence_snapshots.find((item) => item.checkpoint_id === 'CONTROLLED_RESULT')?.observed_values[field]
    ?? summary.execution.observed_result?.[field]
}

function explorationNumber(summary: ValidationExecutionSummary, field: string): number | null {
  const value = explorationValue(summary, field)
  if (typeof value === 'number') return value
  if (typeof value === 'string' && value.trim() !== '' && Number.isFinite(Number(value))) return Number(value)
  return null
}

function explorationText(summary: ValidationExecutionSummary, field: string): string | null {
  const value = explorationValue(summary, field)
  return typeof value === 'string' && value.length > 0 ? value : null
}

function explorationTextList(summary: ValidationExecutionSummary, field: string): string[] {
  const value = explorationValue(summary, field)
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === 'string') : []
}

function EvidenceOutcome({ summary, projection }: { summary: ValidationExecutionSummary; projection: WorkspaceProjection }) {
  const initialAffected = numberValue(summary, 'N1', 'affected_customer_count')
  const upstreamRemaining = numberValue(summary, 'N3', 'affected_customer_count')
  const finalRemaining = numberValue(summary, 'N5', 'affected_customer_count')
  const finalRestored = numberValue(summary, 'N5', 'restored_customer_delta')
  const assessment = projection.restoration_assessments.at(-1)
  const loading = assessment?.calculation === null || assessment?.calculation === undefined
    ? null
    : Number(assessment.calculation.resulting_loading_percent)

  if (summary.execution.evidence_class === 'EXPLORATORY') {
    const selectedSection = explorationText(summary, 'selected_fault_section_id') ?? 'Selected section'
    const affectedFeeder = explorationText(summary, 'affected_feeder_id') ?? 'Affected feeder'
    const boundaries = explorationTextList(summary, 'incident_boundary_device_ids')
    const affectedCustomers = explorationNumber(summary, 'affected_customer_count')
    const restoredCustomers = explorationNumber(summary, 'restored_customer_delta')
    const initialAffectedCustomers = affectedCustomers === null || restoredCustomers === null ? null : affectedCustomers + restoredCustomers
    const outcome = explorationText(summary, 'restoration_outcome')
    const proposedSections = explorationTextList(summary, 'proposed_section_ids')
    const alternateFeeder = explorationText(summary, 'alternate_feeder_id')
    const transferableLoad = explorationNumber(summary, 'transferable_load_kw')
    const resultingLoad = explorationNumber(summary, 'resulting_load_kw')
    const feederCapacity = explorationNumber(summary, 'feeder_capacity_kw')
    const resultingLoading = explorationNumber(summary, 'resulting_loading_percent')
    const radiality = explorationText(summary, 'radiality_status')
    const feederCustomerTotal = projection.network_nodes
      .filter((item) => item.configured.entity_type === 'SECTION' && item.configured.feeder_id === affectedFeeder)
      .reduce((total, item) => total + (item.configured.customer_count ?? 0), 0)
    const proposedRestoredCustomers = projection.network_nodes
      .filter((item) => proposedSections.includes(item.configured.entity_id))
      .reduce((total, item) => total + (item.configured.customer_count ?? 0), 0)
    const savedSourceMap = explorationValue(summary, 'section_source_feeder_ids')
    const savedResultShowsApplied = alternateFeeder !== null && proposedSections.length > 0 && typeof savedSourceMap === 'object' && savedSourceMap !== null
      && proposedSections.every((section) => {
        const sources = (savedSourceMap as Record<string, unknown>)[section]
        return Array.isArray(sources) && sources.includes(alternateFeeder)
      })
    const currentRunReachedFinalState = summary.execution.scenario_run_id === projection.run.scenario_run_id && projection.run.network_state_label === 'N5'
    const restorationApplied = savedResultShowsApplied || currentRunReachedFinalState
    const beforeAlternateCustomers = affectedCustomers === null
      ? null
      : savedResultShowsApplied && restoredCustomers !== null
        ? affectedCustomers + restoredCustomers
        : affectedCustomers
    const normalSupplyRestoredCustomers = beforeAlternateCustomers === null || feederCustomerTotal === 0 ? null : feederCustomerTotal - beforeAlternateCustomers
    const alternateSupplyRestoredCustomers = savedResultShowsApplied && restoredCustomers !== null ? restoredCustomers : proposedRestoredCustomers
    const finalAffectedCustomers = beforeAlternateCustomers === null ? null : Math.max(0, beforeAlternateCustomers - alternateSupplyRestoredCustomers)
    const initialCustomers = feederCustomerTotal > 0 ? feederCustomerTotal : initialAffectedCustomers
    return <div className="evidence-outcome-grid" aria-label="Exploration evidence summary">
      <article><span>Fault impact</span><strong>{initialCustomers === null ? selectedSection : `${initialCustomers} customers affected`}</strong><p>The feeder trip for {selectedSection} on {affectedFeeder} was recorded{boundaries.length === 0 ? '.' : ` and ${boundaries.join(' and ')} proved the fault isolated.`}</p></article>
      <article><span>Normal-supply recovery</span><strong>{beforeAlternateCustomers === null ? 'Customer impact saved' : `${beforeAlternateCustomers} remained affected`}</strong><p>{normalSupplyRestoredCustomers === null ? 'The healthy upstream recovery was preserved.' : `${normalSupplyRestoredCustomers} customers were restored upstream of the isolated fault.`}</p></article>
      <article><span>Alternate-supply decision</span><strong>{outcome === null ? 'Assessment saved' : humanise(outcome)}</strong><p>{resultingLoad !== null && feederCapacity !== null ? `${alternateFeeder ?? 'The alternate feeder'} ${restorationApplied ? 'carries' : 'would carry'} ${formatKw(resultingLoad)}, or ${resultingLoading === null ? 'a saved share' : `${resultingLoading.toFixed(1)}%`} of ${formatKw(feederCapacity)} capacity.` : proposedSections.length === 0 ? 'No sections were eligible for alternate supply.' : `${proposedSections.join(', ')} ${restorationApplied ? 'were' : 'could be'} supplied from ${alternateFeeder ?? 'the alternate feeder'}${transferableLoad === null ? '' : ` (${formatKw(transferableLoad)})`}.`} {radiality === null ? '' : `The network remains ${humanise(radiality).toLowerCase()}.`}</p></article>
      <article><span>Final result</span><strong>{finalAffectedCustomers === null ? 'Customer outcome saved' : `${finalAffectedCustomers} customers remained affected`}</strong><p>{alternateSupplyRestoredCustomers > 0 ? `${alternateSupplyRestoredCustomers} customers ${restorationApplied ? 'were' : 'would be'} restored from the alternate feeder;` : 'No additional customers were eligible for alternate supply;'} the faulted section remained isolated.</p></article>
    </div>
  }

  return <div className="evidence-outcome-grid" aria-label="Operational evidence summary">
    <article><span>Fault impact</span><strong>{initialAffected === null ? 'Saved' : `${initialAffected} customers affected`}</strong><p>The feeder trip and initial outage were recorded.</p></article>
    <article><span>Normal-supply recovery</span><strong>{upstreamRemaining === null ? 'Saved' : `${upstreamRemaining} remained affected`}</strong><p>{initialAffected !== null && upstreamRemaining !== null ? `${initialAffected - upstreamRemaining} customers were restored upstream of the isolated fault.` : 'The healthy upstream section was restored.'}</p></article>
    <article><span>Alternate-supply decision</span><strong>{assessment?.outcome === 'PERMITTED' ? 'Permitted' : assessment === undefined ? 'Saved' : humanise(assessment.outcome)}</strong><p>{loading === null ? 'The safety and network checks were preserved.' : `Riverbend Feeder would carry ${(assessment!.calculation!.resulting_load_kw / 1000).toFixed(3)} MW, or ${loading.toFixed(1)}% of capacity.`}</p></article>
    <article><span>Final result</span><strong>{finalRemaining === null ? 'Saved' : `${finalRemaining} customers remained affected`}</strong><p>{finalRestored === null ? 'The final network state was preserved.' : `${finalRestored} customers were restored from the alternate feeder; the faulted section remained isolated.`}</p></article>
  </div>
}

function ExplorationJourney({ summary, projection }: { summary: ValidationExecutionSummary; projection: WorkspaceProjection }) {
  const selectedSection = explorationText(summary, 'selected_fault_section_id') ?? 'the selected section'
  const affectedFeeder = explorationText(summary, 'affected_feeder_id') ?? 'the affected feeder'
  const boundaries = explorationTextList(summary, 'incident_boundary_device_ids')
  const affectedCustomers = explorationNumber(summary, 'affected_customer_count')
  const restoredCustomers = explorationNumber(summary, 'restored_customer_delta')
  const outcome = explorationText(summary, 'restoration_outcome')
  const proposedSections = explorationTextList(summary, 'proposed_section_ids')
  const alternateFeeder = explorationText(summary, 'alternate_feeder_id')
  const resultingLoading = explorationNumber(summary, 'resulting_loading_percent')
  const feederCustomerTotal = projection.network_nodes
    .filter((item) => item.configured.entity_type === 'SECTION' && item.configured.feeder_id === affectedFeeder)
    .reduce((total, item) => total + (item.configured.customer_count ?? 0), 0)
  const proposedRestoredCustomers = projection.network_nodes
    .filter((item) => proposedSections.includes(item.configured.entity_id))
    .reduce((total, item) => total + (item.configured.customer_count ?? 0), 0)
  const savedSourceMap = explorationValue(summary, 'section_source_feeder_ids')
  const savedResultShowsApplied = alternateFeeder !== null && proposedSections.length > 0 && typeof savedSourceMap === 'object' && savedSourceMap !== null
    && proposedSections.every((section) => {
      const sources = (savedSourceMap as Record<string, unknown>)[section]
      return Array.isArray(sources) && sources.includes(alternateFeeder)
    })
  const currentRunReachedFinalState = summary.execution.scenario_run_id === projection.run.scenario_run_id && projection.run.network_state_label === 'N5'
  const restorationApplied = savedResultShowsApplied || currentRunReachedFinalState
  const beforeAlternateCustomers = affectedCustomers === null
    ? null
    : savedResultShowsApplied && restoredCustomers !== null
      ? affectedCustomers + restoredCustomers
      : affectedCustomers
  const normalRestoredCustomers = beforeAlternateCustomers === null || feederCustomerTotal === 0 ? null : feederCustomerTotal - beforeAlternateCustomers
  const alternateRestoredCustomers = savedResultShowsApplied && restoredCustomers !== null ? restoredCustomers : proposedRestoredCustomers
  const finalAffectedCustomers = beforeAlternateCustomers === null ? null : Math.max(0, beforeAlternateCustomers - alternateRestoredCustomers)
  const stages = [
    { title: 'Normal network', description: `The corrected configuration and ${selectedSection} exploration input were retained.` },
    { title: 'Fault and feeder trip', description: `${feederCustomerTotal > 0 ? `${feederCustomerTotal} customers were affected` : 'The initial outage was recorded'} on ${affectedFeeder}.` },
    { title: 'Fault isolated', description: boundaries.length === 0 ? 'The isolation result was retained.' : `${boundaries.join(' and ')} were proven open around the selected fault.` },
    { title: 'Healthy upstream section restored', description: normalRestoredCustomers === null ? 'Normal-supply recovery was retained.' : `${normalRestoredCustomers} customers were restored upstream; ${beforeAlternateCustomers} remained affected.` },
    { title: 'Alternate supply checked', description: `${outcome === null ? 'The assessment was retained' : humanise(outcome)}${resultingLoading === null ? '.' : ` at ${resultingLoading.toFixed(1)}% alternate-feeder loading.`}` },
    { title: 'Eligible healthy sections restored', description: alternateRestoredCustomers > 0 ? `${alternateRestoredCustomers} customers ${restorationApplied ? 'were' : 'would be'} restored; ${finalAffectedCustomers ?? 'the faulted-section customers'} remained affected.` : 'No additional healthy sections were eligible; the fault remained isolated.' },
  ]
  return <>
    <p className="exploration-sequence-note">Exploration preserves these six operating stages within one combined controlled-result record; they are not relabelled as six formal checkpoints.</p>
    <div className="evidence-grid exploration-sequence" aria-label="Exploration operating sequence">{stages.map((stage) => <article key={stage.title}><span className="status-badge success">Included</span><strong>{stage.title}</strong><small>{stage.description}</small></article>)}</div>
  </>
}

export function EvidenceLibrary({
  projection,
  api,
  refreshKey = 0,
  onReturnToOperational,
  children,
}: {
  projection: WorkspaceProjection
  api: WorkspaceApi
  refreshKey?: number
  onReturnToOperational: () => void
  children?: ReactNode
}) {
  const [candidates, setCandidates] = useState<EvidenceExportCandidate[]>([])
  const [packages, setPackages] = useState<EvidencePackage[]>([])
  const [busyExecutionId, setBusyExecutionId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const evidenceReadinessKey = projection.validation.library_executions
    .map((item) => `${item.execution.validation_execution_id}:${item.execution.status}:${item.evidence_snapshots.length}`)
    .join('|')

  async function refresh() {
    const [nextCandidates, nextPackages] = await Promise.all([
      api.evidenceExportCandidates(),
      api.evidencePackages(),
    ])
    setCandidates(nextCandidates)
    setPackages(nextPackages)
  }

  useEffect(() => {
    refresh().catch((cause: unknown) => setError(cause instanceof Error ? cause.message : 'Unable to read the evidence package register.'))
  }, [api, projection.run.scenario_run_id, evidenceReadinessKey, refreshKey])

  const candidateByExecution = useMemo(
    () => new Map(candidates.map((item) => [item.validation_execution_id, item])),
    [candidates],
  )
  const summaryByExecution = useMemo(
    () => new Map(projection.validation.library_executions.map((item) => [item.execution.validation_execution_id, item])),
    [projection.validation.library_executions],
  )
  const latestRunExecution = projection.validation.library_executions
    .filter((item) => item.execution.scenario_run_id === projection.run.scenario_run_id && item.evidence_snapshots.length > 0)
    .at(-1) ?? projection.validation.library_executions
      .filter((item) => item.execution.scenario_run_id === projection.run.scenario_run_id)
      .at(-1) ?? projection.validation.library_executions
        .filter((item) => item.execution.evidence_class === projection.run.evidence_class && item.evidence_snapshots.length > 0)
        .at(-1)
  const latestEvidenceRunId = latestRunExecution?.execution.scenario_run_id ?? projection.run.scenario_run_id
  const visibleExecutions = projection.validation.library_executions.filter((item) => item.execution.scenario_run_id === latestEvidenceRunId)
  const packageByExecution = useMemo(() => {
    const result = new Map<string, EvidencePackage[]>()
    for (const item of packages) result.set(item.validation_execution_id, [...(result.get(item.validation_execution_id) ?? []), item])
    return result
  }, [packages])
  const latestRunPackages = packages.filter((item) => item.scenario_run_id === latestEvidenceRunId)
  const historicalPackages = packages.filter((item) => item.scenario_run_id !== latestEvidenceRunId).reverse()

  async function generate(validationExecutionId: string) {
    setError(null)
    setBusyExecutionId(validationExecutionId)
    try {
      const created = await api.generateEvidencePackage(validationExecutionId)
      setPackages((current) => current.some((item) => item.package_id === created.package_id) ? current : [...current, created])
      const [nextCandidates, nextPackages] = await Promise.all([api.evidenceExportCandidates(), api.evidencePackages()])
      setCandidates(nextCandidates)
      setPackages((current) => {
        const merged = [...nextPackages]
        if (!merged.some((item) => item.package_id === created.package_id)) merged.push(created)
        return merged.length >= current.length ? merged : current
      })
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Evidence package generation failed.')
    } finally {
      setBusyExecutionId(null)
    }
  }

  return <div className="view-stack">
    <section className="panel" aria-labelledby="evidence-library-title">
      <div className="panel-heading evidence-record-heading">
        <div><span className="eyebrow">Saved operational evidence</span><h2 id="evidence-library-title">What this walkthrough demonstrates</h2></div>
        <button type="button" className="secondary-action" onClick={onReturnToOperational}>Return to final network state</button>
      </div>
      <p>The key operating results are shown first. Record identities and integrity fingerprints remain available under technical traceability for anyone who needs to verify the saved source.</p>
      {error !== null && <div className="callout danger" role="alert">{error}</div>}
      {visibleExecutions.length === 0 ? <p className="empty-state">No saved evidence record is available for this run.</p> : <div className="record-list">{visibleExecutions.map((summary) => {
        const candidate = candidateByExecution.get(summary.execution.validation_execution_id)
        const ready = candidate?.export_available === true
        const recordedPackages = packageByExecution.get(summary.execution.validation_execution_id) ?? []
        return <article key={summary.execution.validation_execution_id} aria-label={`Saved evidence: ${summary.execution.test_id}`}>
          <div className="evidence-status-row">
            <span className={`status-badge ${summary.execution.status === 'FINALISED' ? 'success' : 'neutral'}`}>{summary.execution.status === 'FINALISED' ? 'Evidence complete' : 'Evidence still being completed'}</span>
            <span className={`status-badge ${summary.execution.evidence_class === 'FORMAL' ? 'formal' : 'exploratory'}`}>{summary.execution.evidence_class === 'FORMAL' ? 'Approved walkthrough' : 'Exploration'}</span>
            {summary.execution.verdict !== null && <span className={`status-badge ${summary.execution.verdict === 'PASS' ? 'success' : 'danger'}`}>{summary.execution.verdict === 'PASS' ? 'All defined checks passed' : 'One or more defined checks need review'}</span>}
          </div>
          {summary.evidence_snapshots.length === 0 ? <p className="empty-state">Complete the operating sequence to populate the result summary and its saved stage evidence.</p> : <>
            <EvidenceOutcome summary={summary} projection={projection} />
            <section className="saved-journey" aria-labelledby={`saved-journey-${summary.execution.validation_execution_id}`}>
              <h3 id={`saved-journey-${summary.execution.validation_execution_id}`}>Evidence saved through the operating sequence</h3>
              {summary.execution.evidence_class === 'EXPLORATORY' ? <ExplorationJourney summary={summary} projection={projection} /> : <div className="evidence-grid">{summary.evidence_snapshots.map((evidence) => {
                const copy = checkpoint(evidence)
                return <article key={evidence.evidence_snapshot_id}><span className="status-badge success">Saved</span><strong>{copy.title}</strong><small>{copy.description}</small></article>
              })}</div>}
            </section>
          </>}
          <details className="technical-details"><summary>Technical traceability and integrity records</summary>
            <p>These identities prove which run, configuration, application build and immutable evidence records produced the result above.</p>
            <dl className="identity-grid"><div><dt>Controlled test</dt><dd>{summary.execution.test_id}</dd></div><div><dt>Evidence record</dt><dd>{summary.execution.validation_execution_id}</dd></div><div><dt>Scenario run</dt><dd>{summary.execution.scenario_run_id}</dd></div><div><dt>Configuration</dt><dd>{summary.execution.configuration_id} · v{summary.execution.configuration_version}</dd></div><div><dt>Source catalogue</dt><dd>v{summary.execution.catalogue_version} · {summary.execution.catalogue_sha256}</dd></div><div><dt>Application build</dt><dd>{summary.execution.application_build_id}</dd></div><div><dt>Started</dt><dd>{formatTime(summary.execution.started_scenario_time)}</dd></div><div><dt>Completed</dt><dd>{summary.execution.finalised_scenario_time === null ? 'Not yet completed' : formatTime(summary.execution.finalised_scenario_time)}</dd></div></dl>
            <div className="evidence-grid technical-evidence-grid">{summary.evidence_snapshots.map((evidence) => <article key={evidence.evidence_snapshot_id}><strong>{evidence.checkpoint_id}</strong><span>Revision {evidence.state_revision}</span><small>Snapshot {evidence.evidence_snapshot_id}</small><small>Integrity fingerprint {evidence.canonical_payload_sha256}</small></article>)}</div>
          </details>
          {recordedPackages.length > 0 ? <div className="package-created-notice"><div><strong>Downloadable package recorded</strong><p>{recordedPackages.length === 1 ? 'The verified package is available in the current-run section below.' : `${recordedPackages.length} verified packages are available in the current-run section below.`}</p></div><span className="status-badge success">Recorded</span></div> : <div className="export-action"><button type="button" disabled={!ready || busyExecutionId !== null} onClick={() => generate(summary.execution.validation_execution_id)}>{busyExecutionId === summary.execution.validation_execution_id ? 'Creating evidence package…' : 'Create downloadable evidence package'}</button><div><strong>{candidate === undefined ? 'Checking package readiness…' : ready ? 'Ready to create' : 'Evidence record not ready'}</strong><p>{candidate === undefined ? 'The completed record is being checked.' : ready ? 'Creates a verified .zip containing the result, saved checkpoints and their traceability records without changing the current scenario.' : candidate.reason}</p></div></div>}
        </article>
      })}</div>}
    </section>
    {children}
    <section className="panel" aria-labelledby="package-register-title">
      <div className="panel-heading"><div><span className="eyebrow">Downloadable records</span><h2 id="package-register-title">Evidence packages</h2></div><span className="status-badge neutral">{packages.length === 0 ? 'None created' : `${packages.length} total`}</span></div>
      {latestRunPackages.length === 0 ? <p className="empty-state">No downloadable package has been created for the latest evidence run yet.</p> : <div className="record-list">{latestRunPackages.map((item) => {
        const source = summaryByExecution.get(item.validation_execution_id)
        return <article key={item.package_id} aria-label={`Current evidence package ${item.package_id}`}>
          <div><span className="status-badge success">Verified</span><span className={`status-badge ${item.evidence_class === 'FORMAL' ? 'formal' : 'exploratory'}`}>{item.evidence_class === 'FORMAL' ? 'Approved walkthrough' : 'Exploration'}</span></div>
          <h3>Latest-run evidence package</h3><p className="package-run-label">Run {shortId(item.scenario_run_id)} · completed {source?.execution.finalised_scenario_time === null || source === undefined ? 'after the saved result' : formatTime(source.execution.finalised_scenario_time)}</p><p>This archive contains the saved result and its supporting records.</p>
          <a className="download-link" href={`/api/v1/evidence-packages/${item.package_id}/download`}>Download evidence package (.zip)</a>
          <details className="technical-details"><summary>Package identity and integrity fingerprints</summary><dl className="identity-grid"><div><dt>Package ID</dt><dd>{item.package_id}</dd></div><div><dt>Source run</dt><dd>{item.scenario_run_id}</dd></div><div><dt>Source evidence record</dt><dd>{item.validation_execution_id}</dd></div><div><dt>Source configuration</dt><dd>{item.configuration_id} · v{item.configuration_version}</dd></div><div><dt>Source build</dt><dd>{item.application_build_id}</dd></div><div><dt>Generation build</dt><dd>{item.generation_application_build_id}</dd></div><div><dt>Archive path</dt><dd>{item.archive_path}</dd></div><div><dt>Manifest fingerprint</dt><dd>{item.manifest_sha256}</dd></div><div><dt>Archive fingerprint</dt><dd>{item.archive_sha256}</dd></div><div><dt>Source links</dt><dd>{item.source_record_references.join(', ')}</dd></div></dl></details>
        </article>
      })}</div>}
      {historicalPackages.length > 0 && <section className="saved-journey" aria-labelledby="package-history-title"><h3 id="package-history-title">Earlier evidence packages</h3><p>Earlier runs stay collapsed until you choose one.</p><div className="record-list">{historicalPackages.map((item) => {
        const source = summaryByExecution.get(item.validation_execution_id)
        const completed = source?.execution.finalised_scenario_time ?? source?.execution.started_scenario_time
        return <details className="package-history" key={item.package_id}><summary><span>Run {shortId(item.scenario_run_id)}</span><span className="package-run-label">{completed === undefined ? item.package_id : formatTime(completed)} · {item.package_id}</span></summary><div><p>{item.evidence_class === 'FORMAL' ? 'Approved formal walkthrough' : 'Exploration record'} from configuration {item.configuration_id} v{item.configuration_version}.</p><a className="download-link" href={`/api/v1/evidence-packages/${item.package_id}/download`}>Download this evidence package (.zip)</a><details className="technical-details"><summary>Integrity fingerprints</summary><dl className="identity-grid"><div><dt>Manifest fingerprint</dt><dd>{item.manifest_sha256}</dd></div><div><dt>Archive fingerprint</dt><dd>{item.archive_sha256}</dd></div><div><dt>Archive path</dt><dd>{item.archive_path}</dd></div></dl></details></div></details>
      })}</div></section>}
      <div className="return-action"><button type="button" className="secondary-action" onClick={onReturnToOperational}>Return to final network state</button></div>
    </section>
  </div>
}
