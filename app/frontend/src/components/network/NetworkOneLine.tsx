import cytoscape, { type Core, type ElementDefinition } from 'cytoscape'
import { useEffect, useMemo, useRef } from 'react'
import type { WorkspaceEdge, WorkspaceNode } from '../../api/contracts'
import { formatKw, humanise } from '../format'

interface NetworkOneLineProps {
  nodes: WorkspaceNode[]
  edges: WorkspaceEdge[]
  selectedEntityId: string | null
  onSelect: (entityId: string) => void
}

function nodeClasses(node: WorkspaceNode): string {
  const classes = [node.configured.entity_type.toLowerCase()]
  if (node.derived.energised === true) classes.push('energised')
  if (node.derived.energised === false) classes.push('de-energised')
  if (node.fault_status === 'FAULTED') classes.push('faulted')
  if (node.observed?.value === 'OPEN') classes.push('open-device')
  if (node.observed?.value === 'CLOSED') classes.push('closed-device')
  return classes.join(' ')
}

function edgeIsEnergised(edge: WorkspaceEdge, nodes: WorkspaceNode[]): boolean {
  if (!edge.active) return false

  const endpoints = nodes.filter((node) => [edge.endpoint_a_id, edge.endpoint_b_id].includes(node.entity_id))
  const connectedSections = endpoints.filter((node) => node.configured.entity_type === 'SECTION')
  if (connectedSections.length > 0) {
    return connectedSections.some((node) => node.derived.energised === true)
  }

  // A source-to-breaker edge has no section endpoint. It is energised only when
  // the closed breaker is supplying at least one calculated-energised section
  // on that feeder.
  const connectedFeederIds = new Set(
    endpoints.map((node) => node.configured.feeder_id).filter((feederId): feederId is string => feederId !== null),
  )
  return nodes.some((node) => (
    node.configured.entity_type === 'SECTION'
    && node.configured.feeder_id !== null
    && connectedFeederIds.has(node.configured.feeder_id)
    && node.derived.energised === true
  ))
}

