export function shortId(value: string): string {
  return value.slice(0, 8)
}

export function formatKw(value: number | null): string {
  return value === null ? 'Unavailable' : `${(value / 1000).toFixed(3)} MW`
}

export function formatAge(ageMs: number): string {
  return `${(ageMs / 1000).toFixed(3)} s`
}

export function humanise(value: string): string {
  return value.replaceAll('_', ' ')
}

export function formatTime(value: string): string {
  return value.replace('T', ' ').replace('Z', ' Z')
}
