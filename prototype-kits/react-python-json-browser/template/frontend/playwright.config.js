import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  timeout: 30_000,
  expect: {
    timeout: 5_000,
  },
  // Generated prototypes use local JSON mock storage by default. Run browser
  // tests serially to avoid concurrent writes racing through the same file.
  workers: 1,
  use: {
    baseURL: 'http://127.0.0.1:5173',
    // Prototype anchors use data-prototype-id. This lets tests use
    // page.getByTestId('screen.foo') without switching to data-testid.
    testIdAttribute: 'data-prototype-id',
    trace: 'retain-on-failure',
  },
  webServer: [
    {
      command: 'cd ../backend && PYTHONPATH=. ../.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000',
      url: 'http://127.0.0.1:8000/health',
      reuseExistingServer: true,
      timeout: 120_000,
    },
    {
      command: 'npm run dev -- --port 5173',
      url: 'http://127.0.0.1:5173',
      reuseExistingServer: true,
      timeout: 120_000,
    },
  ],
});