export function NetworkOneLine({ nodes, edges, selectedEntityId, onSelect }: NetworkOneLineProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const graphRef = useRef<Core | null>(null)
  const elements = useMemo<ElementDefinition[]>(
    () => {
      const seededIncorrectEdge = edges.find((edge) => edge.edge_id === 'EDGE-SW-A23-1' && [edge.endpoint_a_id, edge.endpoint_b_id].includes('SEC-B3'))
      const endpointA = nodes.find((node) => node.entity_id === seededIncorrectEdge?.endpoint_a_id)
      const endpointB = nodes.find((node) => node.entity_id === seededIncorrectEdge?.endpoint_b_id)
      const defectNote = seededIncorrectEdge !== undefined ? [{
        data: { id: 'seeded-defect-note', label: '(seeded incorrect configuration)' },
        position: endpointA !== undefined && endpointB !== undefined
          ? { x: (endpointA.position.x + endpointB.position.x) / 2 + 160, y: (endpointA.position.y + endpointB.position.y) / 2 }
          : { x: 1010, y: 330 },
        classes: 'seeded-defect-note',
        selectable: false,
        grabbable: false,
      }] : []
      return [
        ...nodes.map((node) => ({
        data: { id: node.entity_id, label: node.entity_id },
        position: node.position,
        classes: nodeClasses(node),
        selectable: true,
        grabbable: false,
      })),
      ...edges.map((edge) => {
        const energised = edgeIsEnergised(edge, nodes)
        return {
        data: { id: edge.edge_id, source: edge.endpoint_a_id, target: edge.endpoint_b_id },
        classes: energised ? 'energised-edge' : 'de-energised-edge',
        selectable: false,
        grabbable: false,
      }}),
        ...defectNote,
      ]
    },
    [edges, nodes],
  )

  useEffect(() => {
    if (containerRef.current === null) return
    const graph = cytoscape({
      container: containerRef.current,
      elements,
      layout: { name: 'preset', fit: true, padding: 42 },
      autoungrabify: true,
      boxSelectionEnabled: false,
      userPanningEnabled: false,
      userZoomingEnabled: false,
      style: [
        { selector: 'node', style: { width: 74, height: 48, shape: 'round-rectangle', 'background-color': '#f8fafc', 'border-color': '#64748b', 'border-width': 2, label: 'data(label)', color: '#10243e', 'font-size': 12, 'font-weight': 700, 'text-valign': 'center', 'text-halign': 'center' } },
        { selector: 'node.section', style: { width: 92, height: 56 } },
        { selector: 'node.energised', style: { 'background-color': '#d9f4ee', 'border-color': '#0f766e' } },
        { selector: 'node.de-energised', style: { 'background-color': '#eef2f6', 'border-color': '#94a3b8', 'border-style': 'dashed' } },
        { selector: 'node.faulted', style: { 'border-color': '#be123c', 'border-width': 5 } },
        { selector: 'node.open-device', style: { 'background-color': '#fff7ed', 'border-style': 'dashed' } },
        { selector: 'node:selected', style: { 'overlay-color': '#38bdf8', 'overlay-opacity': 0.16, 'overlay-padding': 8 } },
        { selector: 'edge', style: { width: 4, 'line-color': '#64748b', 'curve-style': 'straight' } },
        { selector: 'edge.de-energised-edge', style: { 'line-color': '#94a3b8', 'line-style': 'solid', width: 3, opacity: 0.9 } },
        { selector: 'edge.energised-edge', style: { 'line-color': '#0f766e', width: 5 } },
        { selector: 'node.seeded-defect-note', style: { width: 220, height: 28, shape: 'round-rectangle', 'background-color': '#fff8ed', 'background-opacity': 0.96, 'border-color': '#d99a45', 'border-width': 1, color: '#884307', 'font-size': 12, 'font-weight': 700, 'text-valign': 'center', 'text-halign': 'center' } },
      ],
    })
    graph.on('select', 'node', (event) => onSelect(event.target.id()))
    graphRef.current = graph
    return () => { graph.destroy(); graphRef.current = null }
  }, [elements, onSelect])

  useEffect(() => {
    if (selectedEntityId !== null) graphRef.current?.getElementById(selectedEntityId).select()
  }, [selectedEntityId])

  return (
    <section className="panel network-panel" aria-labelledby="one-line-title">
      <div className="panel-heading">
        <div><span className="eyebrow">Current network state</span><h2 id="one-line-title">Feeder single-line diagram</h2></div>
        <p>Select an entity to inspect it below.</p>
      </div>
      <div ref={containerRef} className="network-canvas" data-topology-editable="false" data-user-zoom="disabled" aria-hidden="true" />
      <div className="network-state-legend" aria-label="Network diagram legend">
        <span><i className="network-line-swatch energised" aria-hidden="true" />Currently energised path</span>
        <span><i className="network-line-swatch de-energised" aria-hidden="true" />Physical connection not currently energised</span>
        <span><i className="network-node-swatch faulted" aria-hidden="true" />Selected fault section</span>
        <span><i className="network-node-swatch open-device" aria-hidden="true" />Open switch or breaker</span>
      </div>
      <details className="network-table-alternative">
        <summary>Accessible network state table</summary>
        <div className="table-scroll"><table>
          <thead><tr><th>Network item</th><th>Equipment type</th><th>Normal network record</th><th>Latest telemetry</th><th>Calculated state</th><th>Fault state</th></tr></thead>
          <tbody>{nodes.map((node) => (
            <tr key={node.entity_id}>
              <th scope="row">{node.entity_id}</th>
              <td>{humanise(node.configured.entity_type)}</td>
              <td>{node.configured.normal_state ?? (node.configured.configured_load_kw !== null ? formatKw(node.configured.configured_load_kw) : node.configured.normal_source_availability ?? '—')}</td>
              <td>{node.observed?.value ?? 'Not an observed point'}</td>
              <td>{node.derived.energised === null ? node.derived.current_source_availability ?? '—' : `${node.derived.energised ? 'ENERGISED' : 'DE-ENERGISED'} · ${node.derived.source_feeder_ids.join(', ') || 'No active source'}`}</td>
              <td>{humanise(node.fault_status)}</td>
            </tr>
          ))}</tbody>
        </table></div>
      </details>
    </section>
  )
}
