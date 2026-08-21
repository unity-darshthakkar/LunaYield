/**
 * Error/safety flow E2E tests for LunaYield Phase 1D.
 *
 * Validates realistic operator-visible error handling and safety UX.
 * Does NOT test backend safety logic (covered by backend unit tests).
 * Uses controlled HTTP interception for one frontend error-rendering test.
 */

import { test, expect, type APIRequestContext, type Page } from '@playwright/test';

const BACKEND_URL = 'http://127.0.0.1:8000';
const PLAN_MANAGEMENT_BUTTON_NAME = /GENERATE PLANS|VIEW PLANS|PLAN SELECTED:/i;
const CURRENT_STATE_TEST_ID = 'current-mission-state';

async function resetMission(request: APIRequestContext): Promise<void> {
  const response = await request.post(`${BACKEND_URL}/api/mission/reset`);
  expect(response.ok()).toBeTruthy();
}

async function waitForMissionControlReady(page: Page): Promise<void> {
  await expect(page.getByText('MISSION CONTROLS')).toBeVisible({ timeout: 15_000 });
  await expect(page.getByTestId(CURRENT_STATE_TEST_ID)).toHaveText('IDLE', { timeout: 15_000 });
  await expect(page.locator('header').getByText('CONNECTED', { exact: true })).toBeVisible({
    timeout: 30_000,
  });
}

async function clickMissionControlButton(page: Page, buttonName: RegExp): Promise<void> {
  const button = page.getByRole('button', { name: buttonName });
  await expect(button).toBeEnabled();
  await button.click();
}

async function closePlansPopup(page: Page): Promise<void> {
  const closeButton = page.getByRole('button', { name: /Close plans popup/i });
  await expect(closeButton).toBeVisible();
  await closeButton.focus();
  await closeButton.press('Enter');
}

