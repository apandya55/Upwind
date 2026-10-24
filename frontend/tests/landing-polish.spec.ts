import { expect, test } from "@playwright/test";

const viewports = [
  { name: "desktop", width: 1440, height: 900 },
  { name: "tablet", width: 768, height: 1024 },
  { name: "mobile", width: 390, height: 844 },
];

test("guided atlas landing, evidence coverage, routes, and responsive layouts", async ({ page }, testInfo) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("console", (message) => { if (message.type() === "error") errors.push(message.text()); });
  for (const viewport of viewports) {
    await page.setViewportSize(viewport);
    await page.goto("/landing");
    await expect(page.getByRole("heading", { name: "Explore America’s air quality, place by place." })).toBeVisible();
    await expect(page.getByRole("link", { name: /Open the atlas/ }).first()).toHaveAttribute("href", "/explore");
    await expect(page.getByRole("link", { name: "Read the method" })).toHaveAttribute("href", "/methodology");
    await expect(page.getByRole("heading", { name: "See what each record tells you." })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Modeled estimates" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Monitor measurements" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Emissions inventory" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Place-based comparison" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Evidence with a defined scope." })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Searchable places" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Supported estimates" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Monitor sites" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Evidence layers" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Start with a place." })).toBeVisible();
    await expect(page.locator("a[href='/workspace']")).toHaveCount(0);
    const preview = page.locator(".preview-frame img");
    await expect(preview).toBeVisible();
    expect(await preview.evaluate((node: HTMLImageElement) => node.naturalWidth)).toBeGreaterThan(100);
    await page.locator('[data-story-step="2"]').scrollIntoViewIfNeeded();
    await expect(page.locator(".story-image-label")).toContainText("Emissions inventory");
    expect(await page.locator(".story-visual img").evaluate((node: HTMLImageElement) => node.naturalWidth)).toBeGreaterThan(100);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await page.screenshot({ path: testInfo.outputPath(`landing-${viewport.name}.png`), fullPage: true });
  }
  expect(errors).toEqual([]);
});

test("primary navigation reaches methodology and the Explorer", async ({ page }) => {
  await page.goto("/landing");
  await page.getByRole("link", { name: "Read the method" }).click();
  await expect(page).toHaveURL(/\/methodology$/);
  await expect(page.getByRole("heading", { name: "Method, evidence, and limits." })).toBeVisible();
  await page.goto("/landing");
  await expect(page.getByRole("link", { name: /Open the atlas/ }).first()).toHaveAttribute("href", "/explore");
});

test("scroll storytelling selects four distinct, current Explorer map states", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/landing");
  const expected = ["Modeled estimates", "Monitor measurements", "Emissions inventory", "Place-based comparison"];
  for (const [index, title] of expected.entries()) {
    const step = page.locator(`[data-story-step="${index}"]`);
    await step.evaluate((node) => { const rect = node.getBoundingClientRect(); window.scrollTo({ top: rect.top + window.scrollY + rect.height / 2 - window.innerHeight * 0.55, behavior: "instant" }); });
    await expect(page.locator(".story-image-label")).toContainText(title);
    const image = page.locator(".story-visual img");
    await expect(image).toHaveAttribute("src", new RegExp(["place", "monitors", "sources", "overview"][index]));
    await expect(image).toHaveJSProperty("complete", true);
    expect(await image.evaluate((node: HTMLImageElement) => node.naturalWidth)).toBeGreaterThanOrEqual(1400);
  }
  await page.setViewportSize({ width: 390, height: 844 });
  expect(await page.locator(".story-visual").evaluate((node) => getComputedStyle(node).position)).not.toBe("sticky");
});
