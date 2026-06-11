import { expect, test, type Page } from "@playwright/test";

const proposal = {
  id: 7,
  organization_id: 1,
  grant_id: 44,
  status: "completed",
  content: "## Executive Summary\n\nInitial proposal body.",
  compatibility_score: 0.82,
  created_at: "2026-06-11T00:00:00Z",
  updated_at: null,
};

function section(content = "Initial proposal body.", version = 1, status = "completed") {
  return {
    id: 11,
    proposal_id: 7,
    section_key: "executive_summary",
    name: "Executive Summary",
    description: "Summarize the project and funding case.",
    weight: 0.25,
    content_json: {
      type: "doc",
      content: [
        {
          type: "paragraph",
          content: [{ type: "text", text: content }],
        },
      ],
    },
    order: 0,
    status,
    version,
    edited_at: null,
    edited_by: null,
    created_at: "2026-06-11T00:00:00Z",
    updated_at: null,
  };
}

async function mockProposalApi(page: Page, role: "writer" | "viewer") {
  let currentSection = section();

  await page.context().addCookies([
    {
      name: "access_token",
      value: "e2e-session",
      domain: "localhost",
      path: "/",
    },
  ]);

  await page.route("**/api/v1/users/me", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        id: 1,
        email: `${role}@example.com`,
        full_name: "Proposal User",
        role,
        organization_id: 1,
        created_at: "2026-06-11T00:00:00Z",
      }),
    });
  });
  await page.route("**/api/v1/proposals/7", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(proposal),
    });
  });
  await page.route("**/api/v1/proposals/7/sections", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([currentSection]),
    });
  });
  await page.route("**/api/v1/proposals/7/sections/11", async (route) => {
    if (route.request().method() === "PATCH") {
      const payload = route.request().postDataJSON();
      currentSection = {
        ...currentSection,
        content_json: payload.content_json,
        version: currentSection.version + 1,
      };
    }
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(currentSection),
    });
  });
  await page.route(
    "**/api/v1/proposals/7/sections/11/regenerate",
    async (route) => {
      currentSection = { ...currentSection, status: "generating" };
      await route.fulfill({
        status: 202,
        contentType: "application/json",
        body: JSON.stringify(currentSection),
      });
    },
  );
}

test("writer edits, autosaves, and starts section regeneration", async ({ page }) => {
  await mockProposalApi(page, "writer");
  await page.goto("/en/proposals/7");

  await expect(page.getByRole("heading", { name: "Proposal Workspace" })).toBeVisible();
  await expect(page.getByRole("button", { name: /executive summary/i })).toBeVisible();

  const editor = page.getByLabel("Proposal section editor");
  await editor.click();
  await page.keyboard.press("Control+A");
  await page.keyboard.type("Updated proposal body");

  await expect(page.getByText("Saved", { exact: true })).toBeVisible({ timeout: 5000 });
  await page.reload();
  await expect(page.getByLabel("Proposal section editor")).toContainText(
    "Updated proposal body",
  );

  page.once("dialog", (dialog) => dialog.accept());
  await page.getByRole("button", { name: /regenerate section/i }).click();
  await expect(page.getByLabel("Generating")).toBeVisible();
});

test("viewer receives a read-only proposal workspace", async ({ page }) => {
  await mockProposalApi(page, "viewer");
  await page.goto("/en/proposals/7");

  await expect(page.getByText(/viewer role has read-only access/i)).toBeVisible();
  await expect(page.getByRole("button", { name: /regenerate section/i })).toHaveCount(0);
  await expect(page.getByLabel("Proposal section editor")).toHaveAttribute(
    "contenteditable",
    "false",
  );
});
