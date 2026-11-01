import { expect, test } from "@playwright/test";

test("local page explains and provides the local CSV workflow", async ({ page }, testInfo) => {
  await page.goto("/local");
  await expect(page.getByRole("heading", { name: "Bring local readings into view." })).toBeVisible();
  await expect(page.getByText("Files are sent only to the local UPWIND API.")).toBeVisible();
  await expect(page.getByText("sensor_id · timestamp · latitude · longitude · pm25_ug_m3")).toBeVisible();
  await page.screenshot({ path: testInfo.outputPath("local-desktop.png"), fullPage: true });

  const templateDownload = page.waitForEvent("download");
  await page.getByRole("link", { name: "CSV template" }).click();
  const template = await templateDownload;
  expect(template.suggestedFilename()).toBe("sensor-template.csv");

  const exampleDownload = page.waitForEvent("download");
  await page.getByRole("link", { name: "Download synthetic CSV" }).click();
  const example = await exampleDownload;
  expect(example.suggestedFilename()).toBe("synthetic-measurements.csv");

  await page.getByRole("link", { name: /Open local workspace/ }).click();
  await expect(page).toHaveURL(/\/workspace$/);
});


