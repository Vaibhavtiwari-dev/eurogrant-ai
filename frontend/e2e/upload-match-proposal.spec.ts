import { test, expect } from '@playwright/test';
import path from 'path';
import fs from 'fs';

// This e2e covers the critical user journey:
//  register → login → upload PDF → assert uploaded → check matches tab.
//
// It runs against a live dev server (see playwright.config.ts webServer).
// Selectors use getByLabel (the forms use aria-label rather than name=).

const FIXTURE_DIR = path.join(__dirname, 'fixtures');
const UNIQUE_EMAIL = `e2e_${Date.now()}@example.com`;
const INVITE_CODE = process.env.MASTER_INVITE_CODE || 'test-invite';

test.beforeAll(() => {
  fs.mkdirSync(FIXTURE_DIR, { recursive: true });
  // Minimal valid PDF (header only — backend only checks first 8 bytes for magic).
  const fixturePath = path.join(FIXTURE_DIR, 'sample.pdf');
  if (!fs.existsSync(fixturePath)) {
    fs.writeFileSync(
      fixturePath,
      Buffer.from([0x25, 0x50, 0x44, 0x46, 0x2d, 0x31, 0x2e, 0x34, 0x0a])
    );
  }
});

test('register → login → upload → matches-tab flow', async ({ page }) => {
  // 1. Land on the marketing page; middleware redirects to /login
  await page.goto('/en');
  await expect(page).toHaveURL(/\/en\/login/);

  // 2. Click the "Request Intelligence Access" link to go to /register
  await page.getByRole('link', { name: /request intelligence access/i }).click();
  await expect(page).toHaveURL(/\/en\/register/);

  // 3. Fill the registration form (queries use the inputs' aria-label)
  await page.getByLabel('Full Name').fill('E2E User');
  await page.getByLabel('Organization Name').fill('E2E Org');
  await page.getByLabel('Email').fill(UNIQUE_EMAIL);
  await page.getByLabel('Password').fill('secure-password-123');
  await page.getByLabel('Invite Code').fill(INVITE_CODE);
  await page.getByRole('button', { name: /enroll agent/i }).click();

  // 4. Register redirects back to /login. Log in with the same credentials.
  await expect(page).toHaveURL(/\/en\/login/);
  await page.getByLabel('Email').fill(UNIQUE_EMAIL);
  await page.getByLabel('Password').fill('secure-password-123');
  await page.getByRole('button', { name: /authorize access/i }).click();

  // 5. Land on the dashboard
  await expect(page).toHaveURL(/\/en\/dashboard/);

  // 6. Open the upload modal and submit a sample PDF
  await page.getByRole('button', { name: /submit documentation|upload/i }).first().click();
  await page.setInputFiles('input[type="file"]', path.join(FIXTURE_DIR, 'sample.pdf'));
  // The upload submit button is inside the modal — scope to it
  await page.getByRole('button', { name: /^upload$/i }).click();

  // 7. The document list refreshes via refreshKey; sample.pdf should appear
  //    in the DocumentList panel (it shows even while still pending).
  await expect(page.getByText('sample.pdf')).toBeVisible({ timeout: 15_000 });

  // 8. Switch to the Semantic Matches tab. "Matched Grants" is not a route —
  //    the matches live on the dashboard under this tab.
  await page.getByRole('button', { name: /semantic matches/i }).click();

  // 9. MatchedGrants shows a "no matches" empty state when the pipeline has
  //    nothing to score yet. Either state is acceptable here; the test passes
  //    if the tab renders without error and (optionally) a Draft Proposal
  //    button is reachable.
  const matchesTab = page.getByRole('button', { name: /semantic matches/i });
  await expect(matchesTab).toBeVisible();

  const draftButtons = page.getByRole('button', { name: /draft proposal/i });
  if ((await draftButtons.count()) > 0) {
    // RAG generation is scheduled for a later phase; the button surfaces an
    // informational toast. We don't assert the toast text because the
    // messaging may evolve.
    await expect(draftButtons.first()).toBeVisible();
  }
});

