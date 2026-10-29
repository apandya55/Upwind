import { readdir, readFile, stat } from "node:fs/promises";

const dist = new URL("../dist/", import.meta.url);
const vercelConfig = JSON.parse(await readFile(new URL("../vercel.json", import.meta.url), "utf8"));
if (!vercelConfig.rewrites?.some((rule) => rule.source === "/(.*)" && rule.destination === "/index.html")) {
  throw new Error("Vercel config must serve the app shell for direct client-side routes");
}
const assets = await readdir(new URL("assets/", dist));
for (const requiredPath of [
  "landing/quality-recovery/overview.webp",
  "landing/quality-recovery/place.webp",
  "landing/quality-recovery/monitors.webp",
  "landing/quality-recovery/sources.webp",
]) {
  await stat(new URL(requiredPath, dist));
}
for (const unusedPath of [
  "landing/quality-recovery/overview.png",
  "landing/quality-recovery/place.png",
  "landing/quality-recovery/monitors.png",
  "landing/quality-recovery/sources.png",
  "landing/explorer-overview.png",
  "landing/explorer-place.png",
  "landing/explorer-sources.png",
  "landing/unfolding-map/unfolding-map.glb",
]) {
  try {
    await stat(new URL(unusedPath, dist));
    throw new Error(`Public build contains an unused source asset ${unusedPath}`);
  } catch (error) {
    if (error?.code !== "ENOENT") throw error;
  }
}
for (const authoringPath of ["landing/unfolding-map/unfolding-map.blend", "landing/unfolding-map/unfolding-map.blend1"]) {
  try {
    await stat(new URL(authoringPath, dist));
    throw new Error(`Public build contains authoring-only asset ${authoringPath}`);
  } catch (error) {
    if (error?.code !== "ENOENT") throw error;
  }
}
if (assets.some((name) => /^App-.*\.js$/.test(name))) {
  throw new Error("Public build contains the local investigation application chunk");
}
try {
  await stat(new URL("workspace/index.html", dist));
  throw new Error("Public build contains a local workspace route shell");
} catch (error) {
  if (error?.code !== "ENOENT") throw error;
}
const robots = await readFile(new URL("robots.txt", dist), "utf8");
if (!robots.includes("Disallow: /workspace")) throw new Error("Public robots.txt does not disallow /workspace");
const llms = await readFile(new URL("llms-full.txt", dist), "utf8");
if (!llms.includes("does not ship the local /workspace route")) throw new Error("Public machine-readable metadata omits local boundary");
console.log("Public build verified: Explorer surface only, no workspace route shell, local workspace excluded from crawlers.");
