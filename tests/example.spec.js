const { test, expect } = require('@playwright/test');

test('homepage has Playwright in title', async ({ page }) => {
  await page.goto('https://playwright.dev/');
  await expect(page).toHaveTitle(/Playwright/);
});

test('get started link navigates to intro page', async ({ page }) => {
  await page.goto('https://playwright.dev/');
  await page.click('text=Get started');
  await expect(page).toHaveURL(/.*intro/);
});

test('take a screenshot of homepage', async ({ page }) => {
  await page.goto('https://playwright.dev/');
  await page.screenshot({ path: 'homepage.png' });
});
