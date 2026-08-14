import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { ActionPanel } from './features/operational/ActionPanel'
import { ContextRibbon } from './features/operational/ContextRibbon'
import { EntityInspector } from './features/operational/EntityInspector'
import { RestorationView } from './features/restoration/RestorationView'
import { TelemetryView } from './features/telemetry-events/TelemetryView'
import { ValidationView } from './features/validation/ValidationView'
import { makeProjection, permittedAssessment } from './test-fixtures'
import { ControlledSurface } from './components/ControlledSurface'
import controlledSurfaces from './controlled-surfaces.v1.json'

describe('I6 engineering presentation components', () => {
  it('renders the exact eight controlled surfaces with their frozen notice and identity profiles', () => {
    expect(controlledSurfaces.surfaces.map((surface) => surface.surface_id)).toEqual([
      'Start / Run Setup', 'Operational Workspace', 'Telemetry & Events',
      'Restoration Assessment', 'Formal Validation', 'Evidence Library',
      'Defect Investigation', 'Engineering Basis',
    ])
    for (const surface of controlledSurfaces.surfaces) {
      const rendered = render(<ControlledSurface
        surfaceId={surface.surface_id}
        identityProfile={surface.required_identity_profile}
        fixedNotice={surface.fixed_notice}
      ><span>content</span></ControlledSurface>)
      const region = rendered.container.querySelector('[data-controlled-surface]')
      expect(region).toHaveAttribute('data-controlled-surface', surface.surface_id)
      expect(region).toHaveAttribute('data-identity-profile', surface.required_identity_profile)
      expect(screen.getByText(surface.fixed_notice)).toBeVisible()
      rendered.unmount()
    }
  })
  it('keeps the approved context fields continuously explicit', () => {
    render(<ContextRibbon projection={makeProjection()} />)
    expect(screen.getAllByText('FORMAL')).toHaveLength(2)
    expect(screen.getByText('SEC-A2')).toBeVisible()
    expect(screen.getByTestId('formal-state')).toHaveTextContent('N4 · Alternate supply assessed')
    expect(screen.getByText('PERMITTED')).toBeVisible()
    expect(screen.getByText('4')).toBeVisible()
    expect(screen.getByTestId('full-run-id')).toHaveTextContent('20000000-0000-0000-0000-000000000001')
    expect(screen.getByTestId('full-run-id')).toBeVisible()
  })

  it('presents configured, observed, derived and fault states as separate authorities', () => {
    render(<EntityInspector node={makeProjection().network_nodes[1]} />)
    expect(screen.getByRole('heading', { name: 'Network record' })).toBeVisible()
    expect(screen.getByRole('heading', { name: 'Latest telemetry' })).toBeVisible()
    expect(screen.getByRole('heading', { name: 'Calculated operating state' })).toBeVisible()
    expect(screen.getAllByText('OPEN')).toHaveLength(2)
    expect(screen.getByText(/become a saved validation record only when/i)).toBeVisible()
  })

  it('uses system availability, plain-language reasons and page-owned action routing', () => {
    const onExecute = vi.fn()
    const onNavigate = vi.fn()
    render(<ActionPanel actions={makeProjection().allowed_actions} faultSectionId="SEC-A2" busyActionId={null} onExecute={onExecute} onNavigate={onNavigate} />)
    fireEvent.click(screen.getByRole('button', { name: 'Restore eligible healthy sections from the alternate feeder' }))
    expect(onNavigate).toHaveBeenCalledWith('restoration')
    expect(onExecute).not.toHaveBeenCalled()
    expect(screen.getByRole('button', { name: /Reclose BRK-A to restore the healthy upstream section/ })).toBeDisabled()
    expect(screen.getByText(/after both boundary switches have trustworthy open indications/i)).toBeVisible()
  })

  it('shows quality and freshness independently for fresh, stale, uncertain, bad and future evidence', () => {
    const base = makeProjection()
    const rows = [
      base.telemetry[0],
      { ...base.telemetry[0], point_id: 'PT-STALE', entity_id: 'SW-A12', age_ms: 60001, freshness: 'STALE' as const, overall_valid: false, reason_codes: ['STALE_TELEMETRY'] },
      { ...base.telemetry[0], point_id: 'PT-UNCERTAIN', entity_id: 'SW-A23', quality: 'UNCERTAIN' as const, quality_valid: false, overall_valid: false, reason_codes: ['QUALITY_UNCERTAIN'] },
      { ...base.telemetry[0], point_id: 'PT-BAD', entity_id: 'BRK-B', quality: 'BAD' as const, quality_valid: false, overall_valid: false, reason_codes: ['QUALITY_BAD'] },
      { ...base.telemetry[0], point_id: 'PT-FUTURE', entity_id: 'TS-01', age_ms: -1, freshness: 'INVALID_TIMESTAMP' as const, timestamp_valid: false, overall_valid: false, reason_codes: ['FUTURE_TIMESTAMP'] },
    ]
    render(<TelemetryView projection={makeProjection({ telemetry: rows })} />)
    expect(screen.getByText('60.001 s')).toBeVisible()
    expect(screen.getByText('UNCERTAIN')).toBeVisible()
    expect(screen.getByText('BAD')).toBeVisible()
    expect(screen.getByText('INVALID TIMESTAMP')).toBeVisible()
    expect(screen.getByText(/quality and age answer different questions/i)).toBeVisible()
  })

  it.each([
    ['BLOCKED', 'cannot make a safe decision'],
    ['REJECTED', 'network or capacity checks did not pass'],
    ['PERMITTED', 'every required safety, network, telemetry and capacity check passed'],
  ] as const)('explains %s as an engineering outcome rather than an application error', (outcome, phrase) => {
    const assessment = { ...permittedAssessment, outcome, reason_codes: [`${outcome}_REASON`] }
    if (outcome !== 'PERMITTED') assessment.calculation = outcome === 'BLOCKED' ? null : permittedAssessment.calculation
    render(<RestorationView projection={makeProjection({ restoration_assessments: [assessment], summary: { ...makeProjection().summary, current_assessment_status: outcome } })} busyActionId={null} validationBusy={false} onExecute={vi.fn()} onSaveEvidence={vi.fn()} onViewEvidence={vi.fn()} />)
    expect(screen.getByRole('heading', { name: outcome })).toBeVisible()
    expect(screen.getByText(new RegExp(phrase, 'i'))).toBeVisible()
  })

  it('shows only the selected walkthrough instead of catalogue-wide validation jargon', () => {
    const projection = makeProjection()
    const template = projection.validation.definitions[0]!
    projection.validation.definitions = [template, ...Array.from({ length: 23 }, (_, index) => ({
      ...template,
      definition: { ...template.definition, test_id: `VT-FML-FIXTURE-${String(index + 1).padStart(3, '0')}` },
    }))]
    render(<ValidationView projection={projection} busy={false} onAction={vi.fn()} onContinue={vi.fn()} />)
    expect(screen.getByRole('heading', { name: 'Validation of the operating logic' })).toBeVisible()
    expect(screen.getByText('0 of 6 states saved')).toBeVisible()
    expect(screen.getByRole('heading', { name: 'How each operating stage was checked' })).toBeVisible()
    expect(screen.getByText(/A fault trips the feeder, the fault can be isolated/i)).toBeVisible()
    expect(screen.getByRole('heading', { name: 'Operating assurance and system validation are different' })).toBeVisible()
    expect(screen.queryByRole('heading', { name: 'Feeder fault, isolation and restoration' })).not.toBeInTheDocument()
    expect(screen.queryByText(/21 of 24 total controlled catalogue definitions/i)).not.toBeInTheDocument()
    expect(screen.getByText(/evidence record has not been created yet/i)).toBeVisible()
  })

  it('presents DC-006 defined criteria separately from achieved evidence', () => {
    const projection = makeProjection()
    const definition = projection.validation.definitions[0]!.definition
    definition.determination_method = {
      method_id: 'DM-FML-N0-N5-001', version: '1.0', method_sha256: 'a'.repeat(64),
      test_id: definition.test_id, case_id: null, evidence_class: 'FORMAL',
      context_kind: 'SCENARIO_EXECUTION', required_context_roles: ['FORMAL_CORRECTED_RUN'],
      checkpoint_roles: ['N0', 'N1', 'N2', 'N3', 'N4', 'N5'], aggregate_rule: 'Backend aggregate only.',
      criterion_ids: ['FML-N0-01'], controlled_fixture: null,
      criteria: [{ criterion_id: 'FML-N0-01', version: '1.0', criterion_sha256: 'b'.repeat(64), kind: 'MACHINE_COMPARISON', test_id: definition.test_id, case_id: null, context_checkpoint: 'N0', expected_value: 'N0 expected state', source_selector: 'EvidenceSnapshot[N0]', operator: 'CANONICAL_RECORD_EQUAL', normalisation: 'exact', required_evidence: 'bound source', evidence_roles: ['TOPOLOGY'], requirement_ids: ['REQ-TOP-001'] }],
    }
    render(<ValidationView projection={projection} busy={false} onAction={vi.fn()} onContinue={vi.fn()} />)
    expect(screen.getAllByText('Technical test traceability').at(-1)).toBeVisible()
    expect(screen.getAllByText(/DM-FML-N0-N5-001 · SCENARIO_EXECUTION/i).at(-1)).toBeInTheDocument()
    expect(screen.getAllByText(/FML-N0-01 · MACHINE COMPARISON/i).at(-1)).toBeInTheDocument()
  })
})
