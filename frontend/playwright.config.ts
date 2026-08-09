import { defineConfig, devices } from '@playwright/test';

/**
 * Playwright configuration for LunaYield Phase 1D E2E tests.
 *
 * Runs Chromium only against the real dev servers.
 * Backend MUST be started separately on http://127.0.0.1:8000
 * Frontend is launched via webServer on http://127.0.0.1:5173
 */
export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: 1,
  reporter: 'html',
  use: {
    baseURL: 'http://127.0.0.1:5173',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },

  // Only Chromium for Phase 1D
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],

  // Launch frontend dev server automatically
  webServer: {
    command: 'npm run dev -- --host 127.0.0.1',
    url: 'http://127.0.0.1:5173',
    reuseExistingServer: !process.env.CI,
    timeout: 60_000,
    env: {
      // Ensure frontend proxy to backend works
      VITE_API_URL: 'http://127.0.0.1:8000',
    },
  },

  // Global setup/teardown not needed - backend started manually
  globalSetup: undefined,
  globalTeardown: undefined,
});