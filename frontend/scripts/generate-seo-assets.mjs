import { mkdir, readFile, writeFile } from "node:fs/promises";
import { join } from "node:path";

const distDir = join(process.cwd(), "dist");
const configuredSiteUrl = process.env.VITE_SITE_URL?.trim();
const explorerBuild = process.env.VITE_APP_SURFACE === "explorer";

if (explorerBuild && !configuredSiteUrl) {
  throw new Error("VITE_SITE_URL is required for the public Explorer build; localhost metadata cannot ship.");
}

if (configuredSiteUrl && !/^https?:\/\//i.test(configuredSiteUrl)) {
  throw new Error("VITE_SITE_URL must be an absolute http(s) URL, for example https://upwind.example");
}

const isFallback = !configuredSiteUrl;
const siteUrl = configuredSiteUrl ? new URL(configuredSiteUrl).origin : "http://localhost:5173";
const buildDate = new Date(process.env.SOURCE_DATE_EPOCH ? Number(process.env.SOURCE_DATE_EPOCH) * 1000 : Date.now()).toISOString().slice(0, 10);
const routes = [
  { path: "/", title: "UPWIND National Explorer | Historical air quality evidence", description: "Explore historical PM2.5 estimates, EPA monitor measurements, and emissions inventory records across U.S. places in the UPWIND public atlas." },
  { path: "/landing", title: "Explore America’s air quality | UPWIND", description: "UPWIND connects historical PM2.5 estimates, EPA monitor measurements, and emissions records by place." },
  { path: "/methodology", title: "Methodology and data sources | UPWIND", description: "Read how UPWIND assigns annual PM2.5 evidence to place points and how to interpret monitors, inventories, and limits." },
  { path: "/about", title: "About the UPWIND air atlas", description: "Learn what the UPWIND public air atlas contains, how its evidence layers differ, and where its limits apply." },
  { path: "/local", title: "Run UPWIND locally | Developer guide", description: "Use the UPWIND source, public datasets, and documented commands to run the air atlas locally." },
];
const routeShells = [
  ...routes.map((route) => ({ ...route, canonicalPath: route.path })),
  { path: "/method", title: "Methodology and data sources | UPWIND", description: "Read how UPWIND assigns annual PM2.5 evidence to place points and how to interpret monitors, inventories, and limits.", canonicalPath: "/methodology" },
  { path: "/explore", title: "UPWIND National Explorer | Historical air quality evidence", description: "Explore historical PM2.5 estimates, EPA monitor measurements, and emissions inventory records across U.S. places in the UPWIND public atlas.", canonicalPath: "/" },
  { path: "/national", title: "UPWIND National Explorer | Historical air quality evidence", description: "Explore historical PM2.5 estimates, EPA monitor measurements, and emissions inventory records across U.S. places in the UPWIND public atlas.", canonicalPath: "/" },
  ...(explorerBuild ? [] : [{ path: "/workspace", title: "UPWIND local investigation workspace", description: "Inspect local air-quality measurements and documented evidence in the UPWIND research workspace.", canonicalPath: "/workspace", robots: "noindex,nofollow" }]),
];

const absolute = (path) => new URL(path, `${siteUrl}/`).toString();

const robots = `# UPWIND crawler policy\n# ${isFallback ? "Local fallback only. Set VITE_SITE_URL before public deployment." : "Public deployment policy."}\nUser-agent: *\nAllow: /\nDisallow: /api/\nDisallow: /workspace\nDisallow: /admin/\nDisallow: /private/\n\nSitemap: ${absolute("/sitemap.xml")}\n`;

const sitemapEntries = routes.map(({ path }) => `  <url>\n    <loc>${escapeXml(absolute(path))}</loc>\n    <lastmod>${buildDate}</lastmod>\n  </url>`).join("\n");
const sitemap = `<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n${sitemapEntries}\n</urlset>\n`;

const llms = `# UPWIND\n\n> UPWIND is a public atlas for exploring historical U.S. air-quality evidence by place. It keeps modeled or assigned estimates, EPA monitor measurements, and emissions inventory records as separate evidence layers.\n\n## Public pages\n\n- [National Explorer](${absolute("/")}): Search places and compare the available historical evidence layers.\n- [Overview](${absolute("/landing")}): Product overview and how to use the atlas.\n- [Methodology](${absolute("/methodology")}): Data sources, assignment method, validation context, and limitations.\n- [About](${absolute("/about")}): Scope and interpretation boundaries.\n- [Local setup](${absolute("/local")}): Run the project locally and inspect source documentation.\n\n## Evidence layers\n\n- Place estimates are historical PM2.5 values assigned to Census place points using the documented release method. They are not current conditions, personal exposure, or a city-wide average.\n- Monitor records are annual EPA AQS summaries and retain their station, year, metric, completeness, and provenance fields.\n- Inventory records are annual EPA NEI facility records. An inventory amount is not an ambient concentration and does not establish a facility's contribution to a nearby monitor.\n\n## Interpretation\n\nUPWIND supports comparison and documented context. It does not establish source responsibility, causation, health risk, regulatory compliance, field calibration, or operational source-attribution accuracy. Always read the methodology and source notes before interpreting a result.\n\n## Machine-readable references\n\n- [Full context](${absolute("/llms-full.txt")})\n- [Sitemap](${absolute("/sitemap.xml")})\n`;

