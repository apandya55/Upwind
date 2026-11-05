import { spawnSync } from "node:child_process";

const siteUrl =
  process.env.VITE_SITE_URL?.trim() ||
  (process.env.VERCEL_URL ? `https://${process.env.VERCEL_URL}` : "https://upwind.vercel.app");
const apiUrl = process.env.VITE_API_BASE_URL?.trim() || "";

const env = {
  ...process.env,
  VITE_SITE_URL: siteUrl,
  VITE_API_BASE_URL: apiUrl,
  VITE_APP_SURFACE: "explorer",
};

const result = spawnSync("npm", ["run", "build"], {
  stdio: "inherit",
  env,
});
if (result.error) throw result.error;
if ((result.status ?? 1) !== 0) process.exit(result.status ?? 1);

const prune = spawnSync("node", ["scripts/prune-public-assets.mjs"], {
  stdio: "inherit",
});
if (prune.error) throw prune.error;
if ((prune.status ?? 1) !== 0) process.exit(prune.status ?? 1);

const verify = spawnSync("npm", ["run", "verify:public"], {
  stdio: "inherit",
  env,
});
if (verify.error) throw verify.error;
process.exit(verify.status ?? 1);
