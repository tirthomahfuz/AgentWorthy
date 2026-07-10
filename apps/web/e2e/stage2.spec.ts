import { test, expect } from "@playwright/test";

/**
 * Stage 2 E2E — requires:
 * - NEXT_PUBLIC_API_URL pointing at running API with migrated DB
 * - NEXTAUTH_SECRET set
 * - Web dev server on baseURL
 *
 * In CI without full stack, tests validate fixture site verification HTML.
 */
test.describe("Stage 2 site verification fixture", () => {
  test("fixture site contains verification meta tag", async ({ page }) => {
    await page.goto("http://localhost:8765/site.html");
    const meta = page.locator('meta[name="agentworthy-verification"]');
    await expect(meta).toHaveAttribute("content", "E2E_FIXTURE_TOKEN");
  });

  test("fixture site has semantic form", async ({ page }) => {
    await page.goto("http://localhost:8765/site.html");
    await expect(page.locator('input[name="email"]')).toBeVisible();
  });
});

test.describe("Stage 2 auth pages", () => {
  test("login page renders", async ({ page }) => {
    await page.goto("/login");
    await expect(page.getByRole("heading", { name: "Sign in" })).toBeVisible();
    await expect(page.getByPlaceholder("you@company.com")).toBeVisible();
  });

  test("dashboard redirects unauthenticated users to login", async ({ page }) => {
    await page.goto("/dashboard");
    await page.waitForURL(/\/login/, { timeout: 10000 });
    expect(page.url()).toContain("/login");
  });
});
