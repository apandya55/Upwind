import { test, expect } from "@playwright/test";
import { readFile, mkdir } from "node:fs/promises";

test("complete example: plan, constraints, save, reopen, export and responsive layout", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("/workspace");
  await expect(
    page.getByRole("heading", { name: "Estuary monitoring study" }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Generate measurement plans" })
    .click();
  await expect(
    page.getByText("Experimental information · exhaustive", { exact: true }),
  ).toBeVisible();
  const first = await page.locator(".plan-option.chosen").innerText();
  await page.getByLabel("Budget (cost units)").fill("120");
  await expect(page.locator(".plan-option")).toHaveCount(0);
  await page
    .getByRole("button", { name: "Generate measurement plans" })
    .click();
  await expect(
    page.getByText("Experimental information · exhaustive", { exact: true }),
  ).toBeVisible();
  expect(await page.locator(".plan-option.chosen").innerText()).not.toEqual(
    first,
  );
  await page
    .getByRole("button", { name: "Save investigation", exact: true })
    .click();
  await expect(page.getByText("Saved locally", { exact: true })).toBeVisible();
  await page
    .getByRole("button", { name: "Export evidence", exact: true })
    .click();
  const downloadPromise = page.waitForEvent("download");
  await page
    .getByRole("button", { name: /Evidence report Self-contained/ })
    .click();
  const download = await downloadPromise;
  const report = await readFile((await download.path())!, "utf8");
  expect(report).toContain("SYNTHETIC DEMONSTRATION");
  expect(report).toContain("Experimental conditional scenario weights");
  await page.getByRole("button", { name: "Close dialog" }).click();
  await page.reload();
  await page.locator(".investigation-switch").click();
  await page
    .locator(".library-row")
    .filter({ hasText: "Estuary monitoring study" })
    .first()
    .click();
  await expect(page.getByLabel("Budget (cost units)")).toHaveValue("120");
  await page.getByLabel("Budget (cost units)").fill("350");
  await page
    .getByRole("button", { name: "Generate measurement plans" })
    .click();
  await expect(page.locator(".plan-option")).toHaveCount(4);
  await mkdir("../.local/screenshots", { recursive: true });
  for (const width of [1440, 1280, 390]) {
    await page.setViewportSize({ width, height: width === 390 ? 844 : 1000 });
    await page.screenshot({
      path: `../.local/screenshots/workspace-${width}.png`,
      fullPage: true,
    });
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth,
      ),
    ).toBeTruthy();
  }
  expect(errors).toEqual([]);
});

