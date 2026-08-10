import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { App } from './App'

describe('I1 frontend scaffold', () => {
  it('states the non-operational scaffold boundary', () => {
    render(<App />)

    expect(screen.getByRole('heading', { name: 'OT Graduate Demonstrator' })).toBeVisible()
    expect(screen.getByText('I1 — Contracts and Inputs scaffold')).toBeVisible()
    expect(screen.getByText(/no real equipment control/i)).toBeVisible()
  })
})
