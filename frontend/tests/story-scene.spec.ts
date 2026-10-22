import { expect, test, type Page } from "@playwright/test";

async function mountStory(page: Page) {
  await page.goto("/");
  await page.evaluate(async () => {
    document.body.replaceChildren();
    const host = document.createElement("div");
    host.id = "story-test-root";
    document.body.append(host);
    const [{ default: React }, client, { default: StoryScene }] = await Promise.all([
      import("/node_modules/.vite/deps/react.js"), import("/node_modules/.vite/deps/react-dom_client.js"), import("/src/StoryScene.tsx"),
    ]);
    client.default.createRoot(host).render(React.createElement(StoryScene));
  });
  await expect(page.locator("#story")).toBeAttached();
}

test("desktop scene maps native scroll progress through its endpoints", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await mountStory(page);
  const scene = page.locator("#story");
  await expect.poll(() => scene.evaluate((node) => node.style.getPropertyValue("--story-progress"))).toBe("0");
  await page.evaluate(() => window.scrollTo(0, document.querySelector("#story")!.getBoundingClientRect().top + window.scrollY));
  const bounds = await scene.boundingBox();
  const height = await scene.evaluate((node) => node.getBoundingClientRect().height);
  const top = bounds!.y + await page.evaluate(() => scrollY);
  for (const progress of [0.6, 0.2, 0.9, 1]) {
    await page.evaluate(({ top, sceneHeight, progress }) => window.scrollTo(0, top + progress * (sceneHeight - innerHeight)), { top, sceneHeight: height, progress });
    await expect.poll(async () => Number(await scene.evaluate((node) => node.style.getPropertyValue("--story-progress")))).toBeGreaterThan(progress - 0.03);
    await expect.poll(async () => Number(await scene.evaluate((node) => node.style.getPropertyValue("--story-progress")))).toBeLessThan(progress + 0.03);
  }
  await expect(scene.locator(".evidence-image img")).toBeVisible();
});

test("mobile and reduced motion render the whole story as a static progression", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await mountStory(page);
  const scene = page.locator("#story");
  await expect(scene.locator(".continuous-story__art")).toBeVisible();
  await expect(scene.locator(".continuous-story__evidence")).toBeVisible();
  await expect.poll(() => scene.evaluate((node) => node.style.getPropertyValue("--evidence"))).toBe("1");
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.setViewportSize({ width: 1200, height: 900 });
  await expect.poll(() => scene.evaluate((node) => node.style.getPropertyValue("--evidence"))).toBe("1");
  await expect(scene.locator(".continuous-story__art")).toBeVisible();
});

test("evidence action is accessible and the scene never creates horizontal overflow", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await mountStory(page);
  await expect(page.getByRole("link", { name: "Explore the map" })).toHaveAttribute("href", "/explore");
  await expect(page.getByRole("heading", { name: "Explore what is measured. Inspect what is nearby." })).toBeAttached();
  const widths = await page.evaluate(() => ({ viewport: document.documentElement.clientWidth, document: document.documentElement.scrollWidth }));
  expect(widths.document).toBeLessThanOrEqual(widths.viewport);
});