test("new investigation, valid and malformed imports, follow-up, observations and restore", async ({
  page,
}) => {
  await page.goto("/workspace");
  await page.locator(".investigation-switch").click();
  await page
    .getByRole("button", { name: "New investigation", exact: true })
    .last()
    .click();
  await page.getByLabel("Investigation name").fill("Browser import exercise");
  await page
    .getByLabel("Concern", { exact: true })
    .fill("Explore a measured episode without assigning responsibility.");
  await page
    .getByRole("button", { name: "Apply investigation settings" })
    .click();
  await page.getByRole("button", { name: "Import data", exact: true }).click();
  await page.getByLabel("CSV file").setInputFiles({
    name: "measurements.csv",
    mimeType: "text/csv",
    buffer: Buffer.from(
      "sensor_id,timestamp,latitude,longitude,pm25_ug_m3\nA,2025-06-12T10:00Z,0,0,12\nA,2025-06-12T10:05Z,0,0,14\nB,2025-06-12T10:00Z,0.001,0.001,15\nB,bad,0.001,0.001,20\n",
    ),
  });
  await page.getByRole("button", { name: "Validate & append CSV" }).click();
  await expect(
    page.getByText("3 accepted · 1 invalid · 0 flagged", { exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Inspect imported data" }).click();
  await expect(page.locator(".quality-list")).toContainText("measurements.csv");
  await page.getByRole("button", { name: "Timeline", exact: true }).click();
  await page.getByLabel("Timeline time").fill("1");
  await expect(page.getByText("10:05 UTC", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Import data", exact: true }).click();
  await page.getByLabel("CSV file").setInputFiles({
    name: "bad.csv",
    mimeType: "text/csv",
    buffer: Buffer.from("wrong,columns\n1,2\n"),
  });
  await page.getByRole("button", { name: "Validate & append CSV" }).click();
  await expect(page.getByRole("alert")).toContainText(
    "Missing required columns",
  );
  await page.getByLabel("CSV file").setInputFiles({
    name: "follow-up.csv",
    mimeType: "text/csv",
    buffer: Buffer.from(
      "sensor_id,timestamp,latitude,longitude,pm25_ug_m3\nA,2025-06-12T10:10,0,0,16\n",
    ),
  });
  await page.getByLabel("Timezone for naive timestamps").fill("UTC");
  await page.getByRole("button", { name: "Validate & append CSV" }).click();
  await expect(
    page.getByText("1 accepted · 0 invalid · 0 flagged", { exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Inspect imported data" }).click();
  await page
    .getByRole("button", { name: "Save investigation", exact: true })
    .click();
  await expect(page.getByText("Saved locally", { exact: true })).toBeVisible();
  await page
    .getByRole("button", { name: "Export evidence", exact: true })
    .click();
  const pending = page.waitForEvent("download");
  await page
    .getByRole("button", { name: /Private investigation archive/ })
    .click();
  const file = await pending,
    raw = await readFile((await file.path())!);
  const inv = JSON.parse(raw.toString());
  expect(inv.measurements).toHaveLength(4);
  expect(inv.imports).toHaveLength(2);
  await page.getByRole("button", { name: "Close dialog" }).click();
  await page.locator(".investigation-switch").click();
  await page.locator("input[type=file]").setInputFiles({
    name: "restore.json",
    mimeType: "application/json",
    buffer: raw,
  });
  await expect(
    page.getByRole("heading", { name: "Browser import exercise" }),
  ).toBeVisible();
  await expect(page.getByText("Saved locally", { exact: true })).toBeVisible();
});

test("offline operation, labelled synthetic CSV reimport, keyboard observation and report", async ({
  page,
}) => {
  await page.route("**/*", async (route) => {
    if (!route.request().url().startsWith("http://127.0.0.1:5174"))
      await route.abort();
    else await route.continue();
  });
  await page.goto("/workspace");
  await page
    .getByRole("button", { name: "Generate measurement plans" })
    .click();
  await expect(
    page.getByText("Plan comparison", { exact: true }),
  ).toBeVisible();
  await page.getByLabel("Add to map").selectOption("observation");
  await page.locator(".map-canvas>svg").press("Enter");
  await page
    .getByLabel("Observation notes")
    .fill("Synthetic resident account, distinct from sensor evidence.");
  await page
    .getByLabel("Observation time (local timezone)")
    .fill("2025-06-12T10:15");
  await page
    .getByRole("button", { name: "Add observation", exact: true })
    .click();
  await page.getByRole("button", { name: "Observations", exact: true }).click();
  await expect(page.locator(".quality-list")).toContainText(
    "Synthetic resident account",
  );
  await page
    .getByRole("button", { name: "Save investigation", exact: true })
    .click();
  await expect(page.getByText("Saved locally", { exact: true })).toBeVisible();
  await page.locator(".investigation-switch").click();
  await page
    .getByRole("button", { name: "New investigation", exact: true })
    .last()
    .click();
  await page
    .getByRole("button", { name: "Apply investigation settings" })
    .click();
  await page.getByRole("button", { name: "Import data", exact: true }).click();
  await page
    .getByLabel("CSV file")
    .setInputFiles("../examples/synthetic-measurements.csv");
  await page.getByRole("button", { name: "Validate & append CSV" }).click();
  await expect(
    page.getByText("21 accepted · 0 invalid · 0 flagged", { exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Inspect imported data" }).click();
  await expect(page.locator(".status-strip")).toContainText(
    "Synthetic example",
  );
  await page
    .getByRole("button", { name: "Export evidence", exact: true })
    .click();
  const promise = page.waitForEvent("download");
  await page
    .getByRole("button", { name: /Evidence report Self-contained/ })
    .click();
  const download = await promise;
  const report = await readFile((await download.path())!, "utf8");
  expect(report).toContain("SYNTHETIC DEMONSTRATION");
  expect(report).toContain("synthetic-measurements.csv");
  expect(report).toContain("SHA256");
});

test("candidate permissions, unsupported weather and map interaction", async ({
  page,
}) => {
  await page.goto("/workspace");
  await page
    .getByRole("button", { name: "Select Footbridge", exact: true })
    .locator("circle")
    .last()
    .click();
  await expect(page.getByLabel("Site name")).toHaveValue("Footbridge");
  await page.getByLabel("Permission confirmed", { exact: true }).uncheck();
  await page.getByRole("button", { name: "Plan", exact: true }).click();
  await page
    .getByRole("button", { name: "Generate measurement plans" })
    .click();
  await expect(page.locator(".plan-option")).toHaveCount(4);
  expect(await page.locator(".plan-option.chosen").innerText()).not.toContain(
    "C1",
  );
  await page.getByRole("button", { name: "Scenarios", exact: true }).click();
  await page.getByLabel("Representative local measured weather").uncheck();
  await page.getByRole("button", { name: "Plan", exact: true }).click();
  await page
    .getByRole("button", { name: "Generate measurement plans" })
    .click();
  await expect(page.getByText("Action needed", { exact: true })).toBeVisible();
  await expect(page.locator(".inline-warning")).toContainText(
    "Confirm steady conditions",
  );
  await page.getByLabel("Planning objective").selectOption("spatial_coverage");
  await page
    .getByRole("button", { name: "Generate measurement plans" })
    .click();
  await expect(
    page.getByText("Plan comparison", { exact: true }),
  ).toBeVisible();
  await page.getByLabel("Map layers").click();
  await page.getByLabel("sources", { exact: true }).uncheck();
  await expect(page.locator(".source-label")).toHaveCount(0);
  await page.getByLabel("Map layers").click();
  await page.getByLabel("Add to map").selectOption("candidate");
  const map = page.locator(".map-canvas>svg");
  const box = (await map.boundingBox())!;
  await map.click({ position: { x: box.width * 0.5, y: box.height * 0.5 } });
  await page
    .getByLabel("Site name", { exact: true })
    .last()
    .fill("Accessible candidate");
  await page.getByLabel("Permission confirmed", { exact: true }).last().check();
  await page
    .getByLabel("Power or battery confirmed", { exact: true })
    .last()
    .check();
  await page
    .getByLabel("Safe access confirmed", { exact: true })
    .last()
    .check();
  await page
    .getByLabel("Available in the observed steady window", { exact: true })
    .last()
    .check();
  await page
    .getByRole("button", { name: "Add candidate", exact: true })
    .click();
  await expect(
    page.getByRole("button", {
      name: "Select Accessible candidate",
      exact: true,
    }),
  ).toBeVisible();
});
