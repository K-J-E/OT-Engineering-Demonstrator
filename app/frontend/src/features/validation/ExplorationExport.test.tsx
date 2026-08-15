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
    default_actor: 'Simulated Reviewer',
    default_mode: 'FORMAL',
    default_evidence_class: 'FORMAL',
    default_configuration_id: 'network-configuration-v1.1',
    default_configuration_version: '1.1',
    default_scenario_time: '2030-01-01T00:00:00.000Z',
    formal_test_id: 'VT-FML-N0-N5-001',
    formal_definition: formal,
    exploration_section_ids: ['SEC-A1', 'SEC-A2', 'SEC-A3', 'SEC-A4', 'SEC-B1', 'SEC-B2', 'SEC-B3', 'SEC-B4'],
    definition_count: 24,
    conceptual_boundary_notice: 'Fictional local operational technology demonstrator — conceptual and simplified SCADA, ADMS and OMS functions only.',
  }
}

function exploratoryProjection() {
  const base = makeProjection()
  const template = base.validation.definitions[0]!
  const campaignCases: Record<string, Array<{ case_id: string; test_id: string; case_title: string; version: string; selected_fault_section_id: string; initial_conditions: Record<string, unknown>; comparison_expected_values: Record<string, unknown>; checkpoint_obligations: Array<{ checkpoint_id: string; required_content: string[] }> }>> = {
    'VT-EXP-ALL-001': [
      { case_id: 'EXP-ALL-A1', test_id: 'VT-EXP-ALL-001', case_title: 'SEC-A1 selection and incident boundary derivation', version: '1.1', selected_fault_section_id: 'SEC-A1', initial_conditions: {}, comparison_expected_values: {}, checkpoint_obligations: [] },
      { case_id: 'EXP-ALL-B2', test_id: 'VT-EXP-ALL-001', case_title: 'SEC-B2 selection and incident boundary derivation', version: '1.1', selected_fault_section_id: 'SEC-B2', initial_conditions: {}, comparison_expected_values: {}, checkpoint_obligations: [] },
    ],
    'VT-EXP-ROLE-001': [
      { case_id: 'EXP-ROLE-A2', test_id: 'VT-EXP-ROLE-001', case_title: 'Feeder A affected and Feeder B alternate', version: '1.1', selected_fault_section_id: 'SEC-A2', initial_conditions: {}, comparison_expected_values: {}, checkpoint_obligations: [] },
      { case_id: 'EXP-ROLE-B2', test_id: 'VT-EXP-ROLE-001', case_title: 'Feeder B affected and Feeder A alternate', version: '1.1', selected_fault_section_id: 'SEC-B2', initial_conditions: {}, comparison_expected_values: {}, checkpoint_obligations: [] },
    ],
  }
  const definitions = ['VT-EXP-ALL-001', 'VT-EXP-ROLE-001', 'VT-EXP-SEPARATION-001'].map((testId) => ({
    ...template,
    definition: { ...template.definition, test_id: testId, title: testId, evidence_class: 'EXPLORATORY' as const, checkpoint_obligations: [{ checkpoint_id: 'CONTROLLED_RESULT', required_content: ['TOPOLOGY'] }], constituent_cases: campaignCases[testId] ?? [] },
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

describe('I8 Trial and export presentation', () => {
  it('offers only configured v1.1 section selections as transient trial input', () => {
    const onStart = vi.fn()
    const rendered = render(<RunSetup bootstrap={bootstrap()} busy={false} existingInvestigation={false} onStartDefectInvestigation={vi.fn()} onStart={onStart} onResumeInvestigation={vi.fn()} onStartSafetyWalkthrough={vi.fn()} />)
    const sectionSelector = screen.getByRole('combobox', { name: 'Trial fault section' })
    expect(sectionSelector).toHaveValue('SEC-A2')
    expect(within(sectionSelector).getByRole('option', { name: 'SEC-A2 (recommended for first run)' })).toBeVisible()
    expect(within(sectionSelector).getByRole('option', { name: 'SEC-A3 (recommended for first run)' })).toBeVisible()
    expect(within(sectionSelector).getByRole('option', { name: 'SEC-B2 (recommended for first run)' })).toBeVisible()
    expect(within(sectionSelector).getByRole('option', { name: 'SEC-B3 (recommended for first run)' })).toBeVisible()
    expect(within(sectionSelector).getByRole('option', { name: 'SEC-A1' })).toBeVisible()
    expect(Array.from(rendered.container.querySelectorAll('.setup-card h2')).map((heading) => heading.textContent).slice(0, 2)).toEqual([
      'Test a selected fault location',
      'Expose a seeded configuration defect—and prove its correction',
    ])
    expect(screen.getByRole('heading', { name: 'Choose a walkthrough to begin' })).toBeVisible()
    expect(screen.queryByLabelText('Actor / reviewer')).not.toBeInTheDocument()
    fireEvent.change(sectionSelector, { target: { value: 'SEC-B2' } })
    fireEvent.click(screen.getByRole('button', { name: 'Start trial' }))
    expect(onStart).toHaveBeenCalledWith('Simulated Reviewer', 'EXPLORATION', 'SEC-B2')
    expect(screen.getByText('Trials:', { exact: true })).toBeVisible()
    expect(screen.queryByText('Exploration:', { exact: true })).not.toBeInTheDocument()
  })

  it('offers the accepted stale-evidence safety walkthrough without changing engineering rules', () => {
    const onStartSafetyWalkthrough = vi.fn()
    const rendered = render(<RunSetup bootstrap={bootstrap()} busy={false} existingInvestigation={false} onStartDefectInvestigation={vi.fn()} onStart={vi.fn()} onResumeInvestigation={vi.fn()} onStartSafetyWalkthrough={onStartSafetyWalkthrough} />)
    const setup = within(rendered.container)
    fireEvent.click(setup.getByRole('button', { name: 'Start stale-evidence walkthrough' }))
    expect(onStartSafetyWalkthrough).toHaveBeenCalledWith('Simulated Reviewer')
    expect(setup.getByText(/stale readings cannot prove isolation/i)).toBeVisible()
  })

  it('keeps a preserved investigation within the combined validation story', () => {
    const onResumeInvestigation = vi.fn()
    const rendered = render(<RunSetup bootstrap={bootstrap()} busy={false} existingInvestigation onStartDefectInvestigation={vi.fn()} onStart={vi.fn()} onResumeInvestigation={onResumeInvestigation} onStartSafetyWalkthrough={vi.fn()} />)
    const setup = within(rendered.container)
    expect(setup.getByRole('heading', { name: 'Expose a seeded configuration defect—and prove its correction' })).toBeVisible()
    expect(setup.queryByRole('heading', { name: 'Begin DEF-001 investigation' })).not.toBeInTheDocument()
    fireEvent.click(setup.getByRole('button', { name: 'Resume preserved defect investigation' }))
    expect(onResumeInvestigation).toHaveBeenCalledWith('Simulated Reviewer')
  })

  it('starts the combined validation story directly from the preserved v1.0 defect', () => {
    const onStartDefectInvestigation = vi.fn()
    const rendered = render(<RunSetup bootstrap={bootstrap()} busy={false} existingInvestigation={false} onStartDefectInvestigation={onStartDefectInvestigation} onStart={vi.fn()} onResumeInvestigation={vi.fn()} onStartSafetyWalkthrough={vi.fn()} />)
    const setup = within(rendered.container)
    fireEvent.click(setup.getByRole('button', { name: 'Start defect walkthrough' }))
    expect(onStartDefectInvestigation).toHaveBeenCalledWith('Simulated Reviewer')
    expect(setup.getByText(/directly against preserved GIS configuration v1.0/i)).toBeVisible()
  })

  it('keeps the selected section and trial identity visible without presenting a validation checkpoint', () => {
    render(<ContextRibbon projection={exploratoryProjection()} />)
    const ribbon = within(screen.getByLabelText('Persistent run context'))
    expect(ribbon.getByText('TRIAL')).toBeVisible()
    expect(ribbon.getByText('TRIAL RECORD')).toBeVisible()
    expect(ribbon.getByText('SEC-B2')).toBeVisible()
    expect(ribbon.getByTestId('exploration-stage')).toHaveTextContent('RESTORATION ASSESSED')
    expect(screen.queryByText('Formal state')).not.toBeInTheDocument()
  })

  it('keeps assurance simple while exposing the validation procedure separately', () => {
    render(<ValidationView projection={makeProjection()} busy={false} onAction={vi.fn()} onContinue={vi.fn()} />)
    expect(screen.getByRole('heading', { name: 'How each operating stage was checked' })).toBeVisible()
    expect(screen.getByRole('heading', { name: 'Operating assurance and system validation are different' })).toBeVisible()
    expect(screen.getByRole('heading', { name: 'How the validation result is produced' })).toBeVisible()
    expect(screen.getByLabelText('Controlled validation procedure').querySelectorAll('article')).toHaveLength(4)
    expect(screen.getByText('Lock the validation basis')).toBeVisible()
    expect(screen.getByText('Evaluate controlled criteria')).toBeVisible()
  })

  it('presents a trial report with assurance and its own technical traceability', () => {
    const { container } = render(<ValidationView projection={exploratoryProjection()} busy={false} onAction={vi.fn()} onContinue={vi.fn()} />)
    const view = within(container)
    expect(view.getByRole('heading', { name: 'Validation of the operating logic for this case' })).toBeVisible()
    expect(view.getByRole('heading', { name: 'How each operating stage was checked' })).toBeVisible()
    expect(container.querySelector('.stage-validation-grid')?.querySelectorAll('article')).toHaveLength(6)
    expect(view.getByText(/result remains separate and is never counted as controlled validation evidence/i)).toBeVisible()
    const report = within(container.querySelector('[aria-labelledby="exploration-evidence-title"]')!)
    expect(report.getByText('Technical test traceability')).toBeVisible()
    expect(view.getByRole('heading', { name: 'How the trial evidence is controlled and extended' })).toBeVisible()
    expect(view.getByRole('heading', { name: 'Multi-scenario validation campaigns' })).toBeVisible()
    expect(view.getByRole('article', { name: 'Validation campaign: All represented fault locations' })).toBeVisible()
    expect(view.getByRole('article', { name: 'Validation campaign: Feeder-role reversal and varied restoration outcomes' })).toBeVisible()
    expect(view.queryByText('Formal progress remains separate')).not.toBeInTheDocument()
    expect(view.queryByRole('heading', { name: 'Exploration validation outcome' })).not.toBeInTheDocument()
    expect(view.queryByRole('button', { name: 'Start the validation record' })).not.toBeInTheDocument()
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
    const { container } = render(<ValidationView projection={projection} busy={false} onAction={vi.fn()} onContinue={vi.fn()} />)
    const view = within(container)
    const campaign = within(view.getByRole('article', { name: 'Validation campaign: Feeder-role reversal and varied restoration outcomes' }))
    fireEvent.click(campaign.getByText('Campaign composition and records'))
    expect(campaign.getByText('Incomplete constituent membership')).toBeVisible()
    expect(campaign.getByText('Present cases:').closest('p')).toHaveTextContent(/EXP-ROLE-B2/i)
    expect(campaign.getByText('Missing cases:').closest('p')).toHaveTextContent(/EXP-ROLE-A2, EXP-ROLE-A1, EXP-ROLE-A4/i)
    expect(campaign.getByText(/Run 92000000/i)).toHaveTextContent(/source 91000000/i)
  })

  it('uses backend export eligibility and displays a new verified package record', async () => {
    const projection = exploratoryProjection()
    projection.validation.library_executions = []
    const api = {
      evidenceExportCandidates: vi.fn().mockResolvedValue([]),
      evidencePackages: vi.fn().mockResolvedValue([{ package_id: 'PKG-123456abcdef', validation_execution_id: '10000000-0000-0000-0000-000000000001', test_id: 'VT-EXP-ROLE-001', test_definition_version: '1.0', test_definition_sha256: '2'.repeat(64), evidence_class: 'EXPLORATORY', scenario_run_id: projection.run.scenario_run_id, configuration_id: projection.run.configuration_id, configuration_version: '1.1', application_build_id: '1'.repeat(64), generation_application_build_id: '1'.repeat(64), evidence_snapshot_ids: ['30000000-0000-0000-0000-000000000001'], manifest_sha256: '4'.repeat(64), archive_sha256: '5'.repeat(64), archive_path: 'evidence/exports/PKG-123456abcdef-EXPLORATORY.zip', verification_status: 'VERIFIED', source_record_references: ['scenario-run:test'] }]),
      generateEvidencePackage: vi.fn(),
    } as unknown as WorkspaceApi
    render(<EvidenceLibrary projection={projection} api={api} onReturnToOperational={vi.fn()} />)
    expect(await screen.findByText('Latest-run evidence package')).toBeVisible()
    expect(screen.getByText('Verified')).toBeVisible()
    expect(screen.getByText('PKG-123456abcdef')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Download evidence package (.zip)' })).toHaveAttribute('href', '/api/v1/evidence-packages/PKG-123456abcdef/download')
    await waitFor(() => expect(api.evidenceExportCandidates).toHaveBeenCalled())
  })
})
