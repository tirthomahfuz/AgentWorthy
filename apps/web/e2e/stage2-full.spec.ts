import { test, expect } from "@playwright/test";
import * as fs from "fs";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const FIXTURE_URL = process.env.E2E_FIXTURE_URL || "http://localhost:8765/";
const MAGIC_LINK_FILE = "/tmp/agentworthy-magic-link.txt";
const NEXTAUTH_STORE = "/tmp/agentworthy-nextauth-store.json";
const FIXTURE_TOKEN_FILE = "/tmp/agentworthy-fixture-token.txt";
const TEST_EMAIL = "e2e-test@agentworthy.example";

test.describe("Stage 2 full flow", () => {
  test("magic link login, add site, fail/pass verification, scan, dashboard score", async ({
    page,
    request,
  }) => {
    test.setTimeout(300000);

    // 1. Dev magic link login
    if (fs.existsSync(MAGIC_LINK_FILE)) fs.unlinkSync(MAGIC_LINK_FILE);
    if (fs.existsSync(NEXTAUTH_STORE)) fs.unlinkSync(NEXTAUTH_STORE);
    await page.goto("/login");
    await page.getByPlaceholder("you@company.com").fill(TEST_EMAIL);
    await page.getByRole("button", { name: "Send magic link" }).click();

    // Wait for magic link file (written by NextAuth dev handler)
    let magicUrl = "";
    for (let i = 0; i < 60; i++) {
      if (fs.existsSync(MAGIC_LINK_FILE)) {
        magicUrl = fs.readFileSync(MAGIC_LINK_FILE, "utf8").trim();
        if (magicUrl) break;
      }
      await page.waitForTimeout(500);
    }
    expect(magicUrl, "magic link URL must be written to /tmp/agentworthy-magic-link.txt").toBeTruthy();
    await page.goto(magicUrl);
    await page.waitForURL(/\/dashboard/, { timeout: 30000 });

    // 2. Add site pointing at fixture (wrong token initially)
    fs.writeFileSync(FIXTURE_TOKEN_FILE, "wrong-token-for-fail");
    await page.getByRole("button", { name: "Add site" }).click();
    await page.getByPlaceholder("https://example.com").fill(FIXTURE_URL);
    await page.getByPlaceholder("Display name").fill("E2E Fixture Site");
    await page.getByRole("button", { name: "Add site" }).last().click();
    await expect(page.getByText("E2E Fixture Site")).toBeVisible({ timeout: 15000 });

    // Get site id via API sync — extract from dashboard link
    const detailsLink = page.getByRole("link", { name: "Details" }).first();
    await expect(detailsLink).toBeVisible();
    const href = await detailsLink.getAttribute("href");
    const siteId = href?.split("/").pop();
    expect(siteId).toBeTruthy();

    // 3. Fail verification (wrong token)
    await page.getByRole("button", { name: "Verify ownership" }).click();
    await page.waitForTimeout(2000);
    // Still unverified — shield should remain
    await expect(page.locator('[aria-label="Unverified"]').first()).toBeVisible();

    // 4. Pass verification — fetch real token from API using page session
    const tokenResp = await page.evaluate(async ({ api, sid }) => {
      const sync = await fetch(`${api}/auth/sync`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: "e2e-test@agentworthy.example", name: "E2E" }),
      });
      const { access_token } = await sync.json();
      const instr = await fetch(`${api}/sites/${sid}/verification-instructions`, {
        headers: { Authorization: `Bearer ${access_token}` },
      });
      return instr.json();
    }, { api: API, sid: siteId });
    const match = tokenResp.meta_tag?.match(/content="([^"]+)"/);
    const realToken = match?.[1];
    expect(realToken).toBeTruthy();
    fs.writeFileSync(FIXTURE_TOKEN_FILE, realToken);

    await page.getByRole("button", { name: "Verify ownership" }).click();
    await page.waitForTimeout(3000);
    await expect(page.locator('[aria-label="Verified"]').first()).toBeVisible({ timeout: 15000 });

    // 5. Trigger scan
    await page.getByRole("button", { name: "Scan now" }).click();
    await page.waitForURL(/\/scans\//, { timeout: 15000 });

    // 6. Wait for score on scan report page (ScoreGauge uses text-4xl)
    await expect(page.locator(".font-mono.text-4xl")).not.toHaveText("0", { timeout: 180000 });
    const scoreText = await page.locator(".font-mono.text-4xl").first().textContent();
    expect(Number(scoreText)).toBeGreaterThan(0);

    // Return to dashboard and verify score visible
    await page.goto("/dashboard");
    await expect(page.getByText(scoreText!)).toBeVisible({ timeout: 15000 });

    // Save dashboard HTML and screenshot for gate proof
    const html = await page.content();
    fs.writeFileSync("/workspace/gate2-dashboard.html", html);
    fs.mkdirSync("/workspace/docs/proof", { recursive: true });
    await page.screenshot({ path: "/workspace/docs/proof/gate2-dashboard.png", fullPage: true });
  });
});
