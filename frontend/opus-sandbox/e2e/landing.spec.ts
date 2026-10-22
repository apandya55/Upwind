import { expect, test } from "@playwright/test";

test("landing presents a clear mission, real routes, and a reversible scroll sequence", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/");
  await expect(page.getByRole("heading", { name: /Air evidence.*within reach/ })).toBeVisible();
  await expect(page.getByRole("link", { name: /Explore the map/ })).toHaveAttribute("href", "/explore");
  await expect(page.getByRole("link", { name: /Bring local sensor data/ })).toHaveAttribute("href", "/local");
  await expect(page.locator(".hero-figure img")).toBeVisible();
  await page.waitForTimeout(900);
  await page.screenshot({ path: "screenshots/desktop-hero-1440x900.png" });

  const story = page.locator(".story");
  const top = await story.evaluate((node) => node.getBoundingClientRect().top + scrollY);
  const height = await story.evaluate((node) => node.getBoundingClientRect().height);
  for (const progress of [0, 0.5, 1]) {
    await page.evaluate(({ top, height, progress }) => scrollTo(0, top + progress * (height - innerHeight)), { top, height, progress });
    await expect.poll(() => story.evaluate((node) => Number.parseFloat(getComputedStyle(node).getPropertyValue("--story-progress")))).toBeGreaterThan(progress - 0.04);
    await expect.poll(() => story.evaluate((node) => Number.parseFloat(getComputedStyle(node).getPropertyValue("--story-progress")))).toBeLessThan(progress + 0.04);
    await page.waitForTimeout(450);
    await page.screenshot({ path: `screenshots/scroll-sequence-${progress}.png` });
    if (progress === 0.5) await expect.poll(() => story.evaluate((node) => Number.parseFloat(getComputedStyle(node).getPropertyValue("--chapter-2")))).toBeGreaterThan(0.95);
  }
  await page.evaluate(({ top, height }) => scrollTo(0, top + height - innerHeight), { top, height });
  await page.evaluate(({ top }) => scrollTo(0, top), { top });
  await expect.poll(() => story.evaluate((node) => Number.parseFloat(getComputedStyle(node).getPropertyValue("--chapter-1")))).toBeGreaterThan(0.95);
});

test("mobile and reduced-motion modes show all chapters without overflow", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await expect(page.locator(".chapter")).toHaveCount(3);
  for (const chapter of await page.locator(".chapter").all()) await expect(chapter).toBeVisible();
  await page.screenshot({ path: "screenshots/mobile-390x844.png", fullPage: true });

  await page.setViewportSize({ width: 1440, height: 900 });
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/");
  await page.screenshot({ path: "screenshots/reduced-motion.png", fullPage: true });
  await page.locator(".story").scrollIntoViewIfNeeded();
  for (const chapter of await page.locator(".chapter").all()) await expect(chapter).toBeVisible();
  await expect(page.locator(".story-sticky")).toHaveCSS("position", "relative");
});

test("layout stays composed at laptop and tablet sizes", async ({ page }) => {
  for (const viewport of [
    { width: 1280, height: 800, name: "desktop-compact-1280x800" },
    { width: 768, height: 1024, name: "tablet-768x1024" },
  ]) {
    await page.setViewportSize({ width: viewport.width, height: viewport.height });
    await page.goto("/");
    await expect(page.getByRole("heading", { name: /Air evidence.*within reach/ })).toBeVisible();
    await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await page.waitForTimeout(900);
    await page.screenshot({ path: `screenshots/${viewport.name}.png` });
    await page.evaluate(() => scrollTo(0, document.body.scrollHeight));
    await expect(page.getByRole("link", { name: /Open the Explorer/ })).toBeVisible();
  }
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/");
  await page.waitForTimeout(900);
  await page.screenshot({ path: "screenshots/full-page-desktop.png", fullPage: true });
});
