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

const llms = `# UPWIND\n\n> UPWIND is an interactive national map and exploration tool for historical U.S. fine particulate matter (PM2.5) air pollution across Census places.\n\n## Public pages\n\n- [National Explorer](${absolute("/")}): Search places and explore historical evidence layers.\n- [Overview](${absolute("/landing")}): Project overview and features.\n- [Methodology](${absolute("/methodology")}): Data sources, interpolation methods, and validation.\n- [About](${absolute("/about")}): Project background and scope.\n- [Local setup](${absolute("/local")}): Run the project locally on your machine.\n\n## Evidence layers\n\n- Place estimates: Historical annual PM2.5 concentrations mapped to 31,000+ U.S. Census places using nearest active monitor interpolation.\n- Monitor measurements: Historical annual summaries from physical EPA AQS reference monitors.\n- Emissions inventory: Permitted industrial facility emissions from the EPA National Emissions Inventory (NEI).\n\n## Notes\n\nUPWIND is designed for community exploration and retrospective analysis. It does not provide real-time air quality feeds or emergency alerts.\n\n## References\n\n- [Full context](${absolute("/llms-full.txt")})\n- [Sitemap](${absolute("/sitemap.xml")})\n`;

const llmsFull = `# UPWIND Documentation\n\n${isFallback ? "Local development build." : `Configured origin: ${siteUrl}.`}\n\n## Overview\n\nUPWIND is an open-source React and FastAPI web application for exploring historical U.S. air-quality data across Census places, EPA monitoring stations, and industrial emissions inventories.\n\n## Routes\n\n${routes.map(({ path, title, description }) => `- ${absolute(path)} — ${title}: ${description}`).join("\n")}\n\nThe /workspace route is a local research workflow and is excluded from the public sitemap.\n\n## Dataset Coverage\n\n- 32,333 searchable Census places (31,523 with supported 2024 estimates)\n- 894 active EPA AQS PM2.5 monitoring sites (2024)\n- 76,404 mapped EPA NEI industrial facilities (2023)\n\n## Scope\n\nEstimates reflect historical annual values assigned from active federal monitoring stations. Proximity to an industrial facility does not demonstrate causation or local exposure.\n`;

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
