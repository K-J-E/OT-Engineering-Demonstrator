import { defineConfig } from '@playwright/test'

const apiPort = process.env.E2E_API_PORT ?? '8000'
const webPort = process.env.E2E_WEB_PORT ?? '4173'

export default defineConfig({
  testDir: './tests/e2e',
  fullyParallel: false,
  workers: 1,
  timeout: 120_000,
  reporter: 'line',
  use: {
    baseURL: `http://127.0.0.1:${webPort}`,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  webServer: [
    {
      command: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=app/backend .venv/bin/uvicorn tests.e2e.runtime_app:app --host 127.0.0.1 --port ${apiPort}`,
      cwd: '../..',
      url: `http://127.0.0.1:${apiPort}/api/v1/workspace/bootstrap`,
      reuseExistingServer: false,
      timeout: 120_000,
    },
    {
      command: `VITE_API_TARGET=http://127.0.0.1:${apiPort} "${process.execPath}" node_modules/vite/bin/vite.js --host 127.0.0.1 --port ${webPort}`,
      cwd: '.',
      url: `http://127.0.0.1:${webPort}`,
      reuseExistingServer: false,
      timeout: 120_000,
    },
  ],
})
