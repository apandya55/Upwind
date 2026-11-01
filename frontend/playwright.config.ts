import { defineConfig } from "@playwright/test";
const python = process.env.UPWIND_PYTHON || ".venv/bin/python";
export default defineConfig({
  testDir: "./tests",
  testIgnore: "**/public-surface.spec.ts",
  workers: 1,
  timeout: 240000,
  expect: { timeout: 120000 },
  use: {
    baseURL: "http://127.0.0.1:5174",
    viewport: { width: 1440, height: 1000 },
    launchOptions: {
      ...(process.env.CHROMIUM_PATH ? { executablePath: process.env.CHROMIUM_PATH } : {}),
      args: ["--no-sandbox"],
    },
    screenshot: "only-on-failure",
  },
  webServer: [
    {
      command: `${python} scripts/create_test_release.py --output-root .local/browser-test-data && ${python} -m uvicorn upwind.api:app --host 127.0.0.1 --port 8001`,
      url: "http://127.0.0.1:8001/api/health",
      reuseExistingServer: false,
      cwd: "..",
      env: {
        UPWIND_NATIONAL_RELEASE_DIR: ".local/browser-test-data/release",
        UPWIND_OSM_ROADS_DIR: ".local/browser-test-data/context/osm_roads/raw",
        UPWIND_DATA_DIR: ".local/browser-test-data/workspace",
        PYTHONPATH: "backend",
      },
    },
    {
      command: "npm run dev -- --port 5174 --strictPort",
      url: "http://127.0.0.1:5174",
      reuseExistingServer: false,
      env: { UPWIND_API_URL: "http://127.0.0.1:8001" },
    },
  ],
});
