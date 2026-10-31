import { expect, test } from "@playwright/test";

for (const viewport of [
  { name: "desktop", width: 1440, height: 900 },
  { name: "tablet", width: 768, height: 1024 },
  { name: "mobile", width: 390, height: 844 },
]) {
  test(`about page renders civic mission and fits ${viewport.name}`, async ({ page }, testInfo) => {
    await page.setViewportSize(viewport);
    const errors: string[] = [];
    page.on("pageerror", (error) => errors.push(error.message));
    page.on("console", (message) => {
      if (message.type() === "error") errors.push(message.text());
    });

    await page.goto("/about");
    await expect(page.getByRole("heading", { name: "A public atlas for exploring historical air-quality evidence." })).toBeVisible();
    await expect(page.getByText("76,404", { exact: true })).toBeVisible();
    await expect(page.getByText("32,333", { exact: true })).toBeVisible();
    await expect(page.getByText("894", { exact: true })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Three records, three different things." })).toBeVisible();
    await expect(page.getByRole("heading", { name: "What this release cannot tell you." })).toBeVisible();
    await expect(page.getByRole("link", { name: "GitHub repository" })).toHaveAttribute("href", "https://github.com/apandya55/Upwind");
    await expect(page.getByRole("link", { name: "Developer portfolio" }).first()).toHaveAttribute("href", "https://arnavpandya.com");

    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await page.screenshot({ path: testInfo.outputPath(`about-${viewport.name}.png`), fullPage: true });
    expect(errors).toEqual([]);
  });
}
