import { useEffect, useState } from 'react'
import { explorationSectionLabel } from '../run-setup/exploration-options'

export function ExplorationRunSelector({
  sectionIds,
  currentSectionId,
  busy,
  onStart,
  idPrefix,
}: {
  sectionIds: string[]
  currentSectionId: string
  busy: boolean
  onStart: (sectionId: string) => void
  idPrefix: string
}) {
  const [selectedSectionId, setSelectedSectionId] = useState(currentSectionId)
  useEffect(() => setSelectedSectionId(currentSectionId), [currentSectionId])

  const repeatsCurrentSection = selectedSectionId === currentSectionId
  const selectId = `${idPrefix}-fault-section`
  return <div className="exploration-run-selector">
    <label htmlFor={selectId}>Fault section for next trial</label>
    <select id={selectId} value={selectedSectionId} onChange={(event) => setSelectedSectionId(event.target.value)}>
      {sectionIds.map((sectionId) => <option key={sectionId} value={sectionId}>{explorationSectionLabel(sectionId)}</option>)}
    </select>
    <button type="button" className="primary-action" disabled={busy || selectedSectionId.length === 0} onClick={() => onStart(selectedSectionId)}>
      {busy ? 'Starting clean trial…' : repeatsCurrentSection ? `Reset and rerun ${selectedSectionId}` : `Start clean trial at ${selectedSectionId}`}
    </button>
  </div>
}
