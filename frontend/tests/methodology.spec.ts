import { expect, test } from "@playwright/test";

for (const viewport of [
  { name: "desktop", width: 1440, height: 900 },
  { name: "tablet", width: 768, height: 1024 },
  { name: "mobile", width: 390, height: 844 },
]) {
  test(`methodology shows current release facts and fits ${viewport.name}`, async ({ page }, testInfo) => {
    await page.setViewportSize(viewport);
    const errors: string[] = [];
    page.on("pageerror", (error) => errors.push(error.message));
    page.on("console", (message) => { if (message.type() === "error") errors.push(message.text()); });
    await page.goto("/methodology");
    await expect(page.getByRole("heading", { name: "Method, evidence, and limits." })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Nearest-monitor annual PM2.5" })).toBeVisible();
    await expect(page.getByText("32,333", { exact: true })).toBeVisible();
    await expect(page.getByText("31,523", { exact: true })).toBeVisible();
    await expect(page.getByText("894", { exact: true })).toBeVisible();
    await expect(page.getByRole("heading", { name: "From annual monitor summaries to a place point." })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Each layer answers a different question." })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Why nearest monitor remains in the release." })).toBeVisible();
    await expect(page.getByText(/±4\.123 µg\/m³ band/)).toBeVisible();
    await expect(page.getByRole("link", { name: "Open atlas" })).toHaveAttribute("href", "/explore");
    await expect(page.getByRole("table")).toBeVisible();
    await expect(page.getByText(/45 km|10-Fold Spatial Cluster CV|23\.7% reduction|1\.12 µg\/m³/)).toHaveCount(0);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await page.screenshot({ path: testInfo.outputPath(`methodology-${viewport.name}.png`), fullPage: true });
    expect(errors).toEqual([]);
  });
}
