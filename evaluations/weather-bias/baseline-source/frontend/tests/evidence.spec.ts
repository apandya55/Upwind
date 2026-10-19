import { test, expect } from "@playwright/test";

test("coverage planning renders when reconstruction fields are explicitly unavailable", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.route("**/api/analyze", (route) =>
    route.fulfill({
      json: {
        status: "ok",
        warnings: [],
        plans: [],
        sources: [],
        model_version: "presentation-contract-fixture",
        input_hash: "0".repeat(64),
        source_probability: null,
        source_region90: null,
        diagnostics: null,
        evidence_status: "ambiguous",
        fitted_rmse_ug_m3: null,
        ties: null,
      },
    }),
  );
  await page.goto("/");
  await page
    .getByRole("button", { name: "Generate measurement plans", exact: true })
    .click();
  await expect(
    page.getByText("Plan comparison", { exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Scenarios", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Compare explanations, not blame." }),
  ).toBeVisible();
  expect(errors).toEqual([]);
});

test("conditional evidence is distinct from field confidence and incomplete diagnostics stay usable", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  // A presentation-only response verifies rendering, not scientific performance.
  await page.route("**/api/analyze", (route) =>
    route.fulfill({
      json: {
        status: "ok",
        warnings: [],
        model_version: "presentation-contract-fixture",
        input_hash: "0".repeat(64),
        sources: [{ id: "S1", latitude: 0, longitude: 0, weight: 1 }],
        plans: [
          {
            method: "Contract plan",
            site_ids: ["C1"],
            cost: 100,
            score: 0.1,
            equipment: 1,
            window: "steady-window",
          },
        ],
        source_probability: 0.4,
        evidence_status: "ambiguous",
        source_region90: {
          level: 0.9,
          meaning: "Conditional single-source quadrature mass.",
          area_m2: 1200,
          domain_area_m2: 2000,
          resolution_m: 20,
          support: "Rectangle spanned by domain anchors",
          cells: [
            {
              polygon: [
                { latitude: 0, longitude: 0 },
                { latitude: 0, longitude: 0.001 },
                { latitude: 0.001, longitude: 0.001 },
              ],
              weight: 1,
            },
          ],
        },
        rows_loaded: 100,
        rows_excluded: 5,
        rows_input: 95,
        rows_used: 40,
        selection: { method: "explicit test selection", limit: 40, seed: 7 },
        diagnostics: {
          method: "Unavailable diagnostic presentation fixture",
          predictive_warning: false,
          held_out_sensor: [
            {
              sensor_id: "A",
              rows: 10,
              unavailable: "unsupported geometry",
              flagged: false,
            },
          ],
        },
      },
    }),
  );
  await page.goto("/");
  await page
    .getByRole("button", { name: "Generate measurement plans", exact: true })
    .click();
  await expect(
    page.getByRole("status").filter({ hasText: "Source not identified" }),
  ).toBeVisible();
  await expect(page.getByLabel("Scientific evidence details")).toContainText(
    "100 loaded · 5 excluded · 95 usable · 40 fitted",
  );
  await expect(page.getByLabel("Scientific evidence details")).toContainText(
    "No held-out sensor predictive check is available",
  );
  await expect(page.locator(".source-label").first()).toHaveText("S1");
  await expect(page.locator(".map-canvas polygon")).toHaveCount(1);
  await page
    .getByText("Held-out sensor prediction details", { exact: true })
    .click();
  await expect(
    page.getByText(
      "A: 10 held-out rows; check unavailable: unsupported geometry.",
      { exact: true },
    ),
  ).toBeVisible();
  await page.getByRole("button", { name: "Scenarios", exact: true }).click();
  await page.getByLabel("Maximum fitted readings").fill("64");
  await expect(page.locator(".map-canvas polygon")).toHaveCount(0);
  expect(errors).toEqual([]);
});
