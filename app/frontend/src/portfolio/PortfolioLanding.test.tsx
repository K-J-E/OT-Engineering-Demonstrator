import { cleanup, render, screen, within } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'
import { PortfolioLanding } from './PortfolioLanding'
import type { PortfolioConfig } from './config'

const emptyConfig: PortfolioConfig = {
  portfolioUrl: '/', demoUrl: '/demo', githubUrl: null, releaseUrl: null, evidenceUrl: null,
}

afterEach(cleanup)

describe('external reviewer portfolio landing', () => {
  it('positions the work as a simulated systems study before presenting the demonstrator', () => {
    const { container } = render(<PortfolioLanding config={emptyConfig} />)
    expect(screen.getByRole('heading', { name: /A simplified, simulated OT systems project/i })).toBeVisible()
    expect(screen.getByText('Engineering Demonstrator — Distribution Operations, Assurance and Defect Investigation')).toBeVisible()
    expect(container.querySelector('.portfolio-hero-copy > .portfolio-kicker')).not.toBeInTheDocument()
    expect(screen.getByText(/not a software product showcase/i)).toBeVisible()
    expect(screen.getByText(/No real utility data or control/i)).toBeVisible()
    expect(screen.getByText(/Develop an end-to-end understanding of how network information becomes operational decisions/i)).toBeVisible()
    expect(screen.getByText(/power-systems and information-systems boundary/i)).toBeVisible()
    expect(screen.getByRole('heading', { name: 'What to evaluate' })).toBeVisible()
    expect(screen.getByRole('heading', { name: 'A safe-looking run is not necessarily a correct result.' })).toBeVisible()
    expect(screen.getByText(/run-time assurance passes, independent validation fails/i)).toBeVisible()
    expect(screen.getByRole('heading', { name: 'Six decisions that carry the technical value' })).toBeVisible()
    expect(screen.getByRole('heading', { name: 'Working where power-network meaning becomes system behaviour' })).toBeVisible()
    expect(screen.getByText(/contribute to early-career tasks/i)).toBeVisible()
    expect(screen.getByRole('heading', { name: 'What V1 revealed—and where V2 could go next' })).toBeVisible()
    expect(screen.getByRole('heading', { name: 'Difficulties resolved before the final validation campaign' })).toBeVisible()
    expect(screen.getByRole('heading', { name: 'AI support accelerated the workflow' })).toBeVisible()
    expect(screen.getByText(/The written test plan was not yet an executable verdict method/i)).toBeVisible()
    expect(screen.getByText(/supporting records include investigation and research, design brief, network model/i)).toBeVisible()
  })

  it('keeps the first-viewport actions focused on the written approach and isolated demo route', () => {
    const { container } = render(<PortfolioLanding config={emptyConfig} />)
    const actions = within(container.querySelector('.portfolio-hero-actions')!).getAllByRole('link')
    expect(actions.map((item) => item.textContent?.trim())).toEqual([
      'Explore the project approach', 'Open the live demonstrator →',
    ])
    expect(actions[1]).toHaveAttribute('href', '/demo')
    expect(screen.queryByRole('link', { name: 'What to evaluate' })).not.toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'V2 automation opportunities' })).toHaveAttribute('href', '#automation')
    expect(screen.getByText(/Maintain requirement-to-test traceability/i)).toBeVisible()
    expect(screen.getByText(/generate review or client summaries only from accepted evidence/i)).toBeVisible()
    expect(screen.getByRole('link', { name: 'Project resources' })).toHaveAttribute('href', '#resources')
    expect(screen.queryByText(/Application materials/i)).not.toBeInTheDocument()
  })

  it('renders deliberate pending states instead of broken document links', () => {
    const { container } = render(<PortfolioLanding config={emptyConfig} />)
    expect(container.querySelectorAll('.portfolio-resource-link.pending')).toHaveLength(2)
  })
})
