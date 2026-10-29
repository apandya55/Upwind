import { useEffect, useState } from "react";

type ReleaseManifest = {
  built_utc?: string;
  selected_modeling_year?: number;
  counts?: { searchable_census_places?: number; supported_model_places?: number; monitor_sites_selected_year?: number };
};

const fmt = (value: number | undefined) => value == null || !Number.isFinite(value) ? "—" : value.toLocaleString("en-US");
const apiBase = import.meta.env.VITE_API_BASE_URL?.trim().replace(/\/$/, "") || "";

export default function CoverageEvidence() {
  const [manifest, setManifest] = useState<ReleaseManifest | null>(null);
  const [unavailable, setUnavailable] = useState(false);
  useEffect(() => {
    const controller = new AbortController();
    fetch(`${apiBase}/api/national/manifest`, { signal: controller.signal })
      .then((r) => { if (!r.ok) throw new Error("Release unavailable"); return r.json() as Promise<ReleaseManifest>; })
      .then(setManifest)
      .catch((error: unknown) => { if (error instanceof DOMException && error.name === "AbortError") return; setUnavailable(true); });
    return () => controller.abort();
  }, []);
  const counts = manifest?.counts;
  const year = manifest?.selected_modeling_year ?? "2024";
  return <section className="coverage-section" aria-labelledby="coverage-heading">
    <div className="landing-shell">
      <div className="coverage-intro"><div><p className="landing-eyebrow">Release coverage</p><h2 id="coverage-heading">Evidence with a defined scope.</h2></div><p>Coverage describes what is present in this release. Estimates, measurements, and inventory records remain distinct evidence.</p></div>
      <div className="coverage-stat-grid" aria-busy={!manifest && !unavailable}>
        <article className="coverage-stat"><strong>{fmt(counts?.searchable_census_places)}</strong><h3>Searchable places</h3><p>Find Census place points across the published U.S. gazetteer; a searchable place may not have a supported estimate.</p><small>2024 Census Gazetteer place points</small></article>
        <article className="coverage-stat"><strong>{fmt(counts?.supported_model_places)}</strong><h3>Supported estimates</h3><p>Places with a historical annual PM2.5 estimate under the release’s geographic and monitor-distance support rules.</p><small>{year} · estimates at place points</small></article>
        <article className="coverage-stat"><strong>{fmt(counts?.monitor_sites_selected_year)}</strong><h3>Monitor sites</h3><p>Eligible physical EPA sites with annual summaries for comparison. These are measurements at stations.</p><small>{year} · EPA AQS annual summaries</small></article>
        <article className="coverage-stat"><strong>3</strong><h3>Evidence layers</h3><p>Estimates, monitor measurements, and nearby emissions inventory records answer different questions; proximity is not attribution.</p><small>Separate units, sources, and limitations</small></article>
      </div>
      <p className="coverage-status">{manifest?.built_utc ? `Release metadata built ${new Date(manifest.built_utc).toLocaleDateString("en-US", { dateStyle: "medium", timeZone: "UTC" })}.` : unavailable ? "Release coverage is temporarily unavailable." : "Loading published release coverage…"} <a href="/methodology">Method and data sources <span aria-hidden="true">↗</span></a></p>
    </div>
  </section>;
}
