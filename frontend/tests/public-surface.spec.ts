import { expect, test } from "@playwright/test";
import { env } from "node:process";

test("public local setup page describes the engine without presenting a remote upload workflow", async ({ page }) => {
  await page.goto("/local");
  await expect(page.getByRole("heading", { name: "Run the engine on your own computer." })).toBeVisible();
  await expect(page.getByText("This public Explorer does not accept uploads.")).toBeVisible();
  await expect(page.getByText("Required columns", { exact: true })).toHaveCount(0);
  await expect(page.getByText("Files are sent only to the local UPWIND API.")).toHaveCount(0);
});

test("public workspace route cannot load local investigation data or controls", async ({ page }) => {
  await page.goto("/workspace");
  await expect(page.getByRole("heading", { name: "The investigation workspace runs locally." })).toBeVisible();
  await expect(page.getByRole("button", { name: /Create investigation|Import data/ })).toHaveCount(0);
  await expect(page.getByText("Saved locally", { exact: true })).toHaveCount(0);
});

test("Vercel build sends National API reads to the configured API origin", async ({ page }) => {
  const apiOrigin = env.EXPECTED_PUBLIC_API_ORIGIN;
  test.skip(!apiOrigin, "Vercel API origin is supplied only by the Vercel build check");
  await page.route(`${apiOrigin}/api/**`, (route) => route.fulfill({ status: 503, contentType: "application/json", body: "{}" }));
  const request = page.waitForRequest((entry) => entry.url() === `${apiOrigin}/api/national/manifest`);
  await page.goto("/");
  const apiRequest = await request;
  expect(apiRequest.method()).toBe("GET");
});
