import { expect, test } from '@playwright/test'

test('v1.0 consequence is investigated before same-build v1.1 repeat and regression', async ({ page }) => {
  await page.goto('/')
  await page.getByRole('button', { name: 'Run v1.0 test and investigate' }).click()
  await expect(page.getByRole('heading', { name: 'DEF-001 controlled investigation' })).toBeVisible()
  await expect(page.getByText('400 affected')).toBeVisible()
  await expect(page.getByText('FAIL').first()).toBeVisible()
  await expect(page.getByText('SEC-B3', { exact: true })).not.toBeVisible()

  for (let index = 0; index < 6; index += 1) {
    await page.getByRole('button', { name: 'Review next evidence step' }).click()
  }
  await expect(page.getByText(/SEC-A3 → SW-A23 → SEC-B3/).first()).toBeVisible()
  await expect(page.getByText('connectivity_edges.EDGE-SW-A23-1.endpoint_a_id', { exact: true }).first()).toBeVisible()
  await page.getByRole('button', { name: 'Record DEF-001 after evidence review' }).click()
  await expect(page.getByText('DEF-001', { exact: true }).last()).toBeVisible()
  await page.getByRole('button', { name: 'Record controlled v1.1 selection' }).click()
  await expect(page.getByText('COR-001', { exact: true })).toBeVisible()
  await page.getByRole('button', { name: 'Run same-build v1.1 direct repeat' }).click()
  await expect(page.getByText('Direct repeat PASS')).toBeVisible()
  await expect(page.getByText(/v1.1 · 850 affected/)).toBeVisible()
  await page.getByRole('button', { name: 'Run corrected full N0–N5 regression' }).click()
  await expect(page.getByText('Corrected N0–N5 evidence preserved')).toBeVisible()
  await expect(page.getByText(/6 immutable checkpoints/)).toBeVisible()
  await expect(page.getByTestId('same-build-proof')).toBeVisible()
  await expect(page.getByTestId('formal-state')).toHaveText('N5')
  await page.getByRole('navigation', { name: 'Workspace views' }).getByRole('button', { name: 'Operational' }).click()
  await expect(page.getByTestId('affected-customers')).toHaveText('220')
})
