import { useEffect, useState } from "react";
import { ArrowUpRight } from "lucide-react";

type ReleaseManifest = {
  built_utc?: string;
  selected_modeling_year?: number;
  counts?: { searchable_census_places?: number; supported_model_places?: number; monitor_sites_selected_year?: number; monitor_site_years?: number; population_covered?: number };
  annual_monitor_audit?: Record<string, { unique_spatial_site_years?: number }>;
  source_audit?: { facility_records_with_coordinates?: number; inventory_year?: number };
  dataset_sources?: Record<string, { url?: string; vintage?: number; period?: string }>;
};

const fmt = (value: number | undefined) => value == null || !Number.isFinite(value) ? "Unavailable" : value.toLocaleString("en-US");

export default function CoverageEvidence() {
  const [manifest, setManifest] = useState<ReleaseManifest | null>(null);
  const [unavailable, setUnavailable] = useState(false);
  useEffect(() => {
    const controller = new AbortController();
    fetch("/api/national/manifest", { signal: controller.signal })
      .then((r) => { if (!r.ok) throw new Error("Release unavailable"); return r.json() as Promise<ReleaseManifest>; })
      .then(setManifest)
      .catch((error: unknown) => { if (error instanceof DOMException && error.name === "AbortError") return; setUnavailable(true); });
    return () => controller.abort();
  }, []);
  const c = manifest?.counts;
  const years = Object.keys(manifest?.annual_monitor_audit ?? {}).map(Number).filter(Number.isFinite).sort((a,b)=>a-b);
  const siteYears = years.reduce((sum, y) => sum + (manifest?.annual_monitor_audit?.[String(y)]?.unique_spatial_site_years ?? 0), 0);
  const source = (key: string) => manifest?.dataset_sources?.[key]?.url;
  const status = !manifest ? unavailable ? "Unavailable" : "Loading release" : "Published data release";
  const fact = (value: number | undefined, label: string, date: string, href?: string) => <article className="coverage-stat" key={label}>
    <strong>{fmt(value)}</strong><span>{label}</span><small>{date}</small>
    {href && <a href={href} target={href.startsWith("/") ? undefined : "_blank"} rel={href.startsWith("/") ? undefined : "noreferrer"}>Source record <ArrowUpRight size={13} aria-hidden="true" /></a>}
  </article>;
  return <section className="coverage-evidence" aria-labelledby="coverage-heading">
    <div className="coverage-heading"><p className="kicker">What the release contains</p><h2 id="coverage-heading">Coverage you can check.</h2><p>Counts come from release metadata. Each evidence layer has its own source, unit, and date.</p></div>
    <div className="coverage-stat-grid" aria-busy={!manifest && !unavailable}>
      {fact(c?.supported_model_places, "Census places with a supported 2024 estimate", "2024 Gazetteer points", "/explore")}
      {fact(c?.monitor_sites_selected_year, "eligible EPA monitor sites", `${manifest?.selected_modeling_year ?? "2024"} annual summaries`, source("EPA AQS annual PM2.5 monitor summaries"))}
    </div>
    <details className="coverage-detail"><summary>Open the full coverage accounting</summary><div className="coverage-detail-content"><p><b>{fmt(c?.searchable_census_places)}</b> searchable Census places · <b>{fmt(siteYears || c?.monitor_site_years)}</b> monitor site-years in the annual archive · <b>{fmt(manifest?.source_audit?.facility_records_with_coordinates)}</b> coordinate-bearing EPA inventory records ({manifest?.source_audit?.inventory_year ?? "2023"}).</p><p>{fmt(c?.population_covered)} is the summed Census population for modeled places, not users or people reached. <a href="/explore">Review release methods and limitations <ArrowUpRight size={12} /></a></p></div></details>
    <p className="coverage-release">{manifest?.built_utc ? `Release built ${new Date(manifest.built_utc).toLocaleDateString("en-US", { dateStyle: "medium", timeZone: "UTC" })} · ${manifest.selected_modeling_year ?? ""} estimates` : status}</p>
  </section>;
}
