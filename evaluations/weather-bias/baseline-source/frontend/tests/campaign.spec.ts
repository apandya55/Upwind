import { test, expect } from "@playwright/test";

test("campaign example preserves periods, explains shared release and exports its result", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("/");
  await page.getByRole("button", { name: "Scenarios", exact: true }).click();
  await page
    .getByRole("button", { name: "Open synthetic campaign example" })
    .click();
  await page
    .getByText("Campaign periods and physical metadata", { exact: true })
    .click();
  await expect(
    page.getByLabel("Period identifier", { exact: true }),
  ).toHaveCount(4);
  await expect(
    page.getByLabel(
      "Fixed source location and constant release across all periods",
    ),
  ).toBeChecked();
  await expect(
    page.getByLabel(
      "Observed wind direction uncertainty (standard deviation, degrees)",
    ),
  ).toHaveValue("3");
  await page
    .getByRole("button", { name: "Analyze current study", exact: true })
    .click();
  await expect(page.getByLabel("Scientific evidence details")).toContainText(
    "4 separately steady periods",
  );
  await expect(page.getByLabel("Scientific evidence details")).toContainText(
    "similarly fitting explanations",
  );
  await page
    .getByText("Cross-period prediction checks", { exact: true })
    .click();
  await expect(page.getByLabel("Scientific evidence details")).toContainText(
    "period-1",
  );
  await expect(
    page.getByText("Prediction variance · exhaustive", { exact: true }),
  ).toBeVisible();
  await page.screenshot({
    path: "../.local/research/campaign-desktop.png",
    fullPage: true,
  });
  await page.getByRole("button", { name: "Scenarios", exact: true }).click();
  await page
    .getByText("Campaign periods and physical metadata", { exact: true })
    .click();
  await page
    .getByLabel("Fixed source location and constant release across all periods")
    .uncheck();
  await page
    .getByRole("button", { name: "Analyze current study", exact: true })
    .click();
  await expect(
    page.getByText(/Confirm a fixed source location and constant release/),
  ).toBeVisible();
  expect(errors).toEqual([]);
});
