import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import type { WorkspaceApi } from '../../api/client'
import type { WorkspaceBootstrap } from '../../api/contracts'
import { ContextRibbon } from '../operational/ContextRibbon'
import { RunSetup } from '../run-setup/RunSetup'
import { makeProjection } from '../../test-fixtures'
import { EvidenceLibrary } from './EvidenceLibrary'
import { ValidationView } from './ValidationView'

function bootstrap(): WorkspaceBootstrap {
  const formal = makeProjection().validation.definitions[0]!
  return {
    application_build_id: '1'.repeat(64),
    default_actor: 'Graduate Engineer',
    default_mode: 'FORMAL',
    default_evidence_class: 'FORMAL',
    default_configuration_id: 'network-configuration-v1.1',
    default_configuration_version: '1.1',
    default_scenario_time: '2030-01-01T00:00:00.000Z',
    formal_test_id: 'VT-FML-N0-N5-001',
    formal_definition: formal,
    exploration_section_ids: ['SEC-A1', 'SEC-A2', 'SEC-A3', 'SEC-A4', 'SEC-B1', 'SEC-B2', 'SEC-B3', 'SEC-B4'],
    definition_count: 24,
    conceptual_boundary_notice: 'Fictional local engineering demonstrator.',
  }
}

function exploratoryProjection() {
  const base = makeProjection()
  const template = base.validation.definitions[0]!
  const definitions = ['VT-EXP-ALL-001', 'VT-EXP-ROLE-001', 'VT-EXP-SEPARATION-001'].map((testId) => ({
    ...template,
    definition: { ...template.definition, test_id: testId, title: testId, evidence_class: 'EXPLORATORY' as const, checkpoint_obligations: [{ checkpoint_id: 'CONTROLLED_RESULT', required_content: ['TOPOLOGY'] }] },
  }))
  return makeProjection({
    run: { ...base.run, mode: 'EXPLORATION', evidence_class: 'EXPLORATORY', fault_section_id: 'SEC-B2', workflow_stage: 'RESTORATION_ASSESSED' },
    validation: {
      ...base.validation,
      definitions: [...base.validation.definitions, ...definitions],
      library_executions: [],
      actions: definitions.map((definition) => ({ action_type: 'START_EXECUTION' as const, available: true, reason_code: 'AVAILABLE', reason: 'Start a separate EXPLORATORY execution.', test_id: definition.definition.test_id, case_id: null, validation_execution_id: null, checkpoint_id: null })),
    },
  })
}

