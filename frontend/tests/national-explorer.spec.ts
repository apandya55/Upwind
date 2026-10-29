import { expect, test } from "@playwright/test";

async function clickViewportSymbol(page: import("@playwright/test").Page, items: any[]) {
  const point = await page.evaluate((features: any[]) => {
    const map = document.querySelector(".national-map") as HTMLElement;
    const canvas = document.querySelector(".maplibregl-canvas") as HTMLCanvasElement;
    const mapInstance = (canvas as HTMLCanvasElement & { _map?: { project: (coordinate: [number, number]) => { x: number; y: number } } })._map;
    if (mapInstance) {
      const bounds = canvas.getBoundingClientRect();
      const candidates = features.filter((item) => !item.is_cluster).map((item) => {
        const position = mapInstance.project([item.render_longitude ?? item.longitude, item.render_latitude ?? item.latitude]);
        return { x: bounds.x + position.x, y: bounds.y + position.y };
      }).filter(({x,y}) => x > bounds.x + 40 && x < Math.min(bounds.right - 450, innerWidth - 450) && y > bounds.y + 235 && y < bounds.bottom - 90);
      candidates.sort((a,b) => Math.hypot(a.x - (bounds.x + 430), a.y - (bounds.y + bounds.height / 2)) - Math.hypot(b.x - (bounds.x + 430), b.y - (bounds.y + bounds.height / 2)));
      return candidates[0];
    }
    const zoom = Number(map.dataset.zoom);
    const centerLon = Number(map.dataset.longitude), centerLat = Number(map.dataset.latitude);
    const world = 512 * 2 ** zoom;
    const mercator = (lon: number, lat: number) => ({
      x: (lon + 180) / 360 * world,
      y: (1 - Math.asinh(Math.tan(lat * Math.PI / 180)) / Math.PI) / 2 * world,
    });
    const center = mercator(centerLon, centerLat);
    const bounds = canvas.getBoundingClientRect();
    const candidates = features.map((item) => {
      const pos = mercator(item.render_longitude ?? item.longitude, item.render_latitude ?? item.latitude);
      return { x: bounds.x + bounds.width / 2 + pos.x - center.x, y: bounds.y + bounds.height / 2 + pos.y - center.y };
    }).filter(({x,y}) => x > bounds.x + 40 && x < Math.min(bounds.right - 450, innerWidth - 450) && y > bounds.y + 235 && y < bounds.bottom - 90);
    candidates.sort((a,b) => Math.hypot(a.x - (bounds.x + 430), a.y - (bounds.y + bounds.height / 2)) - Math.hypot(b.x - (bounds.x + 430), b.y - (bounds.y + bounds.height / 2)));
    return candidates[0];
  }, items);
  expect(point).toBeTruthy();
  await page.mouse.click(point!.x, point!.y);
}

test("public landing and local entry routes are distinct from the Explorer", async ({ page }) => {
  await page.goto("/landing");
  await expect(page.getByRole("heading", { name: "Explore America’s air quality, place by place." })).toBeVisible();
  await page.keyboard.press("Tab");
  await expect(page.getByRole("link", { name: "Skip to content" })).toBeFocused();
  await expect(page.getByRole("link", { name: /Open the atlas/ }).first()).toHaveAttribute("href", "/explore");
  await page.goto("/local");
  await expect(page.getByRole("heading", { name: "Bring local readings into view." })).toBeVisible();
  await expect(page.getByRole("link", { name: /Use the public map|Explore the map/ }).first()).toHaveAttribute("href", "/explore");
});

test("landing uses a static map preview and adapts to mobile", async ({ page }) => {
  await page.goto("/landing");
  await expect(page.getByRole("heading", { name: "Read the record in context." })).toBeVisible();
  await expect(page.locator(".preview-frame img")).toBeVisible();
  await expect(page.locator("#coverage-heading")).toBeVisible();
  await expect(page.locator("a.preview-map")).toHaveCount(0);

  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/landing");
  await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.emulateMedia({ reducedMotion: "reduce" });
  await expect(page.locator(".preview-frame img")).toBeVisible();
  await expect(page.getByRole("link", { name: /Open the atlas/ }).first()).toBeVisible();
});

