import { fireEvent, render, screen, within } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import type { WorkspaceApi } from '../../api/client'
import type { InvestigationWorkspace as InvestigationModel, ValidationExecutionSummary } from '../../api/contracts'
import { makeProjection } from '../../test-fixtures'
import { InvestigationWorkspace } from './InvestigationWorkspace'

function model(): InvestigationModel {
  const execution = makeProjection().validation.run_executions[0]?.execution ?? {
    validation_execution_id: '30000000-0000-0000-0000-000000000001', test_id: 'VT-TOP-DEF-001', test_definition_version: '1.0', test_definition_sha256: '2'.repeat(64), catalogue_sha256: '3'.repeat(64), scenario_run_id: '20000000-0000-0000-0000-000000000001', scenario_mode: 'FORMAL' as const, evidence_class: 'FORMAL' as const, configuration_id: 'network-configuration-v1.0', configuration_version: '1.0', application_build_id: '1'.repeat(64), status: 'FINALISED' as const, started_scenario_time: '2030-01-01T00:00:00.000Z', finalised_scenario_time: '2030-01-01T00:00:10.000Z', expected_result_statement: '850 expected', expected_comparison_values: {}, observed_result: { affected_customer_count: 400 }, calculations: {}, evidence_snapshot_ids: ['40000000-0000-0000-0000-000000000001'], verdict: 'FAIL', verdict_reason: 'mismatch', links: {},
  }
  const steps = Array.from({ length: 7 }, (_, index) => ({ step_id: `INV-0${index + 1}`, title: index === 5 ? 'Immutable configuration comparison' : `Evidence step ${index + 1}`, facts: [{ label: 'Finding', value: index === 5 ? 'SEC-B3 instead of SEC-A2' : `Owned evidence ${index + 1}` }], source_record_references: [`record:${index + 1}`] }))
  return {
    original_failure: { execution, evidence_snapshots: [] }, steps,
    configuration_comparison: { defective: { configuration_id: 'network-configuration-v1.0', version: '1.0', package_sha256: 'a'.repeat(64), data_sha256: 'b'.repeat(64), schema_sha256: 'c'.repeat(64) }, corrected: { configuration_id: 'network-configuration-v1.1', version: '1.1', package_sha256: 'd'.repeat(64), data_sha256: 'e'.repeat(64), schema_sha256: 'c'.repeat(64) }, differences: [{ path: 'connectivity_edges.EDGE-SW-A23-1.endpoint_a_id', before: 'SEC-B3', after: 'SEC-A2' }], unchanged_information_classes: ['loads'] },
    defect_record: null, correction_record: null, direct_repeat: null, regression: null, repeat_links: [], same_build_proven: false, conceptual_boundary_notice: 'Controlled and read-only.',
    actions: [
      { action_type: 'RECORD_DEFECT', available: true, reason_code: 'AVAILABLE', reason: 'Review.' },
      { action_type: 'RECORD_CORRECTION', available: false, reason_code: 'REQUIRES_DEFECT', reason: 'Wait.' },
      { action_type: 'RUN_DIRECT_REPEAT', available: false, reason_code: 'REQUIRES_CORRECTION', reason: 'Wait.' },
      { action_type: 'RUN_REGRESSION', available: false, reason_code: 'REQUIRES_DIRECT_REPEAT_PASS', reason: 'Wait.' },
    ],
  }
}

function sameBuildModel(includeRegression: boolean): InvestigationModel {
  const workspace = model()
  const direct: ValidationExecutionSummary = {
    execution: {
      ...workspace.original_failure.execution,
      validation_execution_id: '30000000-0000-0000-0000-000000000002',
      configuration_id: 'network-configuration-v1.1',
      configuration_version: '1.1',
      observed_result: { affected_customer_count: 850 },
      verdict: 'PASS',
    },
    evidence_snapshots: [],
  }
  const regression: ValidationExecutionSummary = {
    execution: {
      ...direct.execution,
      validation_execution_id: '30000000-0000-0000-0000-000000000003',
      test_id: 'VT-FML-N0-N5-001',
      status: 'ACTIVE',
      finalised_scenario_time: null,
      observed_result: null,
      verdict: null,
      verdict_reason: null,
    },
    evidence_snapshots: [],
  }
  return {
    ...workspace,
    direct_repeat: direct,
    regression: includeRegression ? regression : null,
    same_build_proven: true,
  }
}

describe('I7 investigation presentation', () => {
  it('reveals consequence-to-source evidence progressively before record action', () => {
    render(<InvestigationWorkspace api={{} as WorkspaceApi} failureExecutionId="30000000-0000-0000-0000-000000000001" actor="Reviewer" initial={model()} onUpdate={vi.fn()} />)
    expect(screen.getByRole('heading', { name: 'Confirm the discrepancy' })).toBeVisible()
    expect(screen.queryByText('SEC-B3 instead of SEC-A2')).not.toBeInTheDocument()
    for (let index = 0; index < 3; index += 1) fireEvent.click(screen.getByRole('button', { name: 'Continue investigation' }))
    expect(screen.getByRole('heading', { name: 'The fault is in one GIS connectivity endpoint' })).toBeVisible()
    expect(screen.getByText('SW-A23 connected to SEC-B3')).toBeVisible()
    expect(screen.getByText('connectivity_edges.EDGE-SW-A23-1.endpoint_a_id')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Confirm and record the identified fault' })).toBeEnabled()
  })

  it('limits same-build wording to failure and direct repeat before regression', () => {
    const rendered = render(<InvestigationWorkspace api={{} as WorkspaceApi} failureExecutionId="30000000-0000-0000-0000-000000000001" actor="Reviewer" initial={sameBuildModel(false)} onUpdate={vi.fn()} />)
    const proof = within(rendered.container).getByTestId('same-build-proof')
    expect(proof).toHaveTextContent('The v1.0 failure and v1.1 focused repeat used the same application version; only the network configuration changed.')
    expect(proof).not.toHaveTextContent('corrected full scenario')
  })

  it('includes corrected regression only after its preserved record exists', () => {
    const rendered = render(<InvestigationWorkspace api={{} as WorkspaceApi} failureExecutionId="30000000-0000-0000-0000-000000000001" actor="Reviewer" initial={sameBuildModel(true)} onUpdate={vi.fn()} />)
    expect(within(rendered.container).getByTestId('same-build-proof')).toHaveTextContent('The v1.0 failure and v1.1 focused repeat used the same application version; only the network configuration changed.')
  })
})
