import { expect, test } from '@playwright/test'

test('combined validation entry presents the defect-first story', async ({ page }) => {
  await page.goto('/demo')

  await expect(page.getByRole('heading', { name: 'Expose a seeded configuration defect—and prove its correction' })).toBeVisible()
  await expect(page.getByText(/directly against preserved GIS configuration v1.0/i)).toBeVisible()
  await expect(page.getByRole('button', { name: 'Start defect walkthrough' })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Start formal validation walkthrough' })).toHaveCount(0)
  await expect(page.getByText('VT-TOP-DEF-001 → VT-FML-N0-N5-001')).toBeVisible()
})
