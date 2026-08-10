import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import type { WorkspaceApi } from '../../api/client'
import type { InvestigationWorkspace as InvestigationModel } from '../../api/contracts'
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

describe('I7 investigation presentation', () => {
  it('reveals consequence-to-source evidence progressively before record action', () => {
    render(<InvestigationWorkspace api={{} as WorkspaceApi} failureExecutionId="30000000-0000-0000-0000-000000000001" actor="Reviewer" initial={model()} onUpdate={vi.fn()} />)
    expect(screen.getByText('Evidence step 1')).toBeVisible()
    expect(screen.queryByText('SEC-B3 instead of SEC-A2')).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Record DEF-001 after evidence review' })).toBeDisabled()
    for (let index = 0; index < 5; index += 1) fireEvent.click(screen.getByRole('button', { name: 'Review next evidence step' }))
    expect(screen.getByText('SEC-B3 instead of SEC-A2')).toBeVisible()
    expect(screen.getByText('connectivity_edges.EDGE-SW-A23-1.endpoint_a_id')).toBeVisible()
    fireEvent.click(screen.getByRole('button', { name: 'Review next evidence step' }))
    expect(screen.getByRole('button', { name: 'Record DEF-001 after evidence review' })).toBeEnabled()
  })
})