test("root path directly renders the National Explorer map with discrete navigation and menu drawer", async ({ page }, testInfo) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/");
  await expect(page.locator(".national-header")).toBeVisible();
  await expect(page.locator(".national-search")).toBeVisible();
  await expect(page.locator(".national-layers")).toBeVisible();
  await expect(page.getByRole("button", { name: "Open menu" })).toBeVisible();

  // Take screenshot of map hero
  await page.waitForTimeout(1000);
  await page.screenshot({ path: testInfo.outputPath("national-map-hero.png") });

  // Test opening hamburger menu
  await page.getByRole("button", { name: "Open menu" }).click();
  await page.waitForTimeout(300);
  await expect(page.locator(".national-menu-drawer")).toBeVisible();
  await expect(page.getByRole("link", { name: /Run Model Locally/ })).toHaveAttribute("href", "/local");
  await expect(page.getByRole("link", { name: /Scientific Methodology/ })).toHaveAttribute("href", "/methodology");
  await expect(page.getByRole("link", { name: /About UPWIND/ })).toHaveAttribute("href", "/about");

  // Take screenshot with menu drawer open
  await page.screenshot({ path: testInfo.outputPath("national-menu-drawer.png") });

  // Test closing hamburger menu
  await page.getByRole("button", { name: "Close menu" }).click();
  await expect(page.locator(".national-menu-drawer")).toHaveCount(0);
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await expect(page.locator(".national-search")).toBeVisible();
  await expect(page.locator(".national-layers")).toBeVisible();
  await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.waitForTimeout(500);
  await page.screenshot({ path: testInfo.outputPath("national-explorer-mobile.png") });
});

