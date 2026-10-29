import { spawnSync } from "node:child_process";

const siteUrl = process.env.VITE_SITE_URL?.trim();
if (!siteUrl || !/^https?:\/\//i.test(siteUrl)) {
  throw new Error("VITE_SITE_URL is required for a public build, for example https://upwind.example");
}

const result = spawnSync("npm", ["run", "build"], {
  stdio: "inherit",
  env: { ...process.env, VITE_APP_SURFACE: "explorer" },
});
if (result.error) throw result.error;
if ((result.status ?? 1) !== 0) process.exit(result.status ?? 1);
const prune = spawnSync("node", ["scripts/prune-public-assets.mjs"], { stdio: "inherit" });
if (prune.error) throw prune.error;
if ((prune.status ?? 1) !== 0) process.exit(prune.status ?? 1);
const verify = spawnSync("npm", ["run", "verify:public"], { stdio: "inherit", env: { ...process.env, VITE_APP_SURFACE: "explorer" } });
if (verify.error) throw verify.error;
process.exit(verify.status ?? 1);
