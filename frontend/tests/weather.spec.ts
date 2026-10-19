import { test, expect } from "@playwright/test";

test("paired weather CSV retains independent readings, raw metadata and legacy archives", async ({
  page,
  request,
}) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Import data", exact: true }).click();
  await page.getByLabel("Table type").selectOption("weather");
  const csv =
    "timestamp,latitude,longitude,wind_speed_m_s,wind_from_deg,role,source_id,upstream_id,direction_systematic_sd_deg,speed_systematic_fraction,direction_random_sd_deg,comparison_provenance\n2025-06-12T10:00Z,0,0,2.5,270,primary,A,instrument-A,,,,\n2025-06-12T10:00Z,0,0,2.4,245,reference,B,instrument-B,2,.03,1,independent paired instrument\n";
  await page.getByLabel("CSV file").setInputFiles({
    name: "paired-weather.csv",
    mimeType: "text/csv",
    buffer: Buffer.from(csv),
  });
  await expect(
    page.getByText(/Independent reference readings require distinct/),
  ).toBeVisible();
  await page.getByRole("button", { name: "Validate & append CSV" }).click();
  await expect(
    page.getByText("2 accepted · 0 invalid · 0 flagged", { exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Inspect imported data" }).click();
  await page
    .getByRole("button", { name: "Save investigation", exact: true })
    .click();
  const records = await (
    await request.get("http://127.0.0.1:8001/api/investigations")
  ).json();
  const saved = await (
    await request.get(
      `http://127.0.0.1:8001/api/investigations/${records[0].id}`,
    )
  ).json();
  expect(
    saved.weather.filter((w: { role: string }) => w.role === "reference"),
  ).toHaveLength(1);
  expect(saved.imports.at(-1).raw_csv).toBe(csv);
  const legacy = {
    model_version: "plume-campaign-0.4.0",
    input_hash: "0".repeat(64),
    status: "ok",
    plans: [],
    source_probability: 1,
  };
  saved.result = legacy;
  await page.locator(".investigation-switch").click();
  await page.getByLabel("Restore investigation JSON").setInputFiles({
    name: "legacy.json",
    mimeType: "application/json",
    buffer: Buffer.from(JSON.stringify(saved)),
  });
  await expect(
    page.getByText(/Previous analysis archived: joint common-mode weather/),
  ).toBeVisible();
  await expect(
    page.getByText(/1 previous model results retained/),
  ).toBeVisible();
});
