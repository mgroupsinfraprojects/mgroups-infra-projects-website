const { test, expect } = require('@playwright/test');

test('admin critical route smoke test', async ({ page }) => {
  await page.goto('/admin/login');
  await page.fill('input[name="username"]', 'admin');
  await page.fill('input[name="password"]', process.env.ADMIN_TEST_PASSWORD || process.env.ADMIN_DEFAULT_PASSWORD || 'set-ADMIN_TEST_PASSWORD');
  await page.click('button[type="submit"]');
  await expect(page).toHaveURL(/\/admin/);

  const routes = [
    '/admin/settings',
    '/admin/gallery',
    '/admin/about',
    '/admin/services/new',
    '/admin/projects/new',
    '/admin/appearance',
    '/admin/page-builder',
    '/admin/media',
    '/admin/permissions',
    '/admin/versions',
    '/admin/ordering'
  ];
  for (const route of routes) {
    await page.goto(route);
    await expect(page.locator('body')).not.toContainText('Internal Server Error');
  }
});
