import { expect, test } from '@playwright/test'

test('stale telemetry visibly withholds unsafe isolation actions', async ({ page }) => {
  await page.goto('/')
  await page.getByRole('button', { name: 'Start stale-evidence walkthrough' }).click()

  await expect(page.getByTestId('formal-state')).toHaveText('N1')
  await expect(page.getByTestId('affected-customers')).toHaveText('850')
  await expect(page.getByRole('heading', { name: 'Active-fault incident boundaries' })).toBeVisible()
  await expect(page.getByText('UNPROVEN').first()).toBeVisible()
  await expect(page.getByRole('button', { name: 'Open isolation device SW-A12' })).toBeDisabled()
  await expect(page.getByRole('button', { name: 'Open isolation device SW-A23' })).toBeDisabled()
  await expect(page.getByText(/Boundary SW-A12 is UNPROVEN; trustworthy fresh evidence is required/i)).toHaveCount(2)

  await page.getByRole('navigation', { name: 'Workspace views' }).getByRole('button', { name: 'Telemetry' }).click()
  await expect(page.getByRole('row', { name: /SW-A12.*GOOD.*71\.000 s.*STALE.*INSUFFICIENT/i })).toBeVisible()
  await expect(page.getByRole('row', { name: /SW-A23.*GOOD.*71\.000 s.*STALE.*INSUFFICIENT/i })).toBeVisible()
  await expect(page.getByText(/A GOOD value can still be STALE/i)).toBeVisible()
})
