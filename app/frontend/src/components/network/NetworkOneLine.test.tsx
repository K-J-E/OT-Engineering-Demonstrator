import { render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { WorkspaceNode } from '../../api/contracts'
import { makeProjection } from '../../test-fixtures'

const { cytoscapeMock, graphMock } = vi.hoisted(() => {
  const graph = { on: vi.fn(), destroy: vi.fn(), getElementById: vi.fn(() => ({ select: vi.fn() })) }
  return { graphMock: graph, cytoscapeMock: vi.fn((_options: unknown) => graph) }
})
vi.mock('cytoscape', () => ({ default: cytoscapeMock }))

import { NetworkOneLine } from './NetworkOneLine'

function networkNode(
  entityId: string,
  entityType: WorkspaceNode['configured']['entity_type'],
  feederId: string | null,
  energised: boolean | null,
): WorkspaceNode {
  const base = makeProjection().network_nodes[0]!
  return {
    ...base,
    entity_id: entityId,
    configured: {
      ...base.configured,
      entity_id: entityId,
      entity_type: entityType,
      name: entityId,
      feeder_id: feederId,
      configured_load_kw: entityType === 'SECTION' ? 100 : null,
    },
    observed: entityType === 'SWITCHING_DEVICE' ? {
      point_id: `PT-${entityId}`,
      value: 'CLOSED',
      quality: 'GOOD',
      timestamp: '2030-01-01T00:00:00.000Z',
      age_ms: 0,
      freshness: 'FRESH',
      overall_valid: true,
      reason_codes: [],
    } : null,
    derived: {
      energised,
      source_feeder_ids: energised === true && feederId !== null ? [feederId] : [],
      source_path_node_ids: [],
      current_source_availability: entityType === 'SOURCE' ? 'AVAILABLE' : null,
    },
    fault_status: entityType === 'SECTION' ? 'NOT_FAULTED' : 'NOT_APPLICABLE',
  }
}

describe('fixed one-line', () => {
  beforeEach(() => { cytoscapeMock.mockClear(); graphMock.on.mockClear() })

  it('uses backend positions and connectivity with drag/edit disabled', () => {
    const projection = makeProjection()
    const { container } = render(<NetworkOneLine nodes={projection.network_nodes} edges={projection.network_edges} selectedEntityId={null} onSelect={vi.fn()} />)
    expect(container.querySelector('[data-topology-editable="false"]')).toBeInTheDocument()
    const options = cytoscapeMock.mock.calls[0]![0] as {
      autoungrabify: boolean
      boxSelectionEnabled: boolean
      userPanningEnabled: boolean
      userZoomingEnabled: boolean
      layout: { name: string }
      elements: Array<{ grabbable?: boolean }>
    }
    expect(options.autoungrabify).toBe(true)
    expect(options.boxSelectionEnabled).toBe(false)
    expect(options.userPanningEnabled).toBe(false)
    expect(options.userZoomingEnabled).toBe(false)
    expect(options.layout.name).toBe('preset')
    expect(options.elements.every((element: { grabbable?: boolean }) => element.grabbable === false)).toBe(true)
    expect(container.querySelector('[data-user-zoom="disabled"]')).toBeInTheDocument()
    expect(screen.getByText('Accessible network state table')).toBeVisible()
    expect(screen.getByText('Select an entity to inspect it below.')).toBeVisible()
    expect(screen.queryByText(/does not capture page scrolling or change connectivity/i)).not.toBeInTheDocument()
  })

  it('colours closed connections from calculated energisation rather than switch continuity alone', () => {
    const nodes = [
      networkNode('SEC-B1', 'SECTION', 'FDR-B', true),
      networkNode('SEC-B2', 'SECTION', 'FDR-B', false),
    ]
    render(<NetworkOneLine nodes={nodes} edges={[
      { edge_id: 'EDGE-UPSTREAM', endpoint_a_id: 'SW-UPSTREAM', endpoint_b_id: 'SEC-B1', semantics: 'CONNECTIVITY', active: true },
      { edge_id: 'EDGE-DOWNSTREAM', endpoint_a_id: 'SW-DOWNSTREAM', endpoint_b_id: 'SEC-B2', semantics: 'CONNECTIVITY', active: true },
      { edge_id: 'EDGE-OPEN', endpoint_a_id: 'SEC-B1', endpoint_b_id: 'SW-OPEN', semantics: 'CONNECTIVITY', active: false },
    ]} selectedEntityId={null} onSelect={vi.fn()} />)
    const options = cytoscapeMock.mock.calls[0]![0] as { elements: Array<{ data: { id: string }; classes?: string }> }
    expect(options.elements.find((element) => element.data.id === 'EDGE-UPSTREAM')?.classes).toBe('energised-edge')
    expect(options.elements.find((element) => element.data.id === 'EDGE-DOWNSTREAM')?.classes).toBe('de-energised-edge')
    expect(options.elements.find((element) => element.data.id === 'EDGE-OPEN')?.classes).toBe('de-energised-edge')
  })

  it('colours each source-to-breaker connection from the state of its own feeder', () => {
    const nodes = [
      networkNode('ZS-01', 'SOURCE', null, null),
      networkNode('BRK-A', 'SWITCHING_DEVICE', 'FDR-A', null),
      networkNode('BRK-B', 'SWITCHING_DEVICE', 'FDR-B', null),
      networkNode('SEC-A1', 'SECTION', 'FDR-A', true),
      networkNode('SEC-B1', 'SECTION', 'FDR-B', false),
    ]
    render(<NetworkOneLine nodes={nodes} edges={[
      { edge_id: 'EDGE-BRK-A-1', endpoint_a_id: 'ZS-01', endpoint_b_id: 'BRK-A', semantics: 'CONNECTIVITY', active: true },
      { edge_id: 'EDGE-BRK-B-1', endpoint_a_id: 'ZS-01', endpoint_b_id: 'BRK-B', semantics: 'CONNECTIVITY', active: true },
    ]} selectedEntityId={null} onSelect={vi.fn()} />)
    const options = cytoscapeMock.mock.calls[0]![0] as { elements: Array<{ data: { id: string }; classes?: string }> }
    expect(options.elements.find((element) => element.data.id === 'EDGE-BRK-A-1')?.classes).toBe('energised-edge')
    expect(options.elements.find((element) => element.data.id === 'EDGE-BRK-B-1')?.classes).toBe('de-energised-edge')
  })

  it('places the seeded v1.0 note beside the uninterrupted energised defect edge', () => {
    const nodes = [
      networkNode('SW-A23', 'SWITCHING_DEVICE', 'FDR-A', null),
      networkNode('SEC-B3', 'SECTION', 'FDR-B', true),
    ]
    render(<NetworkOneLine nodes={nodes} edges={[
      { edge_id: 'EDGE-SW-A23-1', endpoint_a_id: 'SW-A23', endpoint_b_id: 'SEC-B3', semantics: 'CONNECTIVITY', active: true },
    ]} selectedEntityId={null} onSelect={vi.fn()} />)
    const options = cytoscapeMock.mock.calls[0]![0] as { elements: Array<{ data: { id: string; label?: string }; classes?: string }> }
    const defect = options.elements.find((element) => element.data.id === 'EDGE-SW-A23-1')
    const note = options.elements.find((element) => element.data.id === 'seeded-defect-note')
    expect(defect?.classes).toBe('energised-edge')
    expect(defect?.data.label).toBeUndefined()
    expect(note?.classes).toBe('seeded-defect-note')
    expect(note?.data.label).toBe('(seeded incorrect configuration)')
    expect(screen.getAllByLabelText('Network diagram legend').at(-1)).toHaveTextContent('Currently energised path')
    expect(screen.getAllByLabelText('Network diagram legend').at(-1)).toHaveTextContent('Open switch or breaker')
  })

  it('omits the seeded-defect note from the corrected endpoint', () => {
    const projection = makeProjection()
    render(<NetworkOneLine nodes={projection.network_nodes} edges={[
      { edge_id: 'EDGE-SW-A23-1', endpoint_a_id: 'SW-A23', endpoint_b_id: 'SEC-A2', semantics: 'CONNECTIVITY', active: true },
    ]} selectedEntityId={null} onSelect={vi.fn()} />)
    const options = cytoscapeMock.mock.calls[0]![0] as { elements: Array<{ data: { id: string } }> }
    expect(options.elements.some((element) => element.data.id === 'seeded-defect-note')).toBe(false)
  })
})
