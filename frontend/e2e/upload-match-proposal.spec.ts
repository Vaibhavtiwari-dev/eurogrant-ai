import { expect, test, type Page } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";

const FIXTURE_DIR = path.join(__dirname, "fixtures");
const FIXTURE_PATH = path.join(FIXTURE_DIR, "sample.pdf");
const TEST_EMAIL = "e2e@example.com";
const TEST_PASSWORD = "Secure-password-123!";

test.beforeAll(() => {
  fs.mkdirSync(FIXTURE_DIR, { recursive: true });
  if (!fs.existsSync(FIXTURE_PATH)) {
    fs.writeFileSync(
      FIXTURE_PATH,
      Buffer.from([0x25, 0x50, 0x44, 0x46, 0x2d, 0x31, 0x2e, 0x34, 0x0a]),
    );
  }
});

async function mockDashboardApi(page: Page) {
  let loggedIn = false;
  let documents: Array<Record<string, unknown>> = [];

  await page.route("**/api/v1/**", async (route) => {
    const request = route.request();
    const pathname = new URL(request.url()).pathname;

    if (pathname.endsWith("/auth/register")) {
      await route.fulfill({ status: 201, contentType: "application/json", body: "{}" });
      return;
    }

    if (pathname.endsWith("/auth/login")) {
      loggedIn = true;
      await page.context().addCookies([
        {
          name: "access_token",
          value: "e2e-session",
          domain: "localhost",
          path: "/",
        },
      ]);
      await route.fulfill({ status: 200, contentType: "application/json", body: "{}" });
      return;
    }

    if (pathname.endsWith("/users/me")) {
      await route.fulfill({
        status: loggedIn ? 200 : 401,
        contentType: "application/json",
        body: JSON.stringify(
          loggedIn
            ? {
                id: 1,
                email: TEST_EMAIL,
                full_name: "E2E User",
                role: "writer",
                organization_id: 1,
                created_at: "2026-06-11T00:00:00Z",
              }
            : { detail: "Not authenticated" },
        ),
      });
      return;
    }

    if (pathname.endsWith("/uploads/company-document")) {
      documents = [
        {
          id: 1,
          file_name: "sample.pdf",
          status: "pending",
          created_at: "2026-06-11T00:00:00Z",
        },
      ];
      await route.fulfill({
        status: 202,
        contentType: "application/json",
        body: JSON.stringify(documents[0]),
      });
      return;
    }

    if (pathname.endsWith("/uploads/documents")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(documents),
      });
      return;
    }

    if (pathname.endsWith("/organizations/dashboard-overview")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          stats: {
            active_high_matches: 0,
            ai_generation_quality: 0,
            total_pipeline_value: 0,
          },
          pipelines: [],
          hot_matches: [],
        }),
      });
      return;
    }

    if (pathname.endsWith("/organizations/me")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          id: 1,
          name: "E2E Org",
          subscription_tier: "standard",
          sector: null,
          headcount_range: null,
          revenue_tier: null,
          legal_entity_type: null,
          countries_of_operation: null,
          core_technologies: null,
          match_threshold: 0.7,
          alert_email_enabled: true,
          created_at: "2026-06-11T00:00:00Z",
        }),
      });
      return;
    }

    if (pathname.endsWith("/grants/matches")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: "[]",
      });
      return;
    }

    await route.fulfill({
      status: 404,
      contentType: "application/json",
      body: JSON.stringify({ detail: `Unhandled E2E API route: ${pathname}` }),
    });
  });
}

test("register, login, upload, and matches-tab flow", async ({ page }) => {
  await mockDashboardApi(page);
  await page.goto("/en/login");

  await page.getByRole("link", { name: /request intelligence access/i }).click();
  await page.getByLabel("Full Name").fill("E2E User");
  await page.getByLabel("Organization Name").fill("E2E Org");
  await page.getByLabel("Email").fill(TEST_EMAIL);
  await page.getByLabel("Password").fill(TEST_PASSWORD);
  await page.getByLabel("Invite Code").fill("test-invite");
  await page.getByRole("button", { name: /register/i }).click();

  await expect(page).toHaveURL(/\/en\/login/);
  await page.getByLabel("Email").fill(TEST_EMAIL);
  await page.getByLabel("Password").fill(TEST_PASSWORD);
  await page.getByRole("button", { name: /sign in/i }).click();

  await expect(page).toHaveURL(/\/en\/dashboard/);
  await page.getByRole("button", { name: /new proposal/i }).click();
  await page.setInputFiles('input[type="file"]', FIXTURE_PATH);
  await expect(page.getByText("sample.pdf")).toBeVisible({ timeout: 10_000 });

  await page.getByRole("tab", { name: /semantic matches/i }).click();
  await expect(
    page.getByRole("heading", { name: /no high-probability matches detected/i }),
  ).toBeVisible();
});
