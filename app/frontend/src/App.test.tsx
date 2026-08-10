import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { ActionPanel } from './features/operational/ActionPanel'
import { ContextRibbon } from './features/operational/ContextRibbon'
import { EntityInspector } from './features/operational/EntityInspector'
import { RestorationView } from './features/restoration/RestorationView'
import { TelemetryView } from './features/telemetry-events/TelemetryView'
import { ValidationView } from './features/validation/ValidationView'
import { makeProjection, permittedAssessment } from './test-fixtures'

describe('I6 engineering presentation components', () => {
  it('keeps the approved context fields continuously explicit', () => {
    render(<ContextRibbon projection={makeProjection()} />)
    expect(screen.getAllByText('FORMAL')).toHaveLength(2)
    expect(screen.getByText('SEC-A2')).toBeVisible()
    expect(screen.getByText('N4')).toBeVisible()
    expect(screen.getByText('PERMITTED')).toBeVisible()
    expect(screen.getByText('4')).toBeVisible()
    expect(screen.getByTestId('full-run-id')).toHaveTextContent('20000000-0000-0000-0000-000000000001')
    expect(screen.getByTestId('full-run-id')).toBeVisible()
  })

  it('presents configured, observed, derived and fault states as separate authorities', () => {
    render(<EntityInspector node={makeProjection().network_nodes[1]} />)
    expect(screen.getByRole('heading', { name: 'Configured truth' })).toBeVisible()
    expect(screen.getByRole('heading', { name: 'Observed SCADA evidence' })).toBeVisible()
    expect(screen.getByRole('heading', { name: 'Derived engineering state' })).toBeVisible()
    expect(screen.getAllByText('OPEN')).toHaveLength(2)
    expect(screen.getByText(/current projection is not an immutable validation evidence snapshot/i)).toBeVisible()
  })

  it('uses backend availability and displays unavailable-action reasons', () => {
    const onExecute = vi.fn()
    render(<ActionPanel actions={makeProjection().allowed_actions} busyActionId={null} onExecute={onExecute} />)
    fireEvent.click(screen.getByRole('button', { name: /^Execute permitted restoration / }))
    expect(onExecute).toHaveBeenCalledOnce()
    expect(screen.getByRole('button', { name: 'Restore normal source BRK-A' })).toBeDisabled()
    expect(screen.getByText('Requires current derived isolation proof at N2.')).toBeVisible()
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
    expect(screen.getByText(/quality and freshness remain separate/i)).toBeVisible()
  })

  it.each([
    ['BLOCKED', 'not an engineering rejection'],
    ['REJECTED', 'evidence is sufficient'],
    ['PERMITTED', 'every applicable evidence and engineering permissive passed'],
  ] as const)('explains %s as an engineering outcome rather than an application error', (outcome, phrase) => {
    const assessment = { ...permittedAssessment, outcome, reason_codes: [`${outcome}_REASON`] }
    if (outcome !== 'PERMITTED') assessment.calculation = outcome === 'BLOCKED' ? null : permittedAssessment.calculation
    render(<RestorationView projection={makeProjection({ restoration_assessments: [assessment], summary: { ...makeProjection().summary, current_assessment_status: outcome } })} busyActionId={null} onExecute={vi.fn()} />)
    expect(screen.getByRole('heading', { name: outcome })).toBeVisible()
    expect(screen.getByText(new RegExp(phrase, 'i'))).toBeVisible()
  })

  it('separates 21 FORMAL definitions from the total catalogue and does not claim execution or pass', () => {
    const projection = makeProjection()
    const template = projection.validation.definitions[0]!
    projection.validation.definitions = Array.from({ length: 24 }, (_, index) => ({
      ...template,
      definition: { ...template.definition, test_id: `VT-FML-FIXTURE-${String(index + 1).padStart(3, '0')}` },
    }))
    render(<ValidationView projection={projection} busy={false} onAction={vi.fn()} />)
    expect(screen.getByText(/21 of 24 total controlled catalogue definitions/i)).toBeVisible()
    expect(screen.getAllByText('21').length).toBeGreaterThanOrEqual(2)
    expect(screen.getByText('Definitions are not executions.')).toBeVisible()
    expect(screen.getAllByText('0').length).toBeGreaterThanOrEqual(3)
    expect(screen.getByText(/no pass\/fail has been created|no VT-FML/i)).toBeVisible()
  })
})