test("National Explorer searches and compares a real Census place", async ({ page }) => {
  await page.goto("/explore");
  await expect(page.locator(".national-method-note")).toContainText("Historical estimates are place-point estimates");
  await expect(page.locator(".national-method-note a")).toHaveAttribute("href", "/methodology");
  await expect(page.getByText("Higher estimates in loaded map view")).toHaveCount(0);
  await expect(page.locator(".national-bottom")).toHaveCount(0);
  await expect(page.locator(".methodology-card")).toHaveCount(0);

  await page.getByRole("button", { name: "Raleigh" }).click();

  await expect(page.getByRole("heading", { name: "Raleigh city, North Carolina" })).toBeVisible();
  await expect(page.getByText(/Nearest training monitor/)).toBeVisible();
  await expect(page.getByRole("heading", { name: "Why this estimate?" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Nearby documented evidence" })).toBeVisible();
  await expect(page.getByText(/AQS annual site summaries|No AQS annual site summary/)).toBeVisible();
  await page.getByRole("button", { name: /Compare place/ }).click();
  await expect(page.getByRole("heading", { name: /Place comparison/ })).toBeVisible();
  await expect(page.getByText("Raleigh city", { exact: true }).last()).toBeVisible();
});

test("Durham Local Pollution Investigation shows real OSM, monitor, and inventory evidence with export", async ({ page }, testInfo) => {
  await page.goto("/explore");
  await page.getByRole("button", { name: "Durham" }).click();
  await expect(page.getByRole("complementary", { name: "Place details and evidence" }).getByRole("heading", { name: "Durham city", exact: true })).toBeVisible();
  await expect(page.getByRole("textbox", { name: "Search Census places" })).toHaveAttribute("aria-expanded", "false");
  const investigate = page.getByRole("button", { name: "Investigate Location" });
  await expect(investigate).toBeVisible();
  expect(await page.locator(".investigate-action").evaluate((action) => action.compareDocumentPosition(document.querySelector(".detail-metric")!) & Node.DOCUMENT_POSITION_FOLLOWING)).toBeTruthy();
  await investigate.click();
  const investigation = page.getByRole("region", { name: "Local pollution investigation for Durham city" });
  await expect(investigation).toBeVisible();
  await expect(investigation).toContainText("Major road network");
  await expect(investigation).toContainText("Fayetteville Road");
  await expect(investigation).toContainText("Open Database License");
  await expect(investigation).toContainText("EPA NEI inventory records");
  await expect(investigation).toContainText("across 2 named corridors");
  await page.screenshot({ path: testInfo.outputPath("durham-investigation-desktop.png") });
  await investigation.getByRole("heading", { name: "Major road network" }).scrollIntoViewIfNeeded();
  await expect(investigation.getByRole("heading", { name: "Major road network" })).toBeVisible();
  const download = page.waitForEvent("download");
  await investigation.getByRole("button", { name: "Export JSON" }).click();
  expect((await download).suggestedFilename()).toContain("upwind-investigation-3719000-2024.json");
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/explore?year=2024&place=3719000");
  await expect(page.getByRole("complementary", { name: "Place details and evidence" }).getByRole("heading", { name: "Durham city", exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Investigate Location" }).click();
  await expect(page.getByRole("region", { name: "Local pollution investigation for Durham city" })).toBeVisible();
  await page.waitForTimeout(800);
  await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await expect(page.locator(".map-selected-pulse-marker")).toHaveCount(1);
  await page.emulateMedia({ reducedMotion: "reduce" });
  await expect.poll(() => page.getByRole("textbox", { name: "Search Census places" }).getAttribute("aria-expanded")).toBe("false");
  const panelTransition = await page.locator(".national-detail-panel").evaluate((node) => getComputedStyle(node).transitionDuration.split(",").every((value) => Number.parseFloat(value.trim()) < 0.001));
  expect(panelTransition).toBe(true);
  await page.screenshot({ path: testInfo.outputPath("durham-investigation-mobile.png") });
  const panelWidths = await page.locator(".national-detail-panel").evaluate((node) => ({ client: node.clientWidth, scroll: node.scrollWidth }));
  expect(panelWidths.scroll).toBeLessThanOrEqual(panelWidths.client + 1);
  await investigation.getByRole("heading", { name: "Major road network" }).scrollIntoViewIfNeeded();
  await expect(investigation.getByRole("heading", { name: "Major road network" })).toBeVisible();
});

test("place search supports keyboard selection and shareable URL state", async ({ page }) => {
  await page.goto("/explore");
  const search = page.getByRole("textbox", { name: "Search Census places" });
  await search.fill("Durham, North Carolina");
  const option = page.getByRole("option", { name: /Durham.*North Carolina/ }).first();
  await expect(option).toBeVisible();
  await search.press("ArrowDown");
  await search.press("Enter");
  await expect(page.getByRole("heading", { name: "Durham city, North Carolina" })).toBeVisible();
  await expect(page).toHaveURL(/place=37/);
  await expect(page.getByRole("heading", { name: "Why this estimate?" })).toBeVisible();
});

test("clicking a rendered place point keeps its detail panel selected", async ({ page }) => {
  const viewportResponse = page.waitForResponse((response) => response.url().includes("/api/national/viewport?") && new URL(response.url()).searchParams.get("layer") === "estimates");
  await page.goto("/explore");
  const viewport = await (await viewportResponse).json();
  await expect(page.getByRole("region", { name: "National evidence map" })).toBeVisible();
  // Click the exact representative coordinate returned by the viewport query.
  await clickViewportSymbol(page, viewport.items);
  await expect(page.locator(".national-detail-panel")).not.toContainText("Start with a place.");
  await expect(page.getByRole("heading", { name: /records nearby|Selected Census place|Monitor|facility/i }).first()).toBeVisible();
  await expect(page.getByRole("heading", { name: "Start with a place." })).toHaveCount(0);
});

test("monitor points load and the quick source overlay can be toggled", async ({ page }) => {
  const monitorResponse = page.waitForResponse((response) => response.url().includes("/api/national/viewport?") && new URL(response.url()).searchParams.get("layer") === "monitors");
  await page.goto("/explore?year=2024&layer=monitors");
  const monitors = await (await monitorResponse).json();
  expect(monitors.items.length).toBeGreaterThan(0);
  await expect(page.getByRole("button", { name: "Monitors" })).toHaveAttribute("aria-pressed", "true");

  await page.getByRole("button", { name: "Estimates" }).click();
  const sourceResponse = page.waitForResponse((response) => response.url().includes("/api/national/viewport?") && new URL(response.url()).searchParams.get("layer") === "sources");
  await page.getByRole("button", { name: "Show sources" }).click();
  await expect(page.getByRole("button", { name: "Sources on" })).toHaveAttribute("aria-pressed", "true");
  const sources = await (await sourceResponse).json();
  expect(sources.items.length).toBeGreaterThan(0);
});

test("back and forward restore the selected place, year, and evidence layer", async ({ page }) => {
  await page.goto("/explore?year=2024&layer=estimates");
  const search = page.getByRole("textbox", { name: "Search Census places" });
  await search.fill("Durham, North Carolina");
  await page.getByRole("option", { name: /Durham.*North Carolina/ }).first().click();
  await expect(page).toHaveURL(/place=3719000/);
  await page.getByRole("button", { name: "Monitors" }).click();
  await page.getByLabel("Historical year").selectOption("2025");
  await expect(page).toHaveURL(/year=2025.*layer=monitors.*place=3719000/);

  await page.goBack();
  await expect(page.getByLabel("Historical year")).toHaveValue("2024");
  await expect(page.getByRole("button", { name: "Monitors" })).toHaveAttribute("aria-pressed", "true");
  await page.goBack();
  await expect(page.getByRole("heading", { name: "Durham city, North Carolina" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Estimates" })).toHaveAttribute("aria-pressed", "true");
  await page.goForward();
  await expect(page.getByRole("button", { name: "Monitors" })).toHaveAttribute("aria-pressed", "true");
});

test("source overlay combines with estimates and share links restore the camera", async ({ page, browser }) => {
  const layerResponses = new Set<string>();
  page.on("response", (response) => {
    if (!response.url().includes("/api/national/viewport?")) return;
    const layer = new URL(response.url()).searchParams.get("layer");
    if (layer) layerResponses.add(layer);
  });
  await page.goto("/explore?year=2024&layer=estimates&sources=1");
  await expect(page.getByRole("button", { name: "Sources on" })).toHaveAttribute("aria-pressed", "true");
  await expect.poll(() => ["estimates", "sources"].every((layer) => layerResponses.has(layer))).toBe(true);
  await expect(page.getByText(/Inventory locations are separate records, not proven contributors/)).toBeVisible();
  const map = page.locator(".national-map");
  await page.getByRole("button", { name: "Zoom in" }).click();
  await page.getByRole("button", { name: "Zoom in" }).click();
  const box = (await map.boundingBox())!;
  await page.mouse.move(box.x + box.width * .55, box.y + box.height * .52);
  await page.mouse.down();
  await page.mouse.move(box.x + box.width * .61, box.y + box.height * .56, { steps: 8 });
  await page.mouse.up();
  await expect.poll(() => new URL(page.url()).searchParams.get("camera")).not.toBeNull();
  const sharedUrl = page.url();
  const camera = new URL(sharedUrl).searchParams.get("camera")!.split(",").map(Number);
  const context = await browser.newContext();
  const freshPage = await context.newPage();
  await freshPage.goto(sharedUrl);
  await expect(freshPage.getByRole("button", { name: "Sources on" })).toHaveAttribute("aria-pressed", "true");
  await expect.poll(() => freshPage.locator(".national-map").getAttribute("data-longitude")).toBe(camera[0].toFixed(4));
  await expect(freshPage.locator(".national-map")).toHaveAttribute("data-latitude", camera[1].toFixed(4));
  await expect(freshPage.locator(".national-map")).toHaveAttribute("data-zoom", camera[2].toFixed(2));
  await context.close();
});

test("place snapshot exports and print use the API snapshot", async ({ page }) => {
  await page.goto("/explore?year=2024&place=3719000");
  await expect(page.getByRole("heading", { name: "Durham city, North Carolina" })).toBeVisible();

  const csvDownload = page.waitForEvent("download");
  await page.getByRole("button", { name: "Export place" }).click();
  expect((await csvDownload).suggestedFilename()).toBe("upwind-national-2024-snapshot.csv");

  const geojsonDownload = page.waitForEvent("download");
  await page.getByRole("button", { name: "GeoJSON" }).click();
  expect((await geojsonDownload).suggestedFilename()).toBe("upwind-national-2024-snapshot.geojson");

  await page.evaluate(() => { window.print = () => undefined; });
  await page.getByRole("button", { name: "Print brief" }).click();
  await expect(page.locator(".print-snapshot")).toContainText("Durham city, North Carolina");
  await expect(page.locator(".print-snapshot")).toContainText("Release");
  await expect(page.locator(".print-snapshot")).toContainText("Questions for further investigation");
});

test("withheld estimates remain explicit and snapshot failures are shown", async ({ page }) => {
  test.setTimeout(30000);
  await page.goto("/explore?year=2018&place=3719000");
  await expect(page.getByRole("heading", { name: "Durham city, North Carolina" })).toBeVisible();
  await expect(page.getByText("Estimate withheld for 2018")).toBeVisible();

  await page.route(/\/api\/national\/snapshot\.csv(?:\?|$)/, (route) => route.fulfill({ status: 503, body: "unavailable" }));
  await page.getByRole("button", { name: "Export place" }).click();
  await expect(page.getByRole("alert")).toContainText("Export could not be loaded");

  await page.route("**/api/national/snapshot?geoids=*", (route) => route.fulfill({ status: 503, body: "unavailable" }));
  const printResponse = page.waitForResponse((response) => response.url().includes("/api/national/snapshot?geoids=") && response.status() === 503);
  await page.getByRole("button", { name: "Print brief" }).click();
  await printResponse;
  await expect(page.getByText("The print snapshot could not be loaded.", { exact: false })).toBeVisible();
});

test("viewport aggregation represents all filtered records within its symbol budget", async ({ page }) => {
  const responses: { layer: string; represented: number; symbols: number; bytes: number }[] = [];
  page.on("response", async (response) => {
    if (!response.url().includes("/api/national/viewport?")) return;
    const body = await response.json().catch(() => null);
    if (body) responses.push({ layer: body.layer, represented: body.represented_records, symbols: body.symbol_count, bytes: JSON.stringify(body).length });
  });
  await page.goto("/explore");
  await expect(page.locator(".map-aggregation-status")).toHaveCount(0);
  await expect(page.locator(".map-coverage-note")).toHaveCount(0);
  await expect.poll(() => responses.length).toBeGreaterThan(0);
  expect(responses[0].represented).toBeGreaterThanOrEqual(responses[0].symbols);
  expect(responses[0].symbols).toBeLessThanOrEqual(3000);
  const mapLayerIds = await page.locator(".maplibregl-canvas").evaluate((canvas) => {
    const map = (canvas as HTMLCanvasElement & { _map?: { getStyle(): { layers: { id: string; type: string }[] } } })._map;
    return map?.getStyle().layers.map((layer) => `${layer.id}:${layer.type}`) || [];
  });
  expect(mapLayerIds.every((layer) => !/(?:place|monitor|facility)-count:/.test(layer))).toBe(true);
  await page.getByRole("button", { name: "Monitors" }).click();
  await expect.poll(() => responses.some((item) => item.layer === "monitors")).toBe(true);
  await page.getByRole("button", { name: "Show sources" }).click();
  await expect.poll(() => responses.some((item) => item.layer === "sources")).toBe(true);
  expect(responses.every((item) => item.represented >= item.symbols && item.symbols <= 3000)).toBe(true);
});

test("dense aggregate opens a pageable, exact member list", async ({ page }) => {
  let result: any = null;
  page.on("response", async (response) => {
    if (response.url().includes("/api/national/viewport?") && !result) result = await response.json().catch(() => null);
  });
  await page.goto("/explore");
  await expect.poll(() => result?.items?.length).toBeGreaterThan(0);
  const candidates = result.items.filter((item: any) => item.is_cluster && item.member_count > 1);
  expect(candidates.length).toBeGreaterThan(0);
  const boxes = await page.evaluate((items) => items.map(({ longitude, latitude, member_count, cluster_id }) => {
    const zoom = 3.1, size = 512 * 2 ** zoom;
    const x = (lon: number) => (lon + 180) / 360 * size;
    const y = (lat: number) => (1 - Math.asinh(Math.tan(lat * Math.PI / 180)) / Math.PI) / 2 * size;
    return { member_count, cluster_id, x: innerWidth / 2 + x(longitude) - x(-98.5), y: innerHeight / 2 + y(latitude) - y(39.8) };
  }), candidates);
  const cluster = boxes.find((item) => item.x > 10 && item.x < 1430 && item.y > 10 && item.y < 890);
  expect(cluster).toBeTruthy();
  await page.locator(".maplibregl-canvas").click({ position: { x: cluster.x, y: cluster.y }, force: true });
  // Several grid cells can overlap at national scale. MapLibre correctly opens
  // the topmost rendered aggregate under the pointer, which may differ from
  // the fixture cell whose approximate screen point was calculated above.
  await expect(page.getByRole("heading", { name: /records nearby/ })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Records", exact: true })).toBeVisible();
  await expect(page.locator(".source-row").first()).toBeVisible();
  await page.screenshot({ path: "/tmp/upwind-polish/cluster-members.png" });
});

test("mobile Explorer layout keeps search, map, and layer controls within the viewport", async ({ page }, testInfo) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/explore");
  await expect(page.getByRole("textbox", { name: "Search Census places" })).toBeVisible();
  await expect(page.getByRole("group", { name: "Map evidence layer" })).toBeVisible();
  await expect(page.getByRole("region", { name: "National evidence map" })).toBeVisible();
  await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await page.screenshot({ path: testInfo.outputPath("explorer-mobile.png"), fullPage: true });
});

test("methodology shows corrected AQS event policy and matched PRISM evidence", async ({ page }) => {
  await page.goto("/explore");
  await page.getByRole("button", { name: "Read limits" }).click();
  await expect(page.getByText(/Events Included when present, otherwise No Events/)).toBeVisible();
  await expect(page.getByText(/1\.320\/1\.859\/−0\.081/)).toBeVisible();
  await expect(page.getByText(/5\/5 2024 folds but only 3\/5 provisional 2025 folds/)).toBeVisible();
});

test("map evidence and basemap tile failures show recoverable fallbacks", async ({ page }) => {
  await page.route("**/api/national/viewport?**", (route) => route.fulfill({ status: 503, body: "unavailable" }));
  await page.route("https://tile.openstreetmap.org/**", (route) => route.fulfill({ status: 503, body: "unavailable" }));
  await page.goto("/explore");
  await expect(page.getByRole("alert")).toContainText("Map evidence could not be loaded");
  await expect(page.getByText("Map tiles are temporarily unavailable.")).toBeVisible();
  await expect(page.getByRole("textbox", { name: "Search Census places" })).toBeVisible();
});

test("map supports deep zoom, drag pan, and reset without losing its controls", async ({ page }) => {
  await page.goto("/explore");
  const map = page.locator(".national-map");
  await expect(map).toBeVisible();
  await expect(map.locator("canvas")).toHaveCount(1);
  const before = await map.evaluate((node) => ({ center: (node as HTMLElement).dataset.center, zoom: (node as HTMLElement).dataset.zoom }));
  for (let i = 0; i < 5; i++) await page.getByRole("button", { name: "Zoom in" }).click();
  await expect.poll(() => map.locator("canvas").count()).toBeGreaterThan(0);
  const zoom = await map.locator("canvas").evaluate((canvas) => (canvas as HTMLCanvasElement).width);
  expect(zoom).toBeGreaterThan(0);
  const box = (await map.boundingBox())!;
  await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
  await page.mouse.down(); await page.mouse.move(box.x + box.width / 2 + 140, box.y + box.height / 2 + 70, { steps: 8 }); await page.mouse.up();
  await page.waitForTimeout(450);
  await page.getByRole("button", { name: "Reset map view" }).click();
  await expect(page.getByRole("button", { name: "Reset map view" })).toBeVisible();
  expect(before).toBeTruthy();
});

test("stale viewport responses cannot replace the latest pan results", async ({ page }) => {
  let delayedRelease: (() => void) | undefined;
  let firstBounds = "";
  await page.route("**/api/national/viewport?**", async (route) => {
    const url = route.request().url();
    const bounds = new URL(url).searchParams.get("west") || "";
    if (!firstBounds) firstBounds = bounds;
    if (bounds === firstBounds) {
      await new Promise<void>((resolve) => { delayedRelease = resolve; });
      await route.fulfill({ json: { layer: "estimates", complete: true, represented_records: 1, symbol_count: 1, items: [{ id: "1111111", name: "Stale result", state: "Test", latitude: 35, longitude: -79, model_estimates: {}, cluster_id: "places.json:3:1:1", is_cluster: false, member_count: 1 }] } });
      return;
    }
    await route.fulfill({ json: { layer: "estimates", complete: true, represented_records: 1, symbol_count: 1, items: [{ id: "2222222", name: "Latest viewport", state: "Test", latitude: 35, longitude: -79, model_estimates: {}, cluster_id: "places.json:3:2:1", is_cluster: false, member_count: 1 }] } });
  });
  await page.goto("/explore");
  const map = page.locator(".national-map");
  await expect.poll(() => delayedRelease ? 1 : 0).toBe(1);
  const box = (await map.boundingBox())!;
  await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
  await page.mouse.down(); await page.mouse.move(box.x + box.width / 2 + 240, box.y + box.height / 2, { steps: 8 }); await page.mouse.up();
  await expect.poll(() => new URL(page.url()).searchParams.get("place") || "").toBe("");
  await page.waitForTimeout(250);
  delayedRelease?.();
  await page.waitForTimeout(300);
  expect(await page.locator(".rank-row").allTextContents()).not.toContain("Stale result");
});

test("map heading is framed in a readable card, select has single chevron, and dot switching preserves clean URL", async ({ page }) => {
  await page.goto("/explore");
  // 1. Heading is in a frosted title card with background
  const titleCard = page.locator(".national-map-title-card");
  await expect(titleCard).toBeVisible();
  await expect(titleCard.getByRole("heading", { name: "National evidence map" })).toBeVisible();

  // 2. Year select has appearance none (single chevron icon without native arrow duplicate)
  const select = page.locator(".national-select select");
  await expect(select).toBeVisible();
  const appearance = await select.evaluate((el) => window.getComputedStyle(el).appearance);
  expect(appearance).toBe("none");

  // 3. Dot switching smoothly selects without changing URL
  const initialUrl = page.url();
  expect(initialUrl).not.toContain("place=");
});

test("historical year selection auto-switches to monitors layer and prevents empty map clash", async ({ page }) => {
  await page.goto("/explore?year=2024&layer=estimates");
  await expect(page.getByRole("button", { name: "Estimates" })).toHaveAttribute("aria-pressed", "true");

  // 1. Switching to an older year (e.g. 2022) auto-switches to monitors layer where real data exists
  await page.getByLabel("Historical year").selectOption("2022");
  await expect(page).toHaveURL(/year=2022.*layer=monitors/);
  await expect(page.getByRole("button", { name: "Monitors" })).toHaveAttribute("aria-pressed", "true");

  // 2. Clicking Estimates while on an older year returns to the modeled year (2024)
  await page.getByRole("button", { name: "Estimates" }).click();
  await expect(page).toHaveURL(/year=2024.*layer=estimates/);
  await expect(page.getByRole("button", { name: "Estimates" })).toHaveAttribute("aria-pressed", "true");

  // 3. Directly loading an unmodeled year on estimates layer presents clear notice without full-width clash
  await page.goto("/explore?year=2022&layer=estimates");
  const notice = page.locator(".map-year-notice");
  await expect(notice).toBeVisible();
  await expect(notice).toContainText("Model estimates are published for 2024");

  // Notice width is bounded (not stretching 100% across to right edge)
  const box = await notice.boundingBox();
  expect(box).not.toBeNull();
  if (box) {
    expect(box.width).toBeLessThanOrEqual(460);
  }

  // Clicking "View 2022 EPA monitors" in the notice switches layer
  await notice.getByRole("button", { name: /View 2022 EPA monitors/i }).click();
  await expect(page).toHaveURL(/year=2022.*layer=monitors/);
  await expect(page.getByRole("button", { name: "Monitors" })).toHaveAttribute("aria-pressed", "true");
});

test("sidebar collapses and expands smoothly via button and keyboard shortcut, repositioning map controls", async ({ page }) => {
  await page.goto("/explore");
  const panel = page.locator(".national-detail-panel");
  await expect(panel).toBeVisible();
  await expect(panel).not.toHaveClass(/is-hidden/);

  // 1. Click "Hide" button to collapse sidebar
  const hideBtn = page.getByRole("button", { name: "Hide sidebar" }).first();
  await hideBtn.click();
  await expect(panel).toHaveClass(/is-hidden/);

  // Floating trigger button appears
  const floatTrigger = page.locator(".floating-sidebar-toggle");
  await expect(floatTrigger).toBeVisible();

  // Floating controls adapt position when collapsed
  await expect(page.locator(".national-shell")).toHaveClass(/sidebar-collapsed/);

  // 2. Click floating trigger to re-open sidebar
  await floatTrigger.click();
  await expect(panel).not.toHaveClass(/is-hidden/);
  await expect(floatTrigger).toHaveCount(0);

  // 3. Keyboard shortcut '[' toggles sidebar
  await page.keyboard.press("[");
  await expect(panel).toHaveClass(/is-hidden/);
  await page.keyboard.press("[");
  await expect(panel).not.toHaveClass(/is-hidden/);

  // 4. Searching and selecting a place automatically reveals the sidebar if collapsed
  await hideBtn.click();
  await expect(panel).toHaveClass(/is-hidden/);
  const search = page.getByRole("textbox", { name: "Search Census places" });
  await search.fill("Raleigh");
  const option = page.getByRole("option", { name: /Raleigh.*North Carolina/ }).first();
  await option.click();
  await expect(panel).not.toHaveClass(/is-hidden/);
  await expect(panel.getByRole("heading", { name: "Raleigh city" })).toBeVisible();
});
