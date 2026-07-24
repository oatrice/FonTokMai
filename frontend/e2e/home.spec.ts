import { test, expect } from '@playwright/test';

test('has title and navbar', async ({ page }) => {
  await page.goto('/');
  await expect(page.locator('text=FonMaYang').first()).toBeVisible();
});
