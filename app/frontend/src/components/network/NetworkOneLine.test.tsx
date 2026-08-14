import { render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { makeProjection } from '../../test-fixtures'

const { cytoscapeMock, graphMock } = vi.hoisted(() => {
  const graph = { on: vi.fn(), destroy: vi.fn(), getElementById: vi.fn(() => ({ select: vi.fn() })) }
  return { graphMock: graph, cytoscapeMock: vi.fn((_options: unknown) => graph) }
})
vi.mock('cytoscape', () => ({ default: cytoscapeMock }))

import { NetworkOneLine } from './NetworkOneLine'

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
    expect(screen.getByText(/does not capture page scrolling or change connectivity/i)).toBeVisible()
  })
})
