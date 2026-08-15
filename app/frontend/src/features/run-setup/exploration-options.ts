const recommendedFirstRunSections = new Set(['SEC-A2', 'SEC-A3', 'SEC-B2', 'SEC-B3'])

export function isRecommendedFirstRunSection(sectionId: string) {
  return recommendedFirstRunSections.has(sectionId)
}

export function explorationSectionLabel(sectionId: string) {
  return isRecommendedFirstRunSection(sectionId)
    ? `${sectionId} (recommended for first run)`
    : sectionId
}

export function defaultExplorationSection(sectionIds: string[]) {
  return sectionIds.find((sectionId) => sectionId === 'SEC-A2')
    ?? sectionIds.find(isRecommendedFirstRunSection)
    ?? sectionIds[0]
    ?? ''
}
