import { useEffect, useMemo, useState } from 'react'
import type { EvidenceExportCandidate, EvidencePackage, WorkspaceProjection } from '../../api/contracts'
import type { WorkspaceApi } from '../../api/client'
import { formatTime, humanise, shortId } from '../../components/format'

export function EvidenceLibrary({ projection, api }: { projection: WorkspaceProjection; api: WorkspaceApi }) {
  const [candidates, setCandidates] = useState<EvidenceExportCandidate[]>([])
  const [packages, setPackages] = useState<EvidencePackage[]>([])
  const [busyExecutionId, setBusyExecutionId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

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
  }, [api, projection.run.scenario_run_id])

  const candidateByExecution = useMemo(
    () => new Map(candidates.map((item) => [item.validation_execution_id, item])),
    [candidates],
  )

  async function generate(validationExecutionId: string) {
    setError(null); setBusyExecutionId(validationExecutionId)
    try { await api.generateEvidencePackage(validationExecutionId); await refresh() }
    catch (cause) { setError(cause instanceof Error ? cause.message : 'Evidence package generation failed.') }
    finally { setBusyExecutionId(null) }
  }

  return <div className="view-stack">
    <section className="panel" aria-labelledby="evidence-library-title">
      <div className="panel-heading"><div><span className="eyebrow">Immutable I5/I7 source records</span><h2 id="evidence-library-title">Evidence library and export</h2></div><span className={`status-badge ${projection.run.evidence_class === 'FORMAL' ? 'formal' : 'exploratory'}`}>{projection.run.evidence_class}</span></div>
      <div className="callout neutral">Exports are assembled by the backend from preserved records. The browser supplies only a validation-execution identity; it does not submit expected values, observed values, verdicts, hashes, configuration truth or engineering calculations.</div>
      {error !== null && <div className="callout danger" role="alert">{error}</div>}
      {projection.validation.library_executions.length === 0 ? <p className="empty-state">No validation execution records are available.</p> : <div className="record-list">{projection.validation.library_executions.map((summary) => {
        const candidate = candidateByExecution.get(summary.execution.validation_execution_id)
        return <article key={summary.execution.validation_execution_id}>
          <div><span className="status-badge neutral">{summary.execution.status}</span><span className={`status-badge ${summary.execution.evidence_class === 'FORMAL' ? 'formal' : 'exploratory'}`}>{summary.execution.evidence_class}</span>{summary.execution.verdict !== null && <span className={`status-badge ${summary.execution.verdict === 'PASS' ? 'success' : 'danger'}`}>{summary.execution.verdict}</span>}</div>
          <h3>{summary.execution.test_id}</h3><p>{summary.execution.expected_result_statement}</p>
          <dl><div><dt>Execution</dt><dd>{summary.execution.validation_execution_id}</dd></div><div><dt>Scenario run</dt><dd>{summary.execution.scenario_run_id}</dd></div><div><dt>Configuration</dt><dd>{summary.execution.configuration_id}</dd></div><div><dt>Source build</dt><dd>{summary.execution.application_build_id}</dd></div><div><dt>Started</dt><dd>{formatTime(summary.execution.started_scenario_time)}</dd></div><div><dt>Determination</dt><dd>{summary.execution.verdict ?? 'NOT DETERMINED'}</dd></div></dl>
          <div className="evidence-grid">{summary.evidence_snapshots.map((evidence) => <article key={evidence.evidence_snapshot_id}><strong>{evidence.checkpoint_id}</strong><span>Revision {evidence.state_revision}</span><small title={evidence.evidence_snapshot_id}>Evidence {shortId(evidence.evidence_snapshot_id)} · {evidence.content_categories.length} categories</small></article>)}</div>
          <div className="export-action"><button type="button" disabled={candidate?.export_available !== true || busyExecutionId !== null} onClick={() => generate(summary.execution.validation_execution_id)}>{busyExecutionId === summary.execution.validation_execution_id ? 'Generating verified ZIP…' : 'Generate new evidence ZIP'}</button><div><strong>{candidate === undefined ? 'Checking backend export gate…' : humanise(candidate.reason_code)}</strong><p>{candidate?.reason ?? 'Export availability is backend-owned.'}</p></div></div>
        </article>
      })}</div>}
    </section>
    <section className="panel" aria-labelledby="package-register-title">
      <div className="panel-heading"><div><span className="eyebrow">Append-only export register</span><h2 id="package-register-title">Generated evidence packages</h2></div><span className="status-badge neutral">{packages.length} packages</span></div>
      {packages.length === 0 ? <p className="empty-state">No package has been generated. Every future export receives a new identity and path.</p> : <div className="record-list">{packages.map((item) => <article key={item.package_id}>
        <div><span className={`status-badge ${item.evidence_class === 'FORMAL' ? 'formal' : 'exploratory'}`}>{item.evidence_class}</span><span className="status-badge success">{item.verification_status}</span></div>
        <h3>{item.package_id}</h3><dl><div><dt>Source execution</dt><dd>{item.validation_execution_id}</dd></div><div><dt>Archive path</dt><dd>{item.archive_path}</dd></div><div><dt>Manifest SHA-256</dt><dd>{item.manifest_sha256}</dd></div><div><dt>Archive SHA-256</dt><dd>{item.archive_sha256}</dd></div></dl>
        <a className="download-link" href={`/api/v1/evidence-packages/${item.package_id}/download`}>Download verified ZIP</a>
      </article>)}</div>}
    </section>
  </div>
}
