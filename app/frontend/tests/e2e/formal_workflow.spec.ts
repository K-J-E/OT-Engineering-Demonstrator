import { expect, test, type Page } from '@playwright/test'

async function selectView(page: Page, name: string) {
  await page.getByRole('navigation', { name: 'Workspace views' }).getByRole('button', { name }).click()
}

async function executeConfirmed(page: Page, accessibleName: RegExp) {
  await page.getByRole('button', { name: accessibleName }).click()
}

test('formal walkthrough stays operational and performs restoration on its review page', async ({ page }) => {
  await page.goto('/')
  await page.getByRole('button', { name: 'Start formal validation walkthrough' }).click()

  const fullRunIdentity = await page.getByTestId('full-run-id').textContent()
  expect(fullRunIdentity).toMatch(/^[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}$/)
  await expect(page.getByTestId('formal-state')).toContainText('N0 · Normal network')
  await expect(page.getByRole('heading', { name: 'Feeder single-line diagram' })).toBeVisible()
  await expect(page.getByRole('navigation', { name: 'Workspace views' }).getByRole('button', { name: 'Operational' })).toHaveAttribute('aria-current', 'page')

  const faultAction = page.getByRole('button', { name: 'Start simulated fault at SEC-A2' })
  await expect(faultAction).toBeEnabled()
  await faultAction.click()
  await expect(page.getByTestId('formal-state')).toContainText('N1 · Fault active')
  await expect(page.getByTestId('affected-customers')).toHaveText('850')

  await page.getByRole('button', { name: 'Review and acknowledge the feeder-trip alarm' }).click()
  await expect(page.getByRole('heading', { name: 'Review before acknowledging' })).toBeVisible()
  await page.getByRole('button', { name: 'Acknowledge this feeder-trip alarm' }).click()
  const continueToIsolation = page.getByRole('button', { name: 'Continue to fault isolation' })
  await expect(continueToIsolation).toHaveClass(/primary-action/)
  await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight))
  await continueToIsolation.click()
  await expect.poll(() => page.getByRole('navigation', { name: 'Workspace views' }).evaluate((element) => Math.abs(Math.round(element.getBoundingClientRect().top)))).toBe(0)

  await executeConfirmed(page, /^Open SW-A12 to isolate SEC-A2$/)
  await executeConfirmed(page, /^Open SW-A23 to isolate SEC-A2$/)
  await expect(page.getByTestId('formal-state')).toContainText('N2 · Fault isolated')

  await executeConfirmed(page, /^Reclose BRK-A to restore the healthy upstream section$/)
  await expect(page.getByTestId('formal-state')).toContainText('N3 · Healthy upstream section restored')
  await expect(page.getByTestId('affected-customers')).toHaveText('670')

  await page.getByRole('button', { name: 'Check alternate supply for healthy de-energised sections' }).click()
  await page.getByRole('button', { name: 'Run alternate-supply check' }).click()
  await expect(page.getByRole('heading', { name: 'PERMITTED', exact: true })).toBeVisible()
  await expect(page.getByText('5.700 MW')).toBeVisible()
  await expect(page.getByText('95.0%')).toBeVisible()

  await expect(page.getByText(/Assessment evidence saved/)).toBeVisible()
  await expect(page.getByRole('button', { name: 'Apply alternate supply restoration' })).toBeVisible()
  await executeConfirmed(page, /^Apply alternate supply restoration$/)

  await expect(page.getByTestId('formal-state')).toContainText('N5 · Eligible healthy sections restored')
  await expect(page.getByTestId('full-run-id')).toHaveText(fullRunIdentity!)
  await expect(page.getByRole('heading', { name: 'Restoration completed' })).toBeVisible()

  await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight))
  await page.getByRole('button', { name: 'Review assurance and validation results' }).click()
  await expect.poll(() => page.getByRole('navigation', { name: 'Workspace views' }).evaluate((element) => Math.abs(Math.round(element.getBoundingClientRect().top)))).toBe(0)
  await expect(page.getByRole('heading', { name: 'How each operating stage was checked' })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Operating assurance and system validation are different' })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'What this walkthrough demonstrates' })).toBeVisible()
  await expect(page.getByText('Evidence complete')).toBeVisible()
  await expect(page.getByText('All defined checks passed')).toBeVisible()
  const savedFormalResult = page.getByRole('article', { name: 'Saved evidence: VT-FML-N0-N5-001' })
  await expect(savedFormalResult.getByText('850 customers affected')).toBeVisible()
  await expect(savedFormalResult.getByText('670 remained affected')).toBeVisible()
  await expect(savedFormalResult.getByText('220 customers remained affected')).toBeVisible()
  const technicalTraceability = savedFormalResult.locator('details.technical-details')
  await technicalTraceability.locator('summary').click()
  expect(await technicalTraceability.evaluate((element) => element.scrollWidth <= element.clientWidth)).toBe(true)
  expect(await technicalTraceability.locator('.technical-evidence-grid').evaluate((element) => element.scrollWidth <= element.clientWidth)).toBe(true)
  const createPackage = page.getByRole('button', { name: 'Create downloadable evidence package' })
  await expect(createPackage).toBeEnabled()
  await createPackage.click()
  await expect(page.getByRole('heading', { name: 'Latest-run evidence package' })).toBeVisible()
  await expect(page.getByText('1 total')).toBeVisible()
  await expect(page.getByText('Downloadable package recorded')).toBeVisible()
  await expect(page.getByRole('link', { name: 'Download evidence package (.zip)' })).toBeVisible()
  await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight))
  await page.getByRole('button', { name: 'Return to final network state' }).last().click()
  await expect.poll(() => page.getByRole('navigation', { name: 'Workspace views' }).evaluate((element) => Math.abs(Math.round(element.getBoundingClientRect().top)))).toBe(0)
  await expect(page.getByRole('heading', { name: 'Feeder single-line diagram' })).toBeVisible()

  await selectView(page, 'Operational')
  await expect(page.getByTestId('affected-customers')).toHaveText('220')
  await expect(page.getByTestId('restored-customers')).toHaveText('450')

  await selectView(page, 'Results & evidence')
  await expect(page.getByRole('heading', { name: 'Validation of the operating logic', exact: true })).toBeVisible()
  await expect(page.getByText('6 of 6 states saved')).toBeVisible()
  await expect(page.getByText(/approved comparison process is complete/i)).toBeVisible()
  await expect(page.getByText('PASS').first()).toBeVisible()
  await expect(page.getByRole('group').filter({ has: page.getByText('Technical test traceability', { exact: true }) })).toBeVisible()
  const resultHeadings = await page.locator('main h2').allTextContents()
  const orderedResultHeadings = [
    'What this walkthrough demonstrates',
    'Operating assurance and system validation are different',
    'How each operating stage was checked',
    'Validation of the operating logic',
    'How the formal result is produced',
    'Saved evidence for this walkthrough',
    'Challenge the operating logic with DEF-001',
    'Evidence packages',
  ]
  expect(orderedResultHeadings.map((heading) => resultHeadings.indexOf(heading))).toEqual([1, 2, 3, 4, 5, 6, 7, 8])
  await expect(page.getByRole('button', { name: 'Continue to DEF-001 investigation' })).toBeEnabled()

  await selectView(page, 'Events')
  await expect(page.getByRole('heading', { name: 'What has happened so far' })).toBeVisible()
  await expect(page.getByText('Eligible healthy sections restored').last()).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Feeder-trip alarm acknowledged' })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Alternate supply assessed' })).toBeVisible()
  await expect(page.getByText(/supporting system records/)).toBeVisible()

  await selectView(page, 'Operational')
  await page.getByRole('button', { name: 'Start a new clean scenario' }).click()
  await expect(page.getByTestId('full-run-id')).not.toHaveText(fullRunIdentity!)
  await expect(page.getByTestId('formal-state')).toContainText('N0 · Normal network')
  await expect(page.getByRole('alert')).toHaveCount(0)
  await page.getByRole('button', { name: 'Start simulated fault at SEC-A2' }).click()
  await page.getByRole('button', { name: 'Review and acknowledge the feeder-trip alarm' }).click()
  await page.getByRole('button', { name: 'Acknowledge this feeder-trip alarm' }).click()
  await page.getByRole('button', { name: 'Continue to fault isolation' }).click()
  await executeConfirmed(page, /^Open SW-A12 to isolate SEC-A2$/)
  await executeConfirmed(page, /^Open SW-A23 to isolate SEC-A2$/)
  await executeConfirmed(page, /^Reclose BRK-A to restore the healthy upstream section$/)
  await page.getByRole('button', { name: 'Check alternate supply for healthy de-energised sections' }).click()
  await page.getByRole('button', { name: 'Run alternate-supply check' }).click()

  await expect(page.getByText(/Assessment evidence saved/)).toBeVisible()
  await expect(page.getByRole('button', { name: 'Apply alternate supply restoration' })).toBeEnabled()
})
