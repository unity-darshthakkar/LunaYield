/**
 * Golden-path E2E test for LunaYield Phase 1D demo.
 *
 * Exercises the complete operator flow against real backend/frontend:
 * IDLE → RUNNING → ANOMALY → PLANNING → AWAITING_APPROVAL → EXECUTING → RESET → IDLE
 */

import { test, expect, type APIRequestContext } from '@playwright/test';

const BACKEND_URL = 'http://127.0.0.1:8000';

test.describe.configure({ timeout: 90_000 });

async function resetMission(request: APIRequestContext): Promise<void> {
  const response = await request.post(`${BACKEND_URL}/api/mission/reset`);
  expect(response.ok()).toBeTruthy();
}

test.describe('LunaYield Mission Flow - Golden Path', () => {

  test.beforeEach(async ({ page, request }) => {
    // Ensure clean mission state before each test
    await resetMission(request);
    await page.goto('/mission-control');
    // Wait for mission state to load - wait for WS to be connected and page ready
    await expect(page.getByText('MISSION CONTROLS')).toBeVisible({ timeout: 15000 });
    // Wait for WebSocket to connect
    await expect(page.locator('header').getByText('CONNECTED', { exact: true })).toBeVisible({ timeout: 30000 });
  });

  test.afterEach(async ({ request }) => {
    // Clean up after test
    await resetMission(request);
  });

  test('complete mission flow: IDLE → RUNNING → ANOMALY → AWAITING_APPROVAL → EXECUTING → RESET', async ({ page }) => {
    // ==========================================
    // STEP 1: Load app, verify IDLE state
    // ==========================================
    await expect(page.getByRole('button', { name: /START MISSION/i })).toBeEnabled();
    await expect(page.getByRole('button', { name: /PAUSE/i })).toBeDisabled();
    await expect(page.getByRole('button', { name: /RESUME/i })).toBeDisabled();
    await expect(page.getByRole('button', { name: /INJECT ANOMALY/i })).toBeDisabled();
    await expect(page.getByRole('button', { name: /GENERATE PLANS/i })).toBeDisabled();

    // Verify IDLE state in the MissionControls Current State panel
    await expect(page.getByTestId('current-mission-state')).toHaveText('IDLE');
    await expect(page.getByText('CURRENT STATE:')).toBeVisible();

    // Telemetry should show idle state
    await expect(page.getByText('Awaiting telemetry stream...')).toBeVisible();

    // ==========================================
    // STEP 2: Start Mission → RUNNING
    // ==========================================
    await page.getByRole('button', { name: /START MISSION/i }).click();

    // Wait for status transition - header badge shows RUNNING
    await expect(page.getByTestId('current-mission-state')).toHaveText('RUNNING');

    // Verify buttons update correctly
    await expect(page.getByRole('button', { name: /START MISSION/i })).toBeDisabled();
    await expect(page.getByRole('button', { name: /PAUSE/i })).toBeEnabled();
    await expect(page.getByRole('button', { name: /INJECT ANOMALY/i })).toBeEnabled();
    await expect(page.getByRole('button', { name: /GENERATE PLANS/i })).toBeDisabled();

    // ==========================================
    // STEP 3: Wait for live telemetry to appear
    // ==========================================
    // TelemetryPanel should transition from "Awaiting telemetry" to showing real data
    await expect(page.getByText('Awaiting telemetry stream...')).not.toBeVisible({ timeout: 30000 });
    // Verify at least battery percentage is displayed (real telemetry sample received)
    await expect(page.getByText(/\d+\.\d+%/).first()).toBeVisible({ timeout: 30000 });

    // ==========================================
    // STEP 4: Inject Anomaly → ANOMALY
    // ==========================================
    await page.getByRole('button', { name: /INJECT ANOMALY/i }).click();

    await expect(page.getByTestId('current-mission-state')).toHaveText('ANOMALY');
    // Anomaly badge should appear
    await expect(page.getByText(/BATTERY ANOMALY ACTIVE/i)).toBeVisible();

    // Buttons update correctly
    await expect(page.getByRole('button', { name: /INJECT ANOMALY/i })).toBeDisabled();
    await expect(page.getByRole('button', { name: /GENERATE PLANS/i })).toBeEnabled();

    // ==========================================
    // STEP 5: Generate Plans → AWAITING_APPROVAL
    // ==========================================
    await page.getByRole('button', { name: /GENERATE PLANS/i }).click();

    await expect(page.getByTestId('current-mission-state')).toHaveText('AWAITING_APPROVAL');
    await expect(page.getByText(/CANDIDATE PLAN\(S\) AVAILABLE/i)).toBeVisible();

    // ==========================================
    // STEP 6: Verify exactly 3 candidate plans displayed
    // ==========================================
    const planCards = page.locator('[data-testid="plan-card"]');
    await expect(planCards).toHaveCount(3);

    // Check all three plan labels exist
    await expect(page.getByText('Minimal Survey')).toBeVisible();
    await expect(page.getByText('Extended Survey')).toBeVisible();
    await expect(page.getByText('Aggressive Survey')).toBeVisible();

    // ==========================================
    // STEP 7: Verify Minimal Survey = VALID, not recommended
    // ==========================================
    const minimalCard = page.locator('[data-testid="plan-card"]', { hasText: 'Minimal Survey' });
    await expect(minimalCard.getByText('VALID')).toBeVisible();
    await expect(minimalCard.getByText('RECOMMENDED')).not.toBeVisible();
    // Should have approve button (not recommended variant)
    await expect(minimalCard.getByRole('button', { name: /APPROVE PLAN/i })).toBeVisible();

    // ==========================================
    // STEP 8: Verify Extended Survey = VALID + RECOMMENDED
    // ==========================================
    const extendedCard = page.locator('[data-testid="plan-card"]', { hasText: 'Extended Survey' });
    await expect(extendedCard.getByText('VALID')).toBeVisible();
    // RECOMMENDED badge (span, not button)
    await expect(extendedCard.locator('span', { hasText: 'RECOMMENDED' })).toBeVisible();
    // Should have recommended approve button
    await expect(extendedCard.getByRole('button', { name: /APPROVE \(RECOMMENDED\)/i })).toBeVisible();

    // ==========================================
    // STEP 9: Verify Aggressive Survey = REJECTED
    // ==========================================
    const aggressiveCard = page.locator('[data-testid="plan-card"]', { hasText: 'Aggressive Survey' });
    // REJECTED status badge (not the "REJECTED - CANNOT APPROVE" text)
    await expect(aggressiveCard.locator('[data-testid="plan-status"]').filter({ hasText: 'REJECTED' })).toBeVisible();
    // RECOMMENDED should not be visible
    await expect(aggressiveCard.getByText('RECOMMENDED', { exact: true })).not.toBeVisible();

    // ==========================================
    // STEP 10: Verify Aggressive Survey safety violation visible
    // ==========================================
    await expect(aggressiveCard.getByText('SAFETY VIOLATIONS')).toBeVisible();
    await expect(aggressiveCard.getByText('[RETURN_BATTERY_MIN_20PCT]')).toBeVisible();
    await expect(aggressiveCard.getByText('Predicted return battery 11.0% is below minimum 20.0%')).toBeVisible();
    await expect(aggressiveCard.getByText('(measured: 11.0, threshold: 20.0)')).toBeVisible();

    // ==========================================
    // STEP 11: Verify Aggressive Survey has NO actionable approval button
    // ==========================================
    await expect(aggressiveCard.getByText('REJECTED - CANNOT APPROVE')).toBeVisible();
    await expect(aggressiveCard.getByRole('button', { name: /APPROVE/i })).not.toBeVisible();

    // ==========================================
    // STEP 12: Approve Extended Survey
    // ==========================================
    await extendedCard.getByRole('button', { name: /APPROVE \(RECOMMENDED\)/i }).click();

    // ==========================================
    // STEP 13: Verify mission becomes EXECUTING
    // ==========================================
    await expect(page.getByTestId('current-mission-state')).toHaveText('EXECUTING');

    // ==========================================
    // STEP 14: Verify approved plan is reflected in frozen mission-control UI
    // ==========================================
    await expect(page.getByTestId('current-mission-state')).toHaveText('EXECUTING');
    await expect(page.getByRole('button', { name: /PLAN SELECTED: EXTENDED SURVEY/i })).toBeDisabled();

    // ==========================================
    // STEP 15: Verify active route reflects approved plan
    // ==========================================
    // RoutePanel should show the active route (now matching Extended Survey)
    const routePanel = page.getByText('ACTIVE ROUTE').locator('..');
    await expect(routePanel.getByText('Approved plan: Extended Survey')).toBeVisible();
    await expect(routePanel.getByText('Base Camp')).toHaveCount(2); // Start + Return
    await expect(routePanel.getByText('Crater A Rim')).toBeVisible();
    await expect(routePanel.getByText('Ice Deposit Site')).toBeVisible();
    await expect(routePanel.getByText('Ridge Observation Point')).toBeVisible();

    // ==========================================
    // STEP 16: Verify plan.approved audit event exists
    // ==========================================
    await page.getByRole('button', { name: /Open audit trail/i }).click();
    const auditPanel = page.getByText('AUDIT TRAIL').locator('..');
    await expect(auditPanel.getByText('plan.approved')).toBeVisible();
    await page.getByRole('button', { name: /Close audit trail/i }).click();

    // ==========================================
    // STEP 17: Reset Mission → IDLE
    // ==========================================
    await page.getByRole('button', { name: /RESET MISSION/i }).click();

    // ==========================================
    // STEP 18: Verify mission returns to IDLE
    // ==========================================
    await expect(page.getByTestId('current-mission-state')).toHaveText('IDLE');

    // ==========================================
    // STEP 19: Verify candidate plans are cleared
    // ==========================================
    await expect(page.getByText('CANDIDATE PLANS')).not.toBeVisible();

    // ==========================================
    // STEP 20: Verify reset audit behavior
    // ==========================================
    await page.getByRole('button', { name: /Open audit trail/i }).click();
    // Should have mission.reset in audit trail
    await expect(auditPanel.getByText('mission.reset')).toBeVisible();
    // Should still have seed event
    await expect(auditPanel.getByText('mission.initialized')).toBeVisible();

    // ==========================================
    // STEP 21: Verify telemetry returns to idle state
    // ==========================================
    await expect(page.getByText('Awaiting telemetry stream...')).toBeVisible({ timeout: 5000 });
  });
});
