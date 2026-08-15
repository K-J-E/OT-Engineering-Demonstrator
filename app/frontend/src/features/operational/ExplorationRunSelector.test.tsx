import { fireEvent, render, screen } from '@testing-library/react'
import { expect, it, vi } from 'vitest'
import { ExplorationRunSelector } from './ExplorationRunSelector'

it('repeats the current trial or starts a clean trial for another section', () => {
  const onStart = vi.fn()
  render(<ExplorationRunSelector sectionIds={['SEC-A1', 'SEC-B3']} currentSectionId="SEC-B3" busy={false} onStart={onStart} idPrefix="test" />)

  fireEvent.click(screen.getByRole('button', { name: 'Reset and rerun SEC-B3' }))
  expect(onStart).toHaveBeenLastCalledWith('SEC-B3')

  fireEvent.change(screen.getByRole('combobox', { name: 'Fault section for next trial' }), { target: { value: 'SEC-A1' } })
  fireEvent.click(screen.getByRole('button', { name: 'Start clean trial at SEC-A1' }))
  expect(onStart).toHaveBeenLastCalledWith('SEC-A1')
})
