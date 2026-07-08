// Optional Playwright smoke test skeleton. Run after: npm i -D @playwright/test
const { test, expect } = require('@playwright/test');
const BASE = process.env.BASE_URL || 'http://127.0.0.1:5000';

test('public home loads and phone is not exposed by default', async ({ page }) => {
  await page.goto(BASE + '/');
  await expect(page).toHaveTitle(/M-GROUPS|Infrastructure|Civil/i);
  await expect(page.locator('body')).not.toContainText('8220141414');
});

test('admin login page loads', async ({ page }) => {
  await page.goto(BASE + '/admin');
  await expect(page.locator('body')).toContainText(/Admin|Login/i);
});