describe('I8 Exploration and export presentation', () => {
  it('offers only configured v1.1 section selections as transient Exploration input', () => {
    const onStart = vi.fn()
    render(<RunSetup bootstrap={bootstrap()} busy={false} onStart={onStart} onStartInvestigation={vi.fn()} />)
    fireEvent.change(screen.getByRole('combobox', { name: 'Exploration fault section' }), { target: { value: 'SEC-B2' } })
    fireEvent.click(screen.getByRole('button', { name: 'Start exploratory v1.1 run' }))
    expect(onStart).toHaveBeenCalledWith('Graduate Engineer', 'EXPLORATION', 'SEC-B2')
    expect(screen.getByText(/cannot satisfy formal validation automatically/i)).toBeVisible()
  })

  it('keeps selected section and EXPLORATORY identity visible without calling it a formal N-state', () => {
    render(<ContextRibbon projection={exploratoryProjection()} />)
    const ribbon = within(screen.getByLabelText('Persistent run context'))
    expect(ribbon.getByText('EXPLORATION')).toBeVisible()
    expect(ribbon.getByText('EXPLORATORY')).toBeVisible()
    expect(ribbon.getByText('SEC-B2')).toBeVisible()
    expect(ribbon.getByTestId('exploration-stage')).toHaveTextContent('RESTORATION ASSESSED')
    expect(screen.queryByText('Formal state')).not.toBeInTheDocument()
  })

  it('presents exploratory definitions separately while retaining FORMAL-only progress', () => {
    render(<ValidationView projection={exploratoryProjection()} busy={false} onAction={vi.fn()} />)
    expect(screen.getByRole('heading', { name: 'Exploration evidence controls' })).toBeVisible()
    expect(screen.getAllByText('EXPLORATORY').length).toBeGreaterThanOrEqual(4)
    expect(screen.getByText(/21 FORMAL definitions; 0 FORMAL executions/i)).toBeVisible()
    expect(screen.queryByRole('button', { name: 'Start formal execution' })).not.toBeInTheDocument()
  })

  it('shows composite completeness and constituent provenance without inventing one run', () => {
    const projection = exploratoryProjection()
    projection.validation.composites = [{
      composite_result_id: '90000000-0000-0000-0000-000000000001', test_id: 'VT-EXP-ROLE-001',
      test_definition_version: '1.1', test_definition_sha256: '2'.repeat(64), catalogue_version: '1.1', catalogue_sha256: '3'.repeat(64),
      evidence_class: 'EXPLORATORY', application_build_id: '1'.repeat(64), configuration_id: 'network-configuration-v1.1', configuration_version: '1.1',
      required_case_ids: ['EXP-ROLE-A2', 'EXP-ROLE-B2', 'EXP-ROLE-A1', 'EXP-ROLE-A4'],
      constituent_links: [{ case_id: 'EXP-ROLE-B2', source_kind: 'EXECUTION_RESULT', validation_execution_id: '91000000-0000-0000-0000-000000000001', suspension_record_id: null, scenario_run_id: '92000000-0000-0000-0000-000000000001', case_definition_sha256: '4'.repeat(64), constituent_verdict: 'PASS', evidence_snapshot_ids: ['93000000-0000-0000-0000-000000000001'] }],
      completeness: { status: 'INCOMPLETE', required_case_ids: ['EXP-ROLE-A2', 'EXP-ROLE-B2', 'EXP-ROLE-A1', 'EXP-ROLE-A4'], present_case_ids: ['EXP-ROLE-B2'], missing_case_ids: ['EXP-ROLE-A2', 'EXP-ROLE-A1', 'EXP-ROLE-A4'], duplicate_case_ids: [], mismatched_case_ids: [], reasons: ['Missing required cases.'] },
      status: 'DRAFT', determination: null, determination_reason: 'Missing required cases.', source_record_references: ['validation-execution:9100'], created_at: '2030-01-01T01:00:00.000Z', finalised_at: null,
    }]
    const { container } = render(<ValidationView projection={projection} busy={false} onAction={vi.fn()} />)
    const view = within(container)
    expect(view.getByRole('heading', { name: 'Composite validation results' })).toBeVisible()
    expect(view.getByText(/Not one fictional run/i)).toBeVisible()
    const composite = view.getByRole('heading', { name: /VT-EXP-ROLE-001.*NOT DETERMINED/i }).closest('article')!
    expect(composite).toHaveTextContent(/EXP-ROLE-B2.*execution 91000000/i)
    expect(composite).toHaveTextContent(/Missing: EXP-ROLE-A2, EXP-ROLE-A1, EXP-ROLE-A4/i)
  })

  it('uses backend export eligibility and displays a new verified package record', async () => {
    const projection = exploratoryProjection()
    projection.validation.library_executions = []
    const api = {
      evidenceExportCandidates: vi.fn().mockResolvedValue([]),
      evidencePackages: vi.fn().mockResolvedValue([{ package_id: 'PKG-123456abcdef', validation_execution_id: '10000000-0000-0000-0000-000000000001', test_id: 'VT-EXP-ROLE-001', test_definition_version: '1.0', test_definition_sha256: '2'.repeat(64), evidence_class: 'EXPLORATORY', scenario_run_id: projection.run.scenario_run_id, configuration_id: projection.run.configuration_id, configuration_version: '1.1', application_build_id: '1'.repeat(64), generation_application_build_id: '1'.repeat(64), evidence_snapshot_ids: ['30000000-0000-0000-0000-000000000001'], manifest_sha256: '4'.repeat(64), archive_sha256: '5'.repeat(64), archive_path: 'evidence/exports/PKG-123456abcdef-EXPLORATORY.zip', verification_status: 'VERIFIED', source_record_references: ['scenario-run:test'] }]),
      generateEvidencePackage: vi.fn(),
    } as unknown as WorkspaceApi
    render(<EvidenceLibrary projection={projection} api={api} />)
    expect(await screen.findByText('PKG-123456abcdef')).toBeVisible()
    expect(screen.getByText('VERIFIED')).toBeVisible()
    expect(screen.getByRole('link', { name: 'Download verified ZIP' })).toHaveAttribute('href', '/api/v1/evidence-packages/PKG-123456abcdef/download')
    await waitFor(() => expect(api.evidenceExportCandidates).toHaveBeenCalled())
  })
})
