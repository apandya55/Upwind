import { rm } from "node:fs/promises";

const dist = new URL("../dist/", import.meta.url);
const generatedSources = [
  "landing/quality-recovery/monitors.png",
  "landing/quality-recovery/overview.png",
  "landing/quality-recovery/place.png",
  "landing/quality-recovery/sources.png",
  "landing/durham-map-view.png",
  "landing/explorer-overview.png",
  "landing/explorer-place.png",
  "landing/explorer-sources.png",
  "landing/landing-desktop.png",
  "landing/landing-hero.png",
  "landing/landing-mobile.png",
];

for (const relativePath of generatedSources) {
  await rm(new URL(relativePath, dist), { force: true });
}

console.log("Removed unused source imagery and authoring assets from the public build.");
