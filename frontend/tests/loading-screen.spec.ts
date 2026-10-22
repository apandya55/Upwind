import { expect, test } from "@playwright/test";

test("simple calm loading screen displays bouncing logo, wind breeze lines, and status", async ({ page }) => {
  // Delay manifest to inspect loading animation
  let routeFulfill: () => void = () => {};
  const manifestHold = new Promise<void>((resolve) => {
    routeFulfill = resolve;
  });

  await page.route("**/api/national/manifest", async (route) => {
    await manifestHold;
    await route.continue();
  });

  await page.goto("/explore");

  const loader = page.locator(".national-loading-screen");
  await expect(loader).toBeVisible();
  await expect(loader.locator(".bouncing-logo")).toBeVisible();
  await expect(loader.locator(".breeze-lines")).toBeVisible();
  await expect(loader.getByText("UPWIND", { exact: true })).toBeVisible();
  await expect(loader.locator(".bouncing-status")).toBeVisible();

  // Release manifest and verify smooth transition to main interface
  routeFulfill();
  await expect(page.getByText("searchable Census places")).toBeVisible();
  await expect(loader).not.toBeVisible();
});

test("bouncing loading screen is responsive on mobile viewport without horizontal overflow", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/explore");

  // Verify no horizontal overflow
  const isWithinBounds = await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth);
  expect(isWithinBounds).toBe(true);

  // Wait for load to complete cleanly
  await expect(page.getByText("searchable Census places")).toBeVisible();
});
