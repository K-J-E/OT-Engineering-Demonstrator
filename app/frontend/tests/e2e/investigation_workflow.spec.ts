import { expect, test, type Page } from '@playwright/test'

async function view(page: Page, name: string) {
  await page.getByRole('navigation', { name: 'Workspace views' }).getByRole('button', { name }).click()
}

test('defect run passes live assurance, fails validation, traces the cause and passes after correction', async ({ page }) => {
  const started = await page.request.post('/api/v1/investigations/start', { data: { actor: 'Graduate Engineer' } })
  expect(started.ok()).toBe(true)
  const investigation = await started.json()
  const failureExecutionId = investigation.original_failure.execution.validation_execution_id as string
  const failureRunId = investigation.original_failure.execution.scenario_run_id as string
  await page.goto('/')
  await page.evaluate(({ failureExecutionId, failureRunId }) => {
    localStorage.setItem('ot-demo-investigation-failure-id', failureExecutionId)
    localStorage.setItem('ot-demo-current-run-id', failureRunId)
    localStorage.setItem('ot-demo-current-experience', 'investigation')
  }, { failureExecutionId, failureRunId })
  await page.reload()

  const navigation = page.getByRole('navigation', { name: 'Workspace views' })
  await expect(navigation.getByRole('button')).toHaveCount(6)
  await expect(navigation.getByRole('button', { name: 'Investigation' })).toHaveClass(/defect-stage/)
  await expect(navigation.getByRole('button', { name: 'Corrected repeat' })).toHaveClass(/defect-stage/)

  await view(page, 'Events')
  await page.getByRole('button', { name: 'Acknowledge this feeder-trip alarm' }).click()
  await page.getByRole('button', { name: 'Continue to fault isolation' }).click()
  await page.getByRole('button', { name: /^Open SW-A12 to isolate SEC-A2$/ }).click()
  await expect(page.getByTestId('formal-state')).toContainText('N2 · Fault isolated')
  await expect(page.getByRole('button', { name: /^Open SW-A23 to isolate SEC-A2$/ })).toHaveCount(0)
  await page.getByRole('button', { name: /^Reclose BRK-A to restore the healthy upstream section$/ }).click()
  await page.getByRole('button', { name: 'Check alternate supply for healthy de-energised sections' }).click()
  await page.getByRole('button', { name: 'Run alternate-supply check' }).click()
  await expect(page.getByRole('heading', { name: 'NO CANDIDATE', exact: true })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'No alternate restoration action is available' })).toBeVisible()
  await page.getByRole('button', { name: 'Review assurance and validation results' }).click()

  await expect(page.getByRole('heading', { name: 'The operation looks credible—but the validated outcome is wrong' })).toBeVisible()
  await expect(page.getByText('Operational assurance').first()).toBeVisible()
  await expect(page.getByText('System validation').first()).toBeVisible()
  await expect(page.getByText('PASS', { exact: true }).first()).toBeVisible()
  await expect(page.getByText('FAIL', { exact: true }).first()).toBeVisible()
  await expect(page.getByText('850 customers affected')).toBeVisible()
  await expect(page.getByText('400 customers affected')).toBeVisible()
  await page.getByRole('button', { name: 'Investigate the validation failure' }).click()

  await expect(page.getByRole('heading', { name: 'Why did a safe-looking run produce the wrong result?' })).toBeVisible()
  for (let index = 0; index < 3; index += 1) await page.getByRole('button', { name: 'Continue investigation' }).click()
  await expect(page.getByRole('heading', { name: 'The fault is in one GIS connectivity endpoint' })).toBeVisible()
  await expect(page.getByText('SW-A23 connected to SEC-B3')).toBeVisible()
  await expect(page.getByText(/Everything can look internally consistent and still be wrong/)).toBeVisible()

  await page.getByRole('button', { name: 'Confirm and record the identified fault' }).click()
  await expect(page.getByText('Recorded as DEF-001')).toBeVisible()
  await page.getByRole('button', { name: 'Select corrected GIS configuration v1.1' }).click()
  await expect(page.getByText('Correction COR-001 recorded')).toBeVisible()
  await page.getByRole('button', { name: 'Run focused corrected check' }).click()
  await expect(page.getByText('PASS · 850 affected customers')).toBeVisible()
  await expect(page.getByTestId('same-build-proof')).toContainText('only the network configuration changed')
  await page.getByRole('button', { name: 'Continue to corrected full run' }).click()
  await page.getByRole('button', { name: 'Run corrected isolation-to-restoration scenario' }).click()

  await expect(page.getByRole('heading', { name: 'Prove the correction through the complete operating sequence' })).toBeVisible()
  await expect(page.getByText('PASS', { exact: true }).first()).toBeVisible()
  await expect(page.getByText('220 remained affected')).toBeVisible()
  await expect(page.getByText('RADIAL', { exact: true })).toBeVisible()
  await expect(page.getByTestId('formal-state')).toContainText('N5 · Eligible healthy sections restored')
})
