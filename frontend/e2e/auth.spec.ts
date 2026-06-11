import { test, expect } from '@playwright/test';

test('should show login page and allow login attempt', async ({ page }) => {
  await page.goto('/en/login');
  await expect(page).toHaveURL(/\/en\/login/);
  
  // Check for the headline
  await expect(page.locator('h1')).toContainText(/EuroGrant AI/i);
  
  // Fill login form
  await page.fill('input[type="email"]', 'agent@eurogrant.ai');
  await page.fill('input[type="password"]', 'secure-password');
  
  // Verify UI elements
  await expect(page.locator('button[type="submit"]')).toBeVisible();
});

test('should navigate to register page', async ({ page }) => {
  await page.goto('/en/login');
  await page.click('text=Request Intelligence Access');
  await expect(page).toHaveURL(/\/register/);
  await expect(page.locator('h2')).toContainText('Create Account');
});
