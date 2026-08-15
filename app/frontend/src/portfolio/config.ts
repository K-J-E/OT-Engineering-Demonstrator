export interface PortfolioConfig {
  portfolioUrl: string
  demoUrl: string
  githubUrl: string | null
  releaseUrl: string | null
  evidenceUrl: string | null
}

function optional(value: string | undefined): string | null {
  const trimmed = value?.trim()
  return trimmed === undefined || trimmed.length === 0 ? null : trimmed
}

export const portfolioConfig: PortfolioConfig = {
  portfolioUrl: optional(import.meta.env.VITE_PORTFOLIO_URL) ?? '/',
  demoUrl: optional(import.meta.env.VITE_PORTFOLIO_DEMO_URL) ?? '/demo',
  githubUrl: optional(import.meta.env.VITE_PORTFOLIO_GITHUB_URL),
  releaseUrl: optional(import.meta.env.VITE_PORTFOLIO_RELEASE_URL),
  evidenceUrl: optional(import.meta.env.VITE_PORTFOLIO_EVIDENCE_URL),
}