test.describe('LunaYield Error/Safety Flow', () => {
  test.describe.configure({ timeout: 75_000 });

  test.beforeEach(async ({ page, request }) => {
    await resetMission(request);
    await page.goto('/mission-control');
    await waitForMissionControlReady(page);
  });

  test.afterEach(async ({ request }) => {
    await resetMission(request);
  });

  test('invalid controls are disabled per mission state', async ({ page }) => {
    // IDLE state: only Start Mission and Reset enabled
    await expect(page.getByRole('button', { name: /START MISSION/i })).toBeEnabled();
    await expect(page.getByRole('button', { name: /PAUSE/i })).toBeDisabled();
    await expect(page.getByRole('button', { name: /RESUME/i })).toBeDisabled();
    await expect(page.getByRole('button', { name: /INJECT ANOMALY/i })).toBeDisabled();
    await expect(page.getByRole('button', { name: /GENERATE PLANS/i })).toBeDisabled();
    await expect(page.getByRole('button', { name: /RESET MISSION/i })).toBeEnabled();

    // Start mission → RUNNING
    await clickMissionControlButton(page, /START MISSION/i);
    await expect(page.getByTestId(CURRENT_STATE_TEST_ID)).toHaveText('RUNNING');

    // RUNNING: Pause, Inject Anomaly, Reset enabled; Start, Resume, Generate Plans disabled
    await expect(page.getByRole('button', { name: /START MISSION/i })).toBeDisabled();
    await expect(page.getByRole('button', { name: /PAUSE/i })).toBeEnabled();
    await expect(page.getByRole('button', { name: /RESUME/i })).toBeDisabled();
    await expect(page.getByRole('button', { name: /INJECT ANOMALY/i })).toBeEnabled();
    await expect(page.getByRole('button', { name: /GENERATE PLANS/i })).toBeDisabled();
    await expect(page.getByRole('button', { name: /RESET MISSION/i })).toBeEnabled();

    // Inject anomaly → ANOMALY
    await clickMissionControlButton(page, /INJECT ANOMALY/i);
    await expect(page.getByTestId(CURRENT_STATE_TEST_ID)).toHaveText('ANOMALY');

    // ANOMALY: Generate Plans, Reset enabled; others disabled
    await expect(page.getByRole('button', { name: /START MISSION/i })).toBeDisabled();
    await expect(page.getByRole('button', { name: /PAUSE/i })).toBeDisabled();
    await expect(page.getByRole('button', { name: /RESUME/i })).toBeDisabled();
    await expect(page.getByRole('button', { name: /INJECT ANOMALY/i })).toBeDisabled();
    await expect(page.getByRole('button', { name: /GENERATE PLANS/i })).toBeEnabled();
    await expect(page.getByRole('button', { name: /RESET MISSION/i })).toBeEnabled();

    // Generate plans → AWAITING_APPROVAL
    await clickMissionControlButton(page, /GENERATE PLANS/i);
    await expect(page.getByTestId(CURRENT_STATE_TEST_ID)).toHaveText('AWAITING_APPROVAL');
    await expect(page.getByRole('heading', { name: /Generated mission plans/i })).toBeVisible();
    await closePlansPopup(page);
    await expect(page.getByRole('heading', { name: /Generated mission plans/i })).not.toBeVisible();

    // AWAITING_APPROVAL: View Plans and Reset enabled; others disabled
    await expect(page.getByRole('button', { name: /START MISSION/i })).toBeDisabled();
    await expect(page.getByRole('button', { name: /PAUSE/i })).toBeDisabled();
    await expect(page.getByRole('button', { name: /RESUME/i })).toBeDisabled();
    await expect(page.getByRole('button', { name: /INJECT ANOMALY/i })).toBeDisabled();
    await expect(page.getByRole('button', { name: PLAN_MANAGEMENT_BUTTON_NAME })).toBeEnabled();
    await expect(page.getByRole('button', { name: /RESET MISSION/i })).toBeEnabled();
  });

  test('rejected Aggressive Survey is visible with violations but non-actionable', async ({ page }) => {
    // Setup: start mission, inject anomaly, generate plans
    await clickMissionControlButton(page, /START MISSION/i);
    await expect(page.getByTestId(CURRENT_STATE_TEST_ID)).toHaveText('RUNNING');

    await clickMissionControlButton(page, /INJECT ANOMALY/i);
    await expect(page.getByTestId(CURRENT_STATE_TEST_ID)).toHaveText('ANOMALY');

    await clickMissionControlButton(page, /GENERATE PLANS/i);
    await expect(page.getByTestId(CURRENT_STATE_TEST_ID)).toHaveText('AWAITING_APPROVAL');

    // Find Aggressive Survey card
    const aggressiveCard = page.locator('[data-testid="plan-card"]', { hasText: 'Aggressive Survey' });

    // Verify REJECTED status
    await expect(aggressiveCard.locator('[data-testid="plan-status"]').filter({ hasText: 'REJECTED' })).toBeVisible();

    // Verify safety violation is displayed with rule ID, description, measured/threshold
    await expect(aggressiveCard.getByText('SAFETY VIOLATIONS')).toBeVisible();
    await expect(aggressiveCard.getByText('[RETURN_BATTERY_MIN_20PCT]')).toBeVisible();
    await expect(aggressiveCard.getByText('Predicted return battery 10.5% is below minimum 20.0%')).toBeVisible();
    await expect(aggressiveCard.getByText('(measured: 10.5, threshold: 20.0)')).toBeVisible();

    // Verify NO approve button - only "REJECTED - CANNOT APPROVE" text
    await expect(aggressiveCard.getByText('REJECTED - CANNOT APPROVE')).toBeVisible();
    await expect(aggressiveCard.getByRole('button', { name: /APPROVE/i })).not.toBeVisible();

    // Verify it is NOT recommended
    await expect(aggressiveCard.getByText('RECOMMENDED', { exact: true })).not.toBeVisible();
  });

  test('backend 422 error is surfaced to operator via frontend rendering', async ({ page }) => {
    // Setup: get to AWAITING_APPROVAL with plans generated
    await clickMissionControlButton(page, /START MISSION/i);
    await expect(page.getByTestId(CURRENT_STATE_TEST_ID)).toHaveText('RUNNING');

    await clickMissionControlButton(page, /INJECT ANOMALY/i);
    await expect(page.getByTestId(CURRENT_STATE_TEST_ID)).toHaveText('ANOMALY');

    await clickMissionControlButton(page, /GENERATE PLANS/i);
    await expect(page.getByTestId(CURRENT_STATE_TEST_ID)).toHaveText('AWAITING_APPROVAL');

    // Get the Extended Survey plan ID from the UI
    const extendedCard = page.locator('[data-testid="plan-card"]', { hasText: 'Extended Survey' });
    const approveButton = extendedCard.getByRole('button', { name: /APPROVE \(RECOMMENDED\)/i });
    await expect(approveButton).toBeVisible();

    // Intercept the approval API call and return a 422
    await page.route('**/api/plans/plan-b-001/approve', async (route) => {
      await route.fulfill({
        status: 422,
        contentType: 'application/json',
        body: JSON.stringify({
          detail: "Plan plan-b-001 is unsafe: Predicted return battery 42.0% is below minimum 20.0%"
        })
      });
    });

    // Click approve - should trigger intercepted 422
    await approveButton.click();

    // Verify error is displayed in the approval error area
    await expect(page.getByText('APPROVAL FAILED:')).toBeVisible({ timeout: 5000 });
    await expect(page.getByText(/Plan plan-b-001 is unsafe/i)).toBeVisible();
  });

  test('WebSocket connection status shows CONNECTED', async ({ page }) => {
    // MissionHeader shows WS status as "CONNECTED" (with "WS" label separate)
    await expect(page.locator('header').getByText('CONNECTED', { exact: true })).toBeVisible({ timeout: 15000 });
  });

  test('generated plans popup can be reopened through VIEW PLANS without regenerating', async ({
    page,
  }) => {
    let generateRequestCount = 0;
    page.on('request', (request) => {
      if (
        request.method() === 'POST' &&
        request.url().endsWith('/api/plans/generate')
      ) {
        generateRequestCount += 1;
      }
    });

    await clickMissionControlButton(page, /START MISSION/i);
    await expect(page.getByTestId(CURRENT_STATE_TEST_ID)).toHaveText('RUNNING');

    await clickMissionControlButton(page, /INJECT ANOMALY/i);
    await expect(page.getByTestId(CURRENT_STATE_TEST_ID)).toHaveText('ANOMALY');

    await clickMissionControlButton(page, /GENERATE PLANS/i);
    await expect(page.getByTestId(CURRENT_STATE_TEST_ID)).toHaveText('AWAITING_APPROVAL');
    await expect(page.getByRole('heading', { name: /Generated mission plans/i })).toBeVisible();
    await expect(generateRequestCount).toBe(1);

    const aggressiveCard = page.locator('[data-testid="plan-card"]', {
      hasText: 'Aggressive Survey',
    });
    await expect(aggressiveCard.getByText('REJECTED - CANNOT APPROVE')).toBeVisible();
    await expect(aggressiveCard.getByRole('button', { name: /APPROVE/i })).not.toBeVisible();

    await closePlansPopup(page);
    await expect(page.getByRole('heading', { name: /Generated mission plans/i })).not.toBeVisible();
    await expect(page.getByRole('button', { name: /VIEW PLANS/i })).toBeEnabled();
    await expect(generateRequestCount).toBe(1);

    await page.getByRole('button', { name: /VIEW PLANS/i }).click();
    await expect(page.getByRole('heading', { name: /Generated mission plans/i })).toBeVisible();
    await expect(generateRequestCount).toBe(1);

    const extendedCard = page.locator('[data-testid="plan-card"]', { hasText: 'Extended Survey' });
    await Promise.all([
      page.waitForResponse(
        (response) =>
          response.request().method() === 'POST' &&
          response.url().endsWith('/api/plans/plan-b-001/approve') &&
          response.ok()
      ),
      extendedCard.getByRole('button', { name: /APPROVE \(RECOMMENDED\)/i }).click(),
    ]);

    await expect(page.getByTestId(CURRENT_STATE_TEST_ID)).toHaveText('EXECUTING');
    await expect(
      page.getByRole('button', { name: /PLAN SELECTED: EXTENDED SURVEY/i })
    ).toBeDisabled();
  });
});
