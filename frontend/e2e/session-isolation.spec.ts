import { expect, test } from '@playwright/test';

test.describe('LunaYield Demo Session Isolation', () => {
  test.describe.configure({ timeout: 90_000 });

  test('two independent browser sessions do not control each other', async ({
    browser,
  }) => {
    const contextA = await browser.newContext();
    const contextB = await browser.newContext();
    const pageA = await contextA.newPage();
    const pageB = await contextB.newPage();

    try {
      await pageA.goto('/mission-control');
      await pageB.goto('/mission-control');

      await Promise.all([
        expect(pageA.getByText('MISSION CONTROLS')).toBeVisible({ timeout: 15_000 }),
        expect(pageB.getByText('MISSION CONTROLS')).toBeVisible({ timeout: 15_000 }),
        expect(pageA.getByTestId('current-mission-state')).toHaveText('IDLE', {
          timeout: 15_000,
        }),
        expect(pageB.getByTestId('current-mission-state')).toHaveText('IDLE', {
          timeout: 15_000,
        }),
      ]);

      await pageA.getByRole('button', { name: /START MISSION/i }).click();
      await expect(pageA.getByTestId('current-mission-state')).toHaveText('RUNNING');
      await expect(pageB.getByTestId('current-mission-state')).toHaveText('IDLE');

      await pageB.getByRole('button', { name: /RESET MISSION/i }).click();
      await expect(pageB.getByTestId('current-mission-state')).toHaveText('IDLE');
      await expect(pageA.getByTestId('current-mission-state')).toHaveText('RUNNING');

      await pageA.getByRole('button', { name: /INJECT ANOMALY/i }).click();
      await expect(pageA.getByTestId('current-mission-state')).toHaveText('ANOMALY');
      await expect(pageA.getByText(/BATTERY ANOMALY ACTIVE/i)).toBeVisible();
      await expect(pageB.getByTestId('current-mission-state')).toHaveText('IDLE');
    } finally {
      await contextA.close();
      await contextB.close();
    }
  });
});
