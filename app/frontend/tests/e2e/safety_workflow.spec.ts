import { expect, test } from '@playwright/test'

test('stale telemetry visibly withholds unsafe isolation actions', async ({ page }) => {
  await page.goto('/')
  await page.getByRole('button', { name: 'Start stale-evidence walkthrough' }).click()

  await expect(page.getByTestId('formal-state')).toContainText('N1 · Fault active')
  await expect(page.getByTestId('affected-customers')).toHaveText('850')
  await expect(page.getByRole('heading', { name: 'Can the faulted section be safely separated from supply?' })).toBeVisible()
  await expect(page.getByText('ISOLATION NOT YET CONFIRMED')).toBeVisible()
  await expect(page.getByRole('button', { name: 'Open SW-A12 to isolate SEC-A2' })).toBeDisabled()
  await expect(page.getByRole('button', { name: 'Open SW-A23 to isolate SEC-A2' })).toBeDisabled()
  await expect(page.getByText('Open position not confirmed')).toHaveCount(2)
  await expect(page.getByText(/too old or invalid for this decision/)).toHaveCount(2)

  const guidedNavigation = page.getByRole('navigation', { name: 'Workspace views' })
  await expect(guidedNavigation.getByRole('button')).toHaveCount(3)
  await expect(guidedNavigation.getByRole('button', { name: 'Restoration' })).toHaveCount(0)

  await page.getByRole('navigation', { name: 'Workspace views' }).getByRole('button', { name: 'Telemetry evidence' }).click()
  await expect(page.getByRole('row', { name: /SW-A12.*GOOD.*71\.000 s.*STALE.*INSUFFICIENT/i })).toBeVisible()
  await expect(page.getByRole('row', { name: /SW-A23.*GOOD.*71\.000 s.*STALE.*INSUFFICIENT/i })).toBeVisible()
  await expect(page.getByText(/A GOOD reading can therefore still be unusable when it is STALE/i)).toBeVisible()
  await page.getByRole('button', { name: 'Review safety result' }).click()
  await expect(page.getByRole('heading', { name: 'The application withheld unsafe switching authority' })).toBeVisible()
  await expect(page.getByText('WITHHELD', { exact: true })).toBeVisible()
  await expect(page.getByText('PASS', { exact: true })).toBeVisible()
  await expect(page.getByText(/Blocked.*operating outcome.*PASS.*validation verdict/i)).toBeVisible()
})
