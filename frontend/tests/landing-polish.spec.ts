import { expect, test } from "@playwright/test";

test("atlas landing tells one sourced Durham story at desktop and mobile widths", async ({ page }) => {
  for (const viewport of [{ width: 1440, height: 900 }, { width: 1280, height: 800 }, { width: 768, height: 1024 }, { width: 390, height: 844 }]) {
    await page.setViewportSize(viewport);
    await page.goto("/");
    await expect(page.getByRole("heading", { name: /Explore your community’s air record/ })).toBeVisible();
    await expect(page.getByRole("link", { name: "Explore the map" }).first()).toHaveAttribute("href", "/explore");
    await expect(page.locator(".hero-product img")).toBeVisible();
    await expect(page.getByRole("heading", { name: /One point\. Several kinds of evidence\./ })).toBeVisible();
    await expect(page.locator(".estimate-row")).toContainText("9.71");
    await expect(page.locator(".monitor-row")).toContainText("37-063-0015");
    await expect(page.locator(".source-row")).toContainText("103.50");
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    const hero = await page.locator(".landing-hero").boundingBox();
    const story = await page.locator(".durham-story").boundingBox();
    expect(hero && story && story.y >= hero.y + hero.height - 1).toBe(true);
  }
});

test("arrow draws once toward the primary CTA and reduced motion keeps it visible", async ({ page }) => {
  await page.goto("/");
  const path = page.locator(".cta-annotation-path");
  await expect(path).toBeVisible();
  expect(await path.evaluate((node) => getComputedStyle(node).animationName)).toBe("arrow-draw");
  await page.emulateMedia({ reducedMotion: "reduce" });
  expect(await path.evaluate((node) => getComputedStyle(node).strokeDashoffset)).toBe("0px");
  await expect(page.getByRole("link", { name: /Explore the map/ }).first()).toBeEnabled();
});

test("coverage is sourced and the full release accounting is progressively disclosed", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByText("31,523", { exact: true })).toBeVisible();
  await expect(page.getByText("894", { exact: true })).toBeVisible();
  const accounting = page.getByText("Open the full coverage accounting");
  await accounting.click();
  await expect(page.locator(".coverage-detail-content")).toContainText("32,333");
  await expect(page.locator(".coverage-detail-content")).toContainText("76,404");
});
