import { expect, test } from "@playwright/test";

for (const viewport of [
  { width: 390, height: 844 },
  { width: 768, height: 1024 },
  { width: 1280, height: 720 },
  { width: 1440, height: 900 },
]) {
  test(`local page spans both viewport edges at ${viewport.width}px`, async ({ page }, testInfo) => {
    await page.setViewportSize(viewport);
    await page.goto("/local");
    await expect(page.locator(".local-hero h1")).toBeVisible();

    const geometry = await page.evaluate(() => {
      const bounds = (selector: string) => {
        const element = document.querySelector<HTMLElement>(selector)!;
        const { left, right, width } = element.getBoundingClientRect();
        return { left, right, width };
      };
      return {
        width: innerWidth,
        scrollWidth: document.documentElement.scrollWidth,
        header: bounds(".app-navbar"),
        footer: bounds(".app-footer"),
        headerContent: bounds(".app-navbar-inner"),
        footerContent: bounds(".app-footer-inner"),
      };
    });

    for (const edge of [geometry.header, geometry.footer]) {
      expect(edge.left).toBeCloseTo(0, 1);
      expect(edge.right).toBeCloseTo(geometry.width, 1);
    }
    expect(geometry.scrollWidth).toBeLessThanOrEqual(geometry.width);
    expect(geometry.headerContent.left).toBeCloseTo(geometry.footerContent.left, 1);
    expect(geometry.headerContent.right).toBeCloseTo(geometry.footerContent.right, 1);

    const trigger = page.getByRole("button", { name: "Open menu" });
    await trigger.click();
    const drawer = page.getByRole("dialog", { name: "Main navigation menu" });
    await expect(drawer).toBeVisible();
    await expect(drawer.locator(".national-menu-item.active")).toHaveAttribute("href", "/local");
    await page.getByRole("button", { name: "Close menu" }).click();
    await expect(drawer).toHaveCount(0);
    await expect(trigger).toBeFocused();

    await page.locator(".app-footer").scrollIntoViewIfNeeded();
    await expect(page.locator(".app-footer").getByRole("link", { name: "National Explorer" })).toBeVisible();
    await page.screenshot({ path: testInfo.outputPath("local-page.png"), fullPage: true });
  });
}
