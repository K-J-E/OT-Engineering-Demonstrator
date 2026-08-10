import { expect, test, type Page } from '@playwright/test'

async function selectView(page: Page, name: string) {
  await page.getByRole('navigation', { name: 'Workspace views' }).getByRole('button', { name }).click()
}

async function executeConfirmed(page: Page, accessibleName: RegExp) {
  page.once('dialog', (dialog) => dialog.accept())
  await page.getByRole('button', { name: accessibleName }).click()
}

test('SEC-B2 exploration reverses feeder roles and exports separately classified evidence', async ({ page }) => {
  await page.goto('/')
  await page.getByRole('combobox', { name: 'Exploration fault section' }).selectOption('SEC-B2')
  await page.getByRole('button', { name: 'Start exploratory v1.1 run' }).click()
  await expect(page.getByTestId('full-run-id')).toBeVisible()
  const ribbon = page.getByLabel('Persistent run context')
  await expect(ribbon.getByText('EXPLORATION', { exact: true })).toBeVisible()
  await expect(ribbon.getByText('EXPLORATORY', { exact: true })).toBeVisible()
  await expect(ribbon.getByText('SEC-B2', { exact: true })).toBeVisible()
  const sourceRunId = await page.getByTestId('full-run-id').textContent()

  await selectView(page, 'Validation')
  await expect(page.getByRole('heading', { name: 'Exploration evidence controls' })).toBeVisible()
  const formalProgress = page
    .getByRole('region', { name: 'Formal progress remains separate' })
    .getByText(/21 FORMAL definitions;/i)
  const formalProgressBeforeExploration = await formalProgress.textContent()
  expect(formalProgressBeforeExploration).not.toBeNull()
  await page.getByRole('button', { name: 'Start exploratory execution VT-EXP-ROLE-001' }).click()
  await selectView(page, 'Operational')

  await page.getByRole('button', { name: 'Initiate controlled fault' }).click()
  await page.getByRole('button', { name: /^Acknowledge feeder-trip alarm / }).click()
  await executeConfirmed(page, /^Open isolation device SW-B12$/)
  await executeConfirmed(page, /^Open isolation device SW-B23$/)
  await executeConfirmed(page, /^Restore normal source BRK-B$/)
  await page.getByRole('button', { name: 'Assess alternate restoration' }).click()

  await selectView(page, 'Restoration')
  await expect(page.getByRole('heading', { name: 'PERMITTED' })).toBeVisible()
  await expect(page.getByText('FDR-B', { exact: true })).toBeVisible()
  await expect(page.getByText(/FDR-A \/ ZS-01/)).toBeVisible()
  await expect(page.getByLabel('Candidate and path').getByText('1.900 MW')).toBeVisible()
  const capacityCalculation = page.getByLabel('Configured capacity and derived supplied load')
  await expect(capacityCalculation.getByText('5.100 MW')).toBeVisible()
  await expect(capacityCalculation.getByText('5.500 MW')).toBeVisible()
  await expect(capacityCalculation.getByText('92.7%')).toBeVisible()

  await selectView(page, 'Validation')
  await page.getByRole('button', { name: 'Capture exploratory checkpoint VT-EXP-ROLE-001' }).click()
  await expect(page.getByText(/1 immutable checkpoint/)).toBeVisible()
  await expect(page.getByText(/NOT DETERMINED/)).toBeVisible()
  await expect(formalProgress).toHaveText(formalProgressBeforeExploration!)
  await selectView(page, 'Operational')
  await executeConfirmed(page, /^Reset into a new run$/)
  await expect(page.getByTestId('full-run-id')).not.toHaveText(sourceRunId!)

  await selectView(page, 'Evidence')
  const sourceRecord = page.getByRole('heading', { name: 'VT-EXP-ROLE-001' }).locator('..')
  await expect(sourceRecord.getByText('EXPLORATORY')).toBeVisible()
  await expect(sourceRecord.getByText('Available')).toBeVisible()
  await sourceRecord.getByRole('button', { name: 'Generate new evidence ZIP' }).click()
  await expect(page.getByText('VERIFIED')).toBeVisible()
  await expect(page.getByRole('link', { name: 'Download verified ZIP' })).toBeVisible()
  await expect(page.getByText(/evidence\/exports\/PKG-[0-9a-f]{12}-EXPLORATORY\.zip/)).toBeVisible()
})
