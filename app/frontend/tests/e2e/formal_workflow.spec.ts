import { expect, test, type Page } from '@playwright/test'

async function selectView(page: Page, name: string) {
  await page.getByRole('navigation', { name: 'Workspace views' }).getByRole('button', { name }).click()
}

async function executeConfirmed(page: Page, accessibleName: RegExp) {
  page.once('dialog', (dialog) => dialog.accept())
  await page.getByRole('button', { name: accessibleName }).click()
}

async function capture(page: Page, checkpoint: string) {
  await selectView(page, 'Validation')
  await page.getByRole('button', { name: `Capture current checkpoint ${checkpoint}` }).click()
  await expect(page.getByRole('heading', { name: 'Evidence checkpoints' })).toBeVisible()
  await selectView(page, 'Operational')
}

test('formal v1.1 N0-N5 is presented from backend-owned engineering state', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByRole('heading', { name: 'OT engineering review workspace' })).toBeVisible()
  await page.getByRole('button', { name: 'Start formal v1.1 run' }).click()

  await expect(page.getByTestId('formal-state')).toHaveText('N0')
  await expect(page.getByTestId('affected-customers')).toHaveText('0')
  await expect(page.getByText('LOCAL · SIMULATED · NO REAL CONTROL')).toBeVisible()

  await selectView(page, 'Validation')
  await page.getByRole('button', { name: 'Start formal execution' }).click()
  await page.getByRole('button', { name: 'Capture current checkpoint N0' }).click()
  await selectView(page, 'Operational')

  await page.getByRole('button', { name: 'Initiate controlled fault' }).click()
  await expect(page.getByTestId('formal-state')).toHaveText('N1')
  await expect(page.getByTestId('affected-customers')).toHaveText('850')
  await capture(page, 'N1')

  await page.getByRole('button', { name: /^Acknowledge feeder-trip alarm / }).click()
  await executeConfirmed(page, /^Open isolation device SW-A12$/)
  await executeConfirmed(page, /^Open isolation device SW-A23$/)
  await expect(page.getByTestId('formal-state')).toHaveText('N2')
  await capture(page, 'N2')

  await executeConfirmed(page, /^Restore normal source BRK-A$/)
  await expect(page.getByTestId('formal-state')).toHaveText('N3')
  await expect(page.getByTestId('affected-customers')).toHaveText('670')
  await capture(page, 'N3')

  await page.reload()
  await expect(page.getByTestId('formal-state')).toHaveText('N3')
  await expect(page.getByTestId('affected-customers')).toHaveText('670')

  await page.getByRole('button', { name: /^Assess alternate restoration$/ }).click()
  await expect(page.getByTestId('formal-state')).toHaveText('N4')
  await capture(page, 'N4')

  await selectView(page, 'Restoration')
  await expect(page.getByRole('heading', { name: 'PERMITTED' })).toBeVisible()
  await expect(page.getByText('1.500 MW').last()).toBeVisible()
  await expect(page.getByText('5.700 MW')).toBeVisible()
  await expect(page.getByText('6.000 MW')).toBeVisible()
  await expect(page.getByText('95.0%')).toBeVisible()
  await expect(page.getByText('450')).toBeVisible()
  await executeConfirmed(page, /^Execute permitted restoration$/)

  await expect(page.getByTestId('formal-state')).toHaveText('N5')
  await selectView(page, 'Operational')
  await expect(page.getByTestId('affected-customers')).toHaveText('220')
  await expect(page.getByTestId('restored-customers')).toHaveText('450')
  await expect(page.getByRole('row', { name: /FDR-B Riverbend Feeder 4.200 MW 6.000 MW 5.700 MW/ })).toBeVisible()
  await capture(page, 'N5')

  await selectView(page, 'Validation')
  await expect(page.getByRole('heading', { name: 'Evidence checkpoints' })).toBeVisible()
  await expect(page.getByText('NOT DETERMINED')).toBeVisible()
  await expect(page.getByText(/No PASS\/FAIL has been created/)).toBeVisible()
  await expect(page.getByRole('button', { name: 'Finalise execution' })).toBeDisabled()

  await selectView(page, 'Events')
  await expect(page.getByRole('heading', { name: 'ALARM ACKNOWLEDGED' })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'RESTORATION ASSESSED' })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'SWITCHING ACTION' })).toHaveCount(4)
})
