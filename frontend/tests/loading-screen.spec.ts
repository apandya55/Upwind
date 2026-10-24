import { expect, test } from "@playwright/test";

test("minimalistic animated loading screen displays squircle wind gust animation and transitions smoothly", async ({ page }) => {
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
  await expect(loader).toBeVisible({ timeout: 10000 });
  await expect(loader).toHaveId("upwind-loading-screen");
  await expect(loader.locator(".national-loading-svg")).toBeVisible({ timeout: 5000 });
  await expect(loader.locator(".stream-top")).toBeAttached({ timeout: 5000 });
  await expect(loader.locator(".stream-mid")).toBeAttached({ timeout: 5000 });
  await expect(loader.locator(".stream-bot")).toBeAttached({ timeout: 5000 });

  // Release manifest and verify smooth transition to main interface
  routeFulfill();
  await expect(page.getByText("searchable Census places")).toBeVisible({ timeout: 15000 });
  await expect(loader).not.toBeVisible({ timeout: 10000 });
});

test("minimalistic loading screen is responsive on mobile viewport without horizontal overflow", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/explore");

  // Verify no horizontal overflow
  const isWithinBounds = await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth);
  expect(isWithinBounds).toBe(true);

  // Wait for load to complete cleanly
  await expect(page.getByText("searchable Census places")).toBeVisible({ timeout: 15000 });
});