const llmsFull = `# UPWIND machine-readable context\n\n${isFallback ? "This build uses http://localhost:5173 as a local fallback because VITE_SITE_URL is not configured. Replace it before public deployment." : `Configured public origin: ${siteUrl}.`}\n\n## Entity\n\nUPWIND is a Vite/React web application with a Python/FastAPI data service. Its public National Explorer presents historical U.S. air-quality evidence from Census place points, EPA AQS annual monitor summaries, and EPA NEI facility inventory records. The application preserves dataset dates, source identity, and documented limitations.\n\n## Routes\n\n${routes.map(({ path, title, description }) => `- ${absolute(path)} — ${title}: ${description}`).join("\n")}\n\nThe /workspace route is a local research workflow and is excluded from the public sitemap. /explore and /national are compatibility aliases for the explorer where supported; the canonical public route is /. /method is an alias for /methodology.\n\n## Verified release coverage\n\nThe documented current release includes 32,333 searchable Census places, 31,523 supported 2024 place-point estimates, 894 eligible 2024 EPA monitor sites, and 76,404 mapped 2023 NEI facility records. The estimate method withholds 810 places under its support rules. These are release coverage counts, not validation or impact claims. Verify these values against the About page and release manifest when refreshing the data.\n\n## What a result means\n\nA place estimate is a historical value attached to a Census place point under the release's documented nearest-monitor assignment. It should not be read as a current measurement, a population-weighted city average, or a personal exposure estimate.\n\nA monitor record is an EPA AQS annual summary for a specific site, year, pollutant, metric, and event treatment. Monitor coverage and completeness remain properties of that record.\n\nAn inventory record is an EPA NEI facility-level annual emissions record. It is contextual source information, not an ambient concentration, release-point measurement, or causal attribution. Facility coordinates retain their documented coordinate role and uncertainty.\n\n## Data and limits\n\nThe release documentation names the source vintages, processing steps, coverage counts, and provenance. Those counts describe what is available in the release; they do not establish accuracy or impact. The scientific documentation reports synthetic evaluation results and known limits separately from the public atlas. Unsupported or missing context is surfaced as unavailable rather than filled with invented values.\n\n## Preferred language\n\nUse “historical estimate,” “EPA monitor measurement,” and “inventory record” for the three layers. Avoid saying that UPWIND proves a source caused a measured concentration, that a facility is responsible for local pollution, or that an estimate represents current air quality.\n\n## Source links\n\n- [Methodology](${absolute("/methodology")})\n- [About](${absolute("/about")})\n- [Project local setup](${absolute("/local")})\n`;

await mkdir(distDir, { recursive: true });
const baseHtml = await readFile(join(distDir, "index.html"), "utf8");
const renderShell = (route) => {
  const canonical = absolute(route.canonicalPath);
  let html = baseHtml
    .replace(/<title>[^<]*<\/title>/, `<title>${escapeHtml(route.title)}</title>`)
    .replace(/<meta name="description" content="[^"]*"\/>/, `<meta name="description" content="${escapeHtml(route.description)}"/>`)
    .replace(/<meta property="og:title" content="[^"]*"\/>/, `<meta property="og:title" content="${escapeHtml(route.title)}"/>`)
    .replace(/<meta property="og:description" content="[^"]*"\/>/, `<meta property="og:description" content="${escapeHtml(route.description)}"/>`)
    .replace(/<meta property="og:type" content="[^"]*"\/>/, `<meta property="og:type" content="${route.path === "/methodology" || route.path === "/method" || route.path === "/about" || route.path === "/local" ? "article" : "website"}"/>`);
  html = html.replace('<div id="root"></div>', `<div id="root"><main data-seo-shell><h1>${escapeHtml(route.title)}</h1><p>${escapeHtml(route.description)}</p><p><a href="/methodology">Methodology and data sources</a></p></main></div>`);
  html = html.replace("</head>", `  <meta property="og:url" content="${escapeHtml(canonical)}"/>\n  <link rel="canonical" href="${escapeHtml(canonical)}"/>\n  <meta name="robots" content="${route.robots || "index,follow"}"/>\n</head>`);
  html = html.replace("</head>", `  <meta property="og:image" content="${escapeHtml(absolute("/landing/quality-recovery/overview.webp"))}"/>\n  <meta property="og:image:alt" content="UPWIND National Explorer map preview"/>\n  <meta name="twitter:image" content="${escapeHtml(absolute("/landing/quality-recovery/overview.webp"))}"/>\n</head>`);
  return html;
};
await writeFile(join(distDir, "index.html"), renderShell({ ...routes[0], canonicalPath: "/" }), "utf8");
await Promise.all(routeShells.filter(({ path }) => path !== "/").map(async (route) => {
  const routeDir = join(distDir, route.path.slice(1));
  await mkdir(routeDir, { recursive: true });
  await writeFile(join(routeDir, "index.html"), renderShell(route), "utf8");
}));
const llmsFullForBuild = explorerBuild
  ? llmsFull.replace("The /workspace route is a local research workflow and is excluded from the public sitemap.", "The public build does not ship the local /workspace route; clone the repository and use the local build for private investigations.")
  : llmsFull;
await Promise.all([
  writeFile(join(distDir, "robots.txt"), robots, "utf8"),
  writeFile(join(distDir, "sitemap.xml"), sitemap, "utf8"),
  writeFile(join(distDir, "llms.txt"), llms, "utf8"),
  writeFile(join(distDir, "llms-full.txt"), llmsFullForBuild, "utf8"),
]);

console.log(`Generated robots.txt, sitemap.xml, llms.txt, and llms-full.txt using ${siteUrl}${isFallback ? " (local fallback; set VITE_SITE_URL for deployment)" : ""}.`);

function escapeXml(value) {
  return value.replace(/[<>&'\"]/g, (character) => ({
    "<": "&lt;",
    ">": "&gt;",
    "&": "&amp;",
    "'": "&apos;",
    '"': "&quot;",
  })[character]);
}

function escapeHtml(value) {
  return value.replace(/[&<>"']/g, (character) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  })[character]);
}
