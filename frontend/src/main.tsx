import React from "react";
import ReactDOM from "react-dom/client";
import { lazy, Suspense } from "react";
import LoadingScreen from "./LoadingScreen";
const EXPLORER_BUILD = import.meta.env.VITE_APP_SURFACE === "explorer";
const App = EXPLORER_BUILD ? lazy(() => import("./LocalOnlyWorkspace")) : lazy(() => import("./App"));
const Landing = lazy(() => import("./Landing"));
const LocalPage = lazy(() => import("./LocalPage"));
const MethodologyPage = lazy(() => import("./MethodologyPage"));
const AboutPage = lazy(() => import("./AboutPage"));
const NationalExplorer = lazy(() => import("./national/NationalExplorer"));
import "./style.css";
import "./atlas-system.css";

const EXPLORER_METADATA = {
  title: "UPWIND National Explorer | Historical air quality evidence",
  description: "Explore historical PM2.5 estimates, EPA monitor measurements, and emissions inventory records across U.S. places in the UPWIND public atlas.",
  type: "website",
};

const SEO_ROUTES: Record<string, { title: string; description: string; type: string; canonicalPath?: string }> = {
  "/": EXPLORER_METADATA,
  "/landing": {
    title: "Explore America’s air quality | UPWIND",
    description: "UPWIND connects historical PM2.5 estimates, EPA monitor measurements, and emissions records by place.",
    type: "website",
  },
  "/methodology": {
    title: "Methodology and data sources | UPWIND",
    description: "Read how UPWIND assigns annual PM2.5 evidence to place points and how to interpret monitors, inventories, and limits.",
    type: "article",
  },
  "/method": {
    title: "Methodology and data sources | UPWIND",
    description: "Read how UPWIND assigns annual PM2.5 evidence to place points and how to interpret monitors, inventories, and limits.",
    type: "article",
    canonicalPath: "/methodology",
  },
  "/about": {
    title: "About the UPWIND air atlas",
    description: "Learn what the UPWIND public air atlas contains, how its evidence layers differ, and where its limits apply.",
    type: "article",
  },
  "/local": {
    title: "Run UPWIND locally | Developer guide",
    description: "Use the UPWIND source, public datasets, and documented commands to run the air atlas locally.",
    type: "article",
  },
  "/workspace": {
    title: "UPWIND local investigation workspace",
    description: "Inspect local air-quality measurements and documented evidence in the UPWIND research workspace.",
    type: "website",
  },
  "/explore": {
    ...EXPLORER_METADATA,
    canonicalPath: "/",
  },
  "/national": {
    ...EXPLORER_METADATA,
    canonicalPath: "/",
  },
};

function setMeta(name: string, content: string, property = false) {
  const selector = property ? `meta[property="${name}"]` : `meta[name="${name}"]`;
  let element = document.head.querySelector<HTMLMetaElement>(selector);
  if (!element) {
    element = document.createElement("meta");
    if (property) element.setAttribute("property", name);
    else element.setAttribute("name", name);
    document.head.appendChild(element);
  }
  element.content = content;
}

function updateDocumentMetadata() {
  const route = SEO_ROUTES[location.pathname] || SEO_ROUTES["/"];
  const configuredOrigin = import.meta.env.VITE_SITE_URL?.trim();
  let origin = location.origin;
  if (configuredOrigin) {
    try {
      origin = new URL(configuredOrigin).origin;
    } catch {
      // Keep local metadata usable while the deployment configuration is corrected.
    }
  }
  const canonicalPath = route.canonicalPath || (SEO_ROUTES[location.pathname] ? location.pathname : "/");
  const canonical = new URL(canonicalPath || "/", `${origin}/`).toString();
  const shareImage = new URL("/landing/quality-recovery/overview.webp", `${origin}/`).toString();
  setMeta("robots", location.pathname === "/workspace" ? "noindex,nofollow" : "index,follow");
  document.title = route.title;
  setMeta("description", route.description);
  setMeta("og:title", route.title, true);
  setMeta("og:description", route.description, true);
  setMeta("og:url", canonical, true);
  setMeta("og:type", route.type, true);
  setMeta("og:site_name", "UPWIND", true);
  setMeta("og:locale", "en_US", true);
  setMeta("og:image", shareImage, true);
  setMeta("og:image:alt", "UPWIND National Explorer map preview", true);
  setMeta("twitter:card", "summary_large_image");
  setMeta("twitter:title", route.title);
  setMeta("twitter:description", route.description);
  setMeta("twitter:image", shareImage);
  let link = document.head.querySelector<HTMLLinkElement>('link[rel="canonical"]');
  if (!link) {
    link = document.createElement("link");
    link.rel = "canonical";
    document.head.appendChild(link);
  }
  link.href = canonical;
  const schema = {
    "@context": "https://schema.org",
    "@graph": [
      { "@type": "WebSite", "@id": `${origin}/#website`, url: origin, name: "UPWIND", description: "A public atlas for historical U.S. air-quality evidence." },
      { "@type": "SoftwareApplication", "@id": `${origin}/#application`, name: "UPWIND National Explorer", applicationCategory: "DataVisualization", operatingSystem: "Web", url: origin, description: "A public map for comparing historical PM2.5 estimates, EPA monitor measurements, and emissions inventory records." },
    ],
  };
  let script = document.head.querySelector<HTMLScriptElement>('script[data-upwind-schema]');
  if (!script) {
    script = document.createElement("script");
    script.type = "application/ld+json";
    script.dataset.upwindSchema = "true";
    document.head.appendChild(script);
  }
  script.textContent = JSON.stringify(schema);
}

updateDocumentMetadata();
ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <Suspense
      fallback={
        <LoadingScreen
          fullScreen={true}
          message="Loading UPWIND…"
          submessage="Preparing public atmospheric atlas and national geospatial layers"
        />
      }
    >
      {EXPLORER_BUILD && location.pathname === "/workspace" ? (
        <App />
      ) : !EXPLORER_BUILD && location.pathname === "/workspace" ? (
        <App />
      ) : location.pathname === "/local" ? (
        <LocalPage />
      ) : location.pathname === "/methodology" || location.pathname === "/method" ? (
        <MethodologyPage />
      ) : location.pathname === "/about" ? (
        <AboutPage />
      ) : location.pathname === "/landing" ? (
        <Landing />
      ) : (
        <NationalExplorer />
      )}
    </Suspense>
  </React.StrictMode>,
);
