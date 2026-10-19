import { useEffect, useRef, useState } from "react";
import type { FormEvent, ReactNode } from "react";
import {
  Wind,
  FolderOpen,
  Plus,
  ArrowUpRight,
  ArrowRight,
  Upload,
  Download,
  Check,
  ChevronDown,
  Activity,
  MapPin,
  FlaskConical,
  BookOpen,
  FileText,
  Settings2,
  X,
  Info,
  Save,
  RotateCcw,
  Play,
  LoaderCircle,
  AlertTriangle,
  Eye,
  MessageSquare,
} from "lucide-react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts";
import StudyMap from "./Map";
import { api, emptyInvestigation } from "./types";
import type {
  Investigation,
  Result,
  Site,
  Point,
  Measurement,
  Weather,
  ImportRecord,
} from "./types";

type Dialog = "define" | "import" | "library" | "help" | "exports" | null;
type Saved = { id: string; name: string; updated: string };
const utc = (s: string) =>
  new Date(s).toLocaleTimeString("en-GB", {
    timeZone: "UTC",
    hour: "2-digit",
    minute: "2-digit",
  });

function EvidenceDetails({ result }: { result: Result }) {
  const region = result.source_region90;
  const availableChecks = result.diagnostics?.held_out_sensor.filter(
    (check) => !check.unavailable && check.rmse_ug_m3 !== undefined,
  );
  return (
    <div className="limits" aria-label="Scientific evidence details">
      {result.observability && (
        <>
          <h3>Can these measurements distinguish locations?</h3>
          <p>
            {(
              100 * result.observability.profile_compatible_domain_fraction
            ).toFixed(1)}
            % of the supported search area has similarly fitting explanations
            after adjusting release strength and background. This diagnostic is
            not a confidence region or proof of a source.
          </p>
          {result.observability.profile_compatible_domain_fraction > 0.7 && (
            <p className="inline-warning">
              Repeating the same layout and wind can leave the ambiguity
              unresolved. Compare accessible sites and independently steady wind
              periods before collecting more readings.
            </p>
          )}
        </>
      )}
      {!!result.study_window_count && result.study_window_count > 1 && (
        <p>
          Campaign: {result.study_window_count} separately steady periods, with
          a shared fixed source and constant release assumption. Background can
          differ between periods.
        </p>
      )}
      {!!result.diagnostics?.held_out_window?.length && (
        <details>
          <summary>Cross-period prediction checks</summary>
          <p>
            Each check withholds a period's concentrations and compares spatial
            contrasts using its recorded weather. This tests the shared-release
            model; it is not a future forecast.
          </p>
          {result.diagnostics.held_out_window.map((check) => (
            <p key={check.window_id}>
              {check.window_id}:{" "}
              {check.unavailable
                ? "Unavailable: " + check.unavailable
                : check.flagged
                  ? "Predictive mismatch flagged"
                  : "No mismatch detected; physical correctness is not established"}
            </p>
          ))}
        </details>
      )}
      {result.evidence_status && (
        <>
          <h3>What the model can distinguish</h3>
          <p>
            <b>Identifiability: </b>
            {result.evidence_status === "source_supported"
              ? "A single-source explanation is supported within this model."
              : result.evidence_status === "model_mismatch"
                ? "The source explanation is not established; predictive checks flag a mismatch."
                : "The available evidence does not identify a source reliably."}
          </p>
          {result.source_probability != null && (
            <p className="score-note">
              Conditional single-source model weight:{" "}
              {result.source_probability.toFixed(3)}; background-only model
              weight: {(1 - result.source_probability).toFixed(3)}. These
              compare the implemented explanations. A background-only result
              does not prove the absence of pollution or other sources.
            </p>
          )}
          <p className="score-note">
            <b>Model adequacy: </b>
            {result.diagnostics?.predictive_warning
              ? "Held-out sensor predictions raise a warning."
              : availableChecks?.length
                ? "The held-out sensor check did not raise a warning; this cannot establish that the physical model is correct."
                : "No held-out sensor predictive check is available."}
          </p>
          <p className="score-note">
            <b>Empirical reliability: </b>Synthetic evaluation only. Model
            weights, regions, and evidence labels are not calibrated for field
            attribution. Evidence-label thresholds are interpretive rules, not
            validated accuracy guarantees.
          </p>
        </>
      )}
      {region && (
        <p className="score-note">
          Conditional 90% model region: {(region.area_m2 / 1e6).toFixed(3)} km²
          within a {(region.domain_area_m2 / 1e6).toFixed(3)} km² domain;
          approximately {region.resolution_m.toFixed(0)} m cells.{" "}
          {region.meaning} Domain: {region.support}. This describes probability
          under the single-source model, not measured geographic coverage or
          responsibility. The search assumes the source lies inside the declared
          rectangle; a boundary result cannot establish that the search domain
          contains it. Cell size targets 20 m and is capped at 24 cells per
          side, so larger domains have coarser resolution.
          {region.domain_area_m2 === 0 &&
            " These anchors form a degenerate rectangle: only discrete hypotheses are compared and no geographic region area is defined."}
        </p>
      )}
      {result.rows_loaded !== undefined && (
        <p className="score-note">
          Observations: {result.rows_loaded.toLocaleString()} loaded ·{" "}
          {(result.rows_excluded ?? 0).toLocaleString()} excluded ·{" "}
          {(result.rows_input ?? result.rows_used ?? 0).toLocaleString()} usable
          · {(result.rows_used ?? 0).toLocaleString()} fitted.
          {result.selection && (
            <>
              {" "}
              Selection: {result.selection.method}; limit{" "}
              {result.selection.limit}, seed {result.selection.seed}. All
              original readings remain retained.
            </>
          )}
        </p>
      )}
      {result.diagnostics && (
        <details>
          <summary>Held-out sensor prediction details</summary>
          <p className="score-note">{result.diagnostics.method}</p>
          {result.diagnostics.held_out_sensor.map((check) => (
            <p className="score-note" key={check.sensor_id}>
              {check.sensor_id}: {check.rows} held-out rows;{" "}
              {check.unavailable || check.rmse_ug_m3 === undefined ? (
                <>
                  check unavailable:{" "}
                  {check.unavailable || "no prediction returned"}.
                </>
              ) : (
                <>
                  RMSE {check.rmse_ug_m3.toFixed(2)} µg/m³; conditional 90%
                  prediction interval coverage{" "}
                  {check.coverage90 === undefined
                    ? "unavailable"
                    : `${(check.coverage90 * 100).toFixed(0)}%`}
                  ; mean negative log predictive density{" "}
                  {check.mean_nlpd?.toFixed(3) ?? "unavailable"}.
                  {check.flagged ? " Warning raised." : " No warning raised."}
                </>
              )}
            </p>
          ))}
        </details>
      )}
    </div>
  );
}

function Modal({
  title,
  onClose,
  children,
}: {
  title: string;
  onClose: () => void;
  children: ReactNode;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    ref.current?.showModal();
    const old = document.activeElement as HTMLElement;
    return () => old?.focus();
  }, []);
  return (
    <dialog
      ref={ref}
      onCancel={onClose}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="dialog-head">
        <h2>{title}</h2>
        <button
          className="icon-button"
          aria-label="Close dialog"
          onClick={onClose}
        >
          <X size={20} />
        </button>
      </div>
      {children}
    </dialog>
  );
}

export default function App() {
  const [inv, setInv] = useState<Investigation | null>(null),
    [error, setError] = useState(""),
    [toast, setToast] = useState(""),
    [dialog, setDialog] = useState<Dialog>(null),
    [dirty, setDirty] = useState(false);
  const [tab, setTab] = useState("Plan"),
    [bottom, setBottom] = useState("Timeline"),
    [busy, setBusy] = useState(false),
    [saved, setSaved] = useState<Saved[]>([]);
  const [selected, setSelected] = useState(""),
    [mode, setMode] = useState(""),
    [newPoint, setNewPoint] = useState<Point | null>(null),
    [time, setTime] = useState(""),
    [planIndex, setPlanIndex] = useState(0),
    [sensorFilter, setSensorFilter] = useState("all");
  const [importKind, setImportKind] = useState<"measurements" | "weather">(
      "measurements",
    ),
    [csv, setCsv] = useState(""),
    [filename, setFilename] = useState(""),
    [zone, setZone] = useState(""),
    [mapping, setMapping] = useState<Record<string, string>>({}),
    [importSummary, setImportSummary] = useState<ImportRecord | null>(null);
  const [units, setUnits] = useState("ug/m3"),
    [fileError, setFileError] = useState("");
  const abort = useRef<AbortController | null>(null),
    analysisRevision = useRef(0),
    fileRef = useRef<HTMLInputElement>(null),
    jsonRef = useRef<HTMLInputElement>(null);
  const notify = (s: string) => {
    setToast(s);
    setTimeout(() => setToast(""), 4500);
  };
  const reportError = (e: unknown) =>
    setError(e instanceof Error ? e.message : String(e));
  useEffect(() => {
    api<Investigation>("/demo")
      .then((data) => setInv(data))
      .catch(reportError);
  }, []);
  useEffect(() => {
    api<Saved[]>("/investigations").then(setSaved).catch(reportError);
  }, [dialog]);
  const edit = (patch: Partial<Investigation>, invalidate = true) => {
    analysisRevision.current++;
    setInv((prev) =>
      prev
        ? {
            ...prev,
            ...patch,
            plan_history:
              invalidate && prev.result
                ? [prev.result, ...prev.plan_history].slice(0, 20)
                : (patch.plan_history ?? prev.plan_history),
            result: invalidate ? null : (patch.result ?? prev.result),
          }
        : prev,
    );
    setDirty(true);
  };
  const load = (data: Investigation) => {
    analysisRevision.current++;
    abort.current?.abort();
    setBusy(false);
    setInv(data);
    setTime("");
    setPlanIndex(0);
    setSelected("");
    setMode("");
    setDirty(false);
    setError("");
    setDialog(null);
    setImportSummary(null);
  };
  async function saveCurrent() {
    if (!inv) return;
    const data = await api<Investigation>("/investigations", inv);
    setInv(data);
    setDirty(false);
    setSaved(await api<Saved[]>("/investigations"));
    return data;
  }
  async function run() {
    if (!inv) return;
    setError("");
    setBusy(true);
    abort.current = new AbortController();
    const revision = analysisRevision.current;
    try {
      const result = await api<Result>("/analyze", inv, abort.current.signal);
      if (revision !== analysisRevision.current) {
        notify(
          "Inputs changed; run again to analyze the current investigation.",
        );
        return;
      }
      setInv((prev) =>
        prev
          ? {
              ...prev,
              result,
              plan_history: [
                ...(prev.result ? [prev.result] : []),
                ...prev.plan_history,
              ].slice(0, 20),
            }
          : prev,
      );
      setDirty(true);
      setPlanIndex(0);
      setTab("Plan");
      notify(
        result.status === "ok"
          ? "Plan comparison complete"
          : "Analysis completed with a constraint or data limitation",
      );
    } catch (e) {
      if ((e as Error).name !== "AbortError") reportError(e);
    } finally {
      setBusy(false);
    }
  }
  async function exportFile(type: "export" | "report" | "measurements.csv") {
    try {
      const data = await saveCurrent();
      if (!data) return;
      const res = await fetch(`/api/investigations/${data.id}/${type}`);
      if (!res.ok) throw new Error("Export failed");
      const url = URL.createObjectURL(await res.blob()),
        a = document.createElement("a");
      a.href = url;
      a.download =
        type === "export"
          ? "upwind-investigation.json"
          : type === "report"
            ? "upwind-evidence.html"
            : "upwind-measurements.csv";
      a.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
      notify(
        "Export saved. Review privacy and evidence limits before sharing.",
      );
    } catch (e) {
      reportError(e);
    }
  }
  async function importCSV() {
    if (!inv) return;
    setFileError("");
    setBusy(true);
    try {
      const data = await api<{
        rows: Measurement[] | Weather[];
        record: ImportRecord;
      }>("/import/csv", {
        csv,
        filename,
        kind: importKind,
        timezone: zone,
        units,
        mapping,
      });
      const sites = [...inv.sites];
      const measurements = [...inv.measurements];
      const weather = [...inv.weather];
      if (importKind === "measurements") {
        const existing = new Set(
          measurements.map((m) => m.sensor_id + "|" + m.timestamp),
        );
        for (const row of data.rows as Measurement[]) {
          if (
            existing.has(row.sensor_id + "|" + row.timestamp) &&
            !row.flags.includes("duplicate")
          )
            row.flags.push("duplicate");
          existing.add(row.sensor_id + "|" + row.timestamp);
          measurements.push(row);
          if (!sites.some((s) => s.id === row.sensor_id))
            sites.push({
              id: row.sensor_id,
              name: row.sensor_id,
              latitude: row.latitude,
              longitude: row.longitude,
              kind: "sensor",
              allowed: false,
              power: false,
              access: false,
              cost: 0,
              windows: ["steady-window"],
            });
        }
      } else weather.push(...(data.rows as Weather[]));
      let area = inv.area;
      if (!inv.measurements.length && data.rows.length) {
        const pts = data.rows;
        const lats = pts.map((p) => p.latitude),
          lons = pts.map((p) => p.longitude);
        area = [
          Math.max(-180, Math.min(...lons) - 0.008),
          Math.max(-85, Math.min(...lats) - 0.006),
          Math.min(180, Math.max(...lons) + 0.008),
          Math.min(85, Math.max(...lats) + 0.006),
        ];
      }
      edit({
        measurements,
        weather,
        sites,
        area,
        synthetic:
          inv.synthetic || data.rows.some((r) => r.origin === "synthetic"),
        imports: [...inv.imports, data.record],
      });
      setImportSummary(data.record);
      notify(
        `${data.record.summary.accepted} rows imported; raw CSV preserved`,
      );
    } catch (e) {
      setFileError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  function addPoint(ev: FormEvent<HTMLFormElement>) {
    ev.preventDefault();
    if (!inv || !newPoint) return;
    const form = new FormData(ev.currentTarget),
      latitude = Number(form.get("latitude")),
      longitude = Number(form.get("longitude"));
    const p = { latitude, longitude };
    if (mode === "source") {
      edit({ source_locations: [...inv.source_locations, p] });
    } else if (mode === "observation") {
      edit({
        observations: [
          ...inv.observations,
          {
            ...p,
            timestamp: new Date(String(form.get("timestamp"))).toISOString(),
            note: String(form.get("name")),
            approximate: true,
          },
        ],
      });
    } else {
      const id = String(form.get("id"));
      if (inv.sites.some((s) => s.id === id)) {
        setFileError("That site ID already exists.");
        return;
      }
      edit({
        sites: [
          ...inv.sites,
          {
            ...p,
            id,
            name: String(form.get("name")),
            kind: mode as "candidate" | "sensor",
            cost: Number(form.get("cost")),
            allowed: form.has("allowed"),
            power: form.has("power"),
            access: form.has("access"),
            windows: form.has("window") ? ["steady-window"] : [],
          },
        ],
      });
    }
    setNewPoint(null);
    setMode("");
    setFileError("");
    notify("Added to investigation");
  }
  if (!inv)
    return (
      <div className="splash">
        <Wind size={42} />
        <h1>UPWIND</h1>
        <p>{error || "Opening the investigation workspace…"}</p>
        {error && (
          <button onClick={() => location.reload()}>Retry connection</button>
        )}
      </div>
    );
  const result = inv.result,
    plan = result?.plans[planIndex],
    site = inv.sites.find((s) => s.id === selected),
    times = [...new Set(inv.measurements.map((m) => m.timestamp))].sort();
  const filtered = inv.measurements.filter(
    (m) =>
      (!time || m.timestamp === time) &&
      (sensorFilter === "all" || m.sensor_id === sensorFilter),
  );
  const chart = times.map((timestamp) => {
    const rows = inv.measurements.filter(
      (m) =>
        m.timestamp === timestamp &&
        (sensorFilter === "all" || m.sensor_id === sensorFilter),
    );
    return {
      timestamp,
      time: utc(timestamp),
      mean: rows.length
        ? rows.reduce((s, m) => s + m.pm25_ug_m3, 0) / rows.length
        : null,
    };
  });
  const eligible = inv.sites.filter(
    (s) =>
      s.kind === "candidate" &&
      s.allowed &&
      s.power &&
      s.access &&
      s.windows.includes(inv.settings.window),
  );
  const required =
    importKind === "measurements"
      ? ["sensor_id", "timestamp", "latitude", "longitude", "pm25_ug_m3"]
      : [
          "timestamp",
          "latitude",
          "longitude",
          "wind_speed_m_s",
          "wind_from_deg",
        ];
  const headers =
    csv
      .split(/\r?\n/)[0]
      ?.replace(/^\uFEFF/, "")
      .split(",")
      .map((h) => h.trim().replace(/^"|"$/g, "")) || [];
  const updateSite = (patch: Partial<Site>) =>
    edit({
      sites: inv.sites.map((s) => (s.id === selected ? { ...s, ...patch } : s)),
    });
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <a className="brand" href="#" onClick={(e) => e.preventDefault()}>
          <span className="brand-mark">
            <Wind size={26} />
          </span>
          <span>
            UPWIND<small>COMMUNITY AIR INTELLIGENCE</small>
          </span>
        </a>
        <div className="workspace-label">
          <span className="online-dot" />
          LOCAL WORKSPACE<span className="version">v0.1</span>
        </div>
        <button
          className="investigation-switch"
          onClick={() => setDialog("library")}
        >
          <span className="folder-icon">
            <FolderOpen size={17} />
          </span>
          <span>
            <small>INVESTIGATION</small>
            {inv.name}
          </span>
          <ChevronDown size={14} />
        </button>
        <nav>
          <div className="nav-label">WORKSPACE</div>
          <button
            className="nav-item active"
            onClick={() => {
              setTab("Plan");
              setDialog(null);
            }}
          >
            <Activity size={18} />
            Investigation<span className="nav-count">01</span>
          </button>
          <button
            className="nav-item"
            onClick={() => {
              setTab("Sites");
              setSelected(inv.sites[0]?.id || "");
            }}
          >
            <MapPin size={18} />
            Monitoring sites
            <span className="nav-count">{inv.sites.length}</span>
          </button>
          <button className="nav-item" onClick={() => setTab("Scenarios")}>
            <FlaskConical size={18} />
            Source scenarios
            <span className="experimental-dot" />
          </button>
          <button className="nav-item" onClick={() => setDialog("exports")}>
            <FileText size={18} />
            Evidence report
            <ArrowUpRight size={14} />
          </button>
          <div className="nav-label second">YOUR INVESTIGATIONS</div>
          {saved.slice(0, 4).map((s) => (
            <button
              key={s.id}
              className="saved-item"
              onClick={() =>
                api<Investigation>("/investigations/" + s.id)
                  .then(load)
                  .catch(reportError)
              }
            >
              <span className="saved-dot" />
              {s.name}
            </button>
          ))}
          <button
            className="new-investigation"
            onClick={() => {
              load(emptyInvestigation());
              setDirty(true);
              setDialog("define");
            }}
          >
            <Plus size={15} />
            New investigation
          </button>
        </nav>
        <div className="sidebar-bottom">
          <div className="evidence-note">
            <FlaskConical size={17} />
            <strong>Know what the data can say.</strong>
            <p>Measurements are evidence. Source scenarios are hypotheses.</p>
            <button onClick={() => setDialog("help")}>
              Read the scientific limits
              <ArrowRight size={14} />
            </button>
          </div>
          <button className="nav-item" onClick={() => setDialog("help")}>
            <BookOpen size={17} />
            Field guide & methods
          </button>
          <div className="local-foot">
            <span className="online-dot" />
            Runs locally. Your data stays here.
          </div>
        </div>
      </aside>
      <main>
        <header className="topbar">
          <div className="breadcrumb">
            Workspace<span>/</span>
            <b>Investigation</b>
          </div>
          <div className="top-actions">
            <span className="save-state">
              {dirty
                ? "Unsaved changes"
                : inv.id
                  ? "Saved locally"
                  : "Bundled example"}
            </span>
            <button
              className="button secondary"
              onClick={() => {
                setDialog("import");
                setFileError("");
              }}
            >
              <Upload size={15} />
              Import data
            </button>
            <button
              className="button"
              onClick={() =>
                saveCurrent()
                  .then(() => notify("Investigation saved locally"))
                  .catch(reportError)
              }
            >
              <Save size={15} />
              Save investigation
            </button>
          </div>
        </header>
        <div className="page-body">
          <div className="page-title">
            <div>
              <div className="eyebrow">
                INVESTIGATION /{" "}
                {inv.synthetic
                  ? "SYNTHETIC DEMONSTRATION"
                  : "COMMUNITY MONITORING"}
              </div>
              <h1>
                {inv.name}
                <button
                  className="edit-title"
                  aria-label="Edit investigation"
                  onClick={() => setDialog("define")}
                >
                  <Settings2 size={17} />
                </button>
              </h1>
              <p>{inv.objective}</p>
            </div>
            <button
              className="text-button"
              onClick={() => setDialog("exports")}
            >
              Export evidence
              <ArrowUpRight size={16} />
            </button>
          </div>
          {error && (
            <div role="alert" className="error-banner">
              <AlertTriangle size={17} />
              <span>{error}</span>
              <button aria-label="Dismiss error" onClick={() => setError("")}>
                <X size={16} />
              </button>
            </div>
          )}
          <div className={"status-strip " + (!inv.synthetic ? "real" : "")}>
            <Info size={16} />
            <span>
              <b>
                {inv.synthetic ? "Synthetic example." : "User investigation."}
              </b>{" "}
              {inv.synthetic
                ? "Contains simulated inputs; row origins distinguish imported and synthetic data. No field accuracy is established."
                : "Verify instrument quality and local conditions. Experimental scenarios do not establish source responsibility."}
            </span>
            <button onClick={() => setDialog("help")}>
              Evidence levels
              <ArrowUpRight size={13} />
            </button>
          </div>
          {result?.warnings.some((w) => w.includes("MODEL MISMATCH")) && (
            <div role="alert" className="inline-warning">
              {result.warnings.find((w) => w.includes("MODEL MISMATCH"))}
            </div>
          )}
          {result?.evidence_status &&
            result.evidence_status !== "source_supported" && (
              <div className="inline-warning" role="status">
                <b>Source not identified. </b>
                {result.evidence_status === "model_mismatch"
                  ? "Predictive checks flag a model mismatch. Review competing explanations and measurements before interpreting the map."
                  : "These readings do not sufficiently distinguish a single source from background or alternative locations. The conditional region can remain broad."}
              </div>
            )}
          <div className="overview">
            <div>
              <span className="metric-label">MEASUREMENTS</span>
              <strong>
                {inv.measurements.length.toLocaleString()}
                <small>PM2.5 readings</small>
              </strong>
              <span className="metric-foot">
                {new Set(inv.measurements.map((m) => m.sensor_id)).size}{" "}
                monitors ·{" "}
                {times.length
                  ? new Date(times[0]).toLocaleDateString("en-GB", {
                      timeZone: "UTC",
                      day: "numeric",
                      month: "short",
                      year: "numeric",
                    })
                  : "No readings yet"}
              </span>
            </div>
            <div>
              <span className="metric-label">PERMISSIBLE CANDIDATES</span>
              <strong>
                {eligible.length}
                <small>
                  of {inv.sites.filter((s) => s.kind === "candidate").length}{" "}
                  marked sites
                </small>
              </strong>
              <span className="metric-foot">
                <span className="tiny-check">✓</span>Permission, power & access
                confirmed
              </span>
            </div>
            <div>
              <span className="metric-label">MODEL STATUS</span>
              <strong className="model-metric">
                <span className="amber-dot" />
                {result?.status === "insufficient_data"
                  ? "Insufficient data"
                  : result?.evidence_status === "ambiguous"
                    ? "Source unresolved"
                    : result?.evidence_status === "model_mismatch"
                      ? "Check model fit"
                      : "Experimental"}
                <small>Conditional model comparison</small>
              </strong>
              <span className="metric-foot">
                {inv.weather.length
                  ? `${inv.weather.length} local weather records · assumptions required`
                  : "Weather missing · use spatial coverage"}
              </span>
            </div>
          </div>
          <div className="workspace-grid">
            <div className="explore-column">
              <StudyMap
                inv={inv}
                time={time}
                selected={selected}
                mode={mode}
                onPick={(s) => {
                  setSelected(s.id);
                  setTab("Sites");
                }}
                onAdd={(p) => {
                  setFileError("");
                  setNewPoint(p);
                }}
                onMode={setMode}
                planIndex={planIndex}
              />
              <section className="data-card">
                <div className="data-head">
                  <div className="tabs">
                    {[
                      "Timeline",
                      "Readings",
                      "Data quality",
                      "Observations",
                    ].map((t) => (
                      <button
                        key={t}
                        className={bottom === t ? "selected" : ""}
                        onClick={() => setBottom(t)}
                      >
                        {t}
                        {t === "Data quality" &&
                          inv.imports.some((i) => i.summary.invalid > 0) && (
                            <span className="amber-dot" />
                          )}
                      </button>
                    ))}
                  </div>
                  <select
                    aria-label="Filter monitor"
                    value={sensorFilter}
                    onChange={(e) => setSensorFilter(e.target.value)}
                  >
                    <option value="all">All monitors</option>
                    {[...new Set(inv.measurements.map((m) => m.sensor_id))].map(
                      (id) => (
                        <option key={id}>{id}</option>
                      ),
                    )}
                  </select>
                </div>
                {bottom === "Timeline" && (
                  <>
                    <div className="chart-caption">
                      <span>
                        <i className="line-key" />
                        Observed PM2.5{" "}
                        <small>· arithmetic mean of selected monitors</small>
                      </span>
                      <span>µg/m³ · UTC</span>
                    </div>
                    {chart.length ? (
                      <div className="timeline">
                        <ResponsiveContainer width="100%" height={150}>
                          <AreaChart
                            data={chart}
                            margin={{
                              top: 10,
                              right: 20,
                              bottom: 0,
                              left: -22,
                            }}
                            onClick={(e) => {
                              const i = Number(e?.activeTooltipIndex);
                              if (Number.isInteger(i) && chart[i])
                                setTime(chart[i].timestamp);
                            }}
                          >
                            <defs>
                              <linearGradient
                                id="chartFill"
                                x1="0"
                                y1="0"
                                x2="0"
                                y2="1"
                              >
                                <stop stopColor="#8bd5bc" stopOpacity={0.2} />
                                <stop
                                  offset="1"
                                  stopColor="#8bd5bc"
                                  stopOpacity={0}
                                />
                              </linearGradient>
                            </defs>
                            <CartesianGrid stroke="#23313a" vertical={false} />
                            <XAxis
                              dataKey="time"
                              tick={{ fontSize: 11, fill: "#8b9ca9" }}
                              axisLine={false}
                              tickLine={false}
                            />
                            <YAxis
                              tick={{ fontSize: 11, fill: "#8b9ca9" }}
                              axisLine={false}
                              tickLine={false}
                            />
                            <Tooltip
                              contentStyle={{
                                background: "#14212b",
                                border: "1px solid #3c505e",
                                borderRadius: 8,
                                color: "#dbe6e8",
                              }}
                              formatter={(v) => [
                                Number(v).toFixed(2) + " µg/m³",
                                "Observed mean",
                              ]}
                            />
                            <Area
                              dataKey="mean"
                              type="linear"
                              stroke="#a9dfbd"
                              strokeWidth={2}
                              fill="url(#chartFill)"
                              isAnimationActive={false}
                            />
                          </AreaChart>
                        </ResponsiveContainer>
                      </div>
                    ) : (
                      <div className="empty-state">
                        Import measurements to explore the timeline.
                      </div>
                    )}
                    <div className="time-control">
                      <span>
                        {time ? utc(time) + " UTC" : "All observations"}
                      </span>
                      <input
                        aria-label="Timeline time"
                        type="range"
                        min="0"
                        max={Math.max(0, times.length - 1)}
                        value={Math.max(0, times.indexOf(time))}
                        disabled={!times.length}
                        onChange={(e) => setTime(times[Number(e.target.value)])}
                      />
                      <button onClick={() => setTime("")}>Show all</button>
                    </div>
                  </>
                )}
                {bottom === "Readings" && (
                  <div className="table-scroll">
                    <table>
                      <thead>
                        <tr>
                          <th>Sensor</th>
                          <th>Time (UTC)</th>
                          <th>PM2.5 µg/m³</th>
                          <th>Quality</th>
                          <th>Origin</th>
                        </tr>
                      </thead>
                      <tbody>
                        {filtered.slice(0, 150).map((m, i) => (
                          <tr key={i}>
                            <td>{m.sensor_id}</td>
                            <td>{utc(m.timestamp)}</td>
                            <td>{m.pm25_ug_m3.toFixed(2)}</td>
                            <td>
                              {m.flags.join(", ") || "No automatic flags"}
                            </td>
                            <td>{m.origin}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                    {!filtered.length && (
                      <p className="empty-state">
                        No readings in this selection.
                      </p>
                    )}
                    <small className="table-note">
                      Showing up to 150 rows. Export CSV includes all{" "}
                      {inv.measurements.length} retained rows.
                    </small>
                  </div>
                )}
                {bottom === "Data quality" && (
                  <div className="quality-list">
                    <p>
                      No smoothing or calibration applied. Missing rows are
                      never invented. Negative, duplicate, and extreme readings
                      are retained but excluded from inference.
                    </p>
                    {inv.synthetic && (
                      <p className="small-label">
                        SYNTHETIC FIXTURE · reproducible seed 42 · simulated
                        instruments
                      </p>
                    )}
                    {inv.imports.map((r, i) => (
                      <article key={i}>
                        <b>{r.filename}</b>
                        <span>
                          {r.kind} · {r.summary.accepted}/{r.summary.total} rows
                          accepted · {r.summary.invalid} invalid ·{" "}
                          {r.summary.flagged} flagged
                        </span>
                        <code>SHA256 {r.sha256}</code>
                        <details>
                          <summary>Issues & transformations</summary>
                          {r.transformations.map((t) => (
                            <p key={t}>{t}</p>
                          ))}
                          {r.summary.issues.map((x) => (
                            <p key={x.line}>
                              Row {x.line}: {x.error}
                            </p>
                          ))}
                        </details>
                      </article>
                    ))}
                    <h4>Instrument notes</h4>
                    <textarea
                      aria-label="Instrument metadata"
                      placeholder="Sensor model, calibration provenance, humidity sensitivity…"
                      value={inv.instruments.notes || ""}
                      onChange={(e) =>
                        edit({
                          instruments: {
                            ...inv.instruments,
                            notes: e.target.value,
                          },
                        })
                      }
                    />
                  </div>
                )}
                {bottom === "Observations" && (
                  <div className="quality-list">
                    <p>
                      Resident accounts are separate from instrument
                      measurements. Use approximate locations and avoid personal
                      details.
                    </p>
                    <button
                      className="button secondary"
                      onClick={() => {
                        setMode("observation");
                        notify("Choose an approximate location on the map.");
                      }}
                    >
                      <Plus size={14} />
                      Add observation
                    </button>
                    {inv.observations.map((o, i) => (
                      <article key={i}>
                        <b>{new Date(o.timestamp).toLocaleString()}</b>
                        <p>{o.note}</p>
                        <small>
                          Approximate location · not a measured pollutant
                          identification
                        </small>
                      </article>
                    ))}
                  </div>
                )}
              </section>
            </div>
            <aside className="result-card">
              <div className="result-head">
                <span className="eyebrow">MEASUREMENT DESIGN</span>
                <div className="tabs">
                  {["Plan", "Scenarios", "Sites"].map((t) => (
                    <button
                      key={t}
                      className={tab === t ? "selected" : ""}
                      onClick={() => setTab(t)}
                    >
                      {t}
                    </button>
                  ))}
                </div>
              </div>
              {tab === "Plan" && (
                <div className="result-body">
                  <h2>Make the next measurement count.</h2>
                  <p className="muted">
                    Compare feasible sites under the same practical constraints.
                  </p>
                  <label className="field">
                    Planning objective
                    <select
                      value={inv.settings.objective}
                      onChange={(e) =>
                        edit({
                          settings: {
                            ...inv.settings,
                            objective: e.target.value as
                              | "scenario_information"
                              | "spatial_coverage"
                              | "prediction_variance",
                          },
                        })
                      }
                    >
                      <option value="scenario_information">
                        Experimental scenario information
                      </option>
                      <option value="spatial_coverage">
                        Spatial coverage · no weather needed
                      </option>
                      <option value="prediction_variance">
                        Spatial prediction · concentration uncertainty
                      </option>
                    </select>
                  </label>
                  <div className="field-row">
                    <label className="field">
                      Budget (cost units)
                      <input
                        type="number"
                        min="0"
                        max="1000000"
                        value={inv.settings.budget}
                        onChange={(e) =>
                          edit({
                            settings: {
                              ...inv.settings,
                              budget: Number(e.target.value),
                            },
                          })
                        }
                      />
                    </label>
                    <label className="field">
                      Equipment limit
                      <input
                        type="number"
                        min="1"
                        max="8"
                        value={inv.settings.equipment_limit}
                        onChange={(e) =>
                          edit({
                            settings: {
                              ...inv.settings,
                              equipment_limit: Number(e.target.value),
                            },
                          })
                        }
                      />
                    </label>
                  </div>
                  <div className="window-note">
                    <Wind size={15} />
                    <span>
                      Observed steady window
                      <small>
                        Retrospective only · future scheduling unsupported
                      </small>
                    </span>
                  </div>
                  <button
                    className="button primary run-button"
                    disabled={busy}
                    onClick={run}
                  >
                    {busy ? (
                      <LoaderCircle className="spin" size={16} />
                    ) : (
                      <Play size={15} />
                    )}{" "}
                    {busy ? "Comparing plans…" : "Generate measurement plans"}
                    <ArrowRight size={15} />
                  </button>
                  {busy && (
                    <button
                      className="text-button"
                      onClick={() => {
                        abort.current?.abort();
                        setBusy(false);
                      }}
                    >
                      Cancel request
                    </button>
                  )}
                  {!result && (
                    <div className="before-plan">
                      <span className="plan-icon">
                        <MapPin size={24} />
                      </span>
                      <b>A plan grounded in your constraints</b>
                      <p>
                        {eligible.length} eligible sites. Compare the optimizer
                        with spatial spread, a reproducible random plan, and a
                        wind baseline when weather supports it.
                      </p>
                      <div>
                        <span>01 · Define</span>
                        <span>02 · Compare</span>
                        <span>03 · Measure</span>
                      </div>
                    </div>
                  )}
                  {result && (
                    <>
                      <div className="section-rule" />
                      <div className="result-status">
                        <span
                          className={
                            result.status === "ok" ? "tiny-check" : "amber-dot"
                          }
                        >
                          {result.status === "ok" ? "✓" : ""}
                        </span>
                        <b>
                          {result.status === "ok"
                            ? "Plan comparison"
                            : "Action needed"}
                        </b>
                        <small>
                          {result.runtime_ms !== undefined
                            ? `${result.runtime_ms} ms`
                            : ""}
                        </small>
                      </div>
                      {result.reason && (
                        <p className="inline-warning">{result.reason}</p>
                      )}
                      {result.plans.map((p, i) => (
                        <button
                          className={
                            "plan-option " + (planIndex === i ? "chosen" : "")
                          }
                          key={p.method}
                          onClick={() => setPlanIndex(i)}
                        >
                          <span className="plan-rank">
                            {i === 0 ? (
                              <Wind size={15} />
                            ) : (
                              String(i + 1).padStart(2, "0")
                            )}
                          </span>
                          <span>
                            <b>{p.method}</b>
                            <small>
                              {p.site_ids.join(" + ") || "No sites"} ·{" "}
                              {p.cost.toFixed(0)} cost units
                            </small>
                          </span>
                          <span className="plan-score">
                            {p.score.toFixed(5)}
                            <small>
                              {inv.settings.objective === "scenario_information"
                                ? "nats"
                                : inv.settings.objective ===
                                    "prediction_variance"
                                  ? "(µg/m³)²"
                                  : "coverage"}
                            </small>
                          </span>
                        </button>
                      ))}
                      {plan && (
                        <div className="selected-sites">
                          <span className="small-label">SELECTED PLAN</span>
                          {plan.site_ids.map((id) => (
                            <button
                              key={id}
                              onClick={() => {
                                setSelected(id);
                                setTab("Sites");
                              }}
                            >
                              <MapPin size={14} />
                              {inv.sites.find((s) => s.id === id)?.name || id}
                              <ArrowUpRight size={13} />
                            </button>
                          ))}
                        </div>
                      )}
                      <p className="score-note">{result.interpretation}</p>
                      {inv.settings.objective === "scenario_information" && (
                        <p className="score-note">
                          Experimental measurement comparison under the assumed
                          observed weather window. This is not a future weather
                          forecast or a demonstrated field improvement. Compare
                          the spread and random baselines before choosing sites.
                        </p>
                      )}
                      <EvidenceDetails result={result} />
                      {result.plans.find((p) => p.seeds) && (
                        <p className="score-note">
                          Random baseline: 20 seeds; mean{" "}
                          {result.plans
                            .find((p) => p.seeds)
                            ?.mean_score?.toFixed(5)}
                          , range{" "}
                          {result.plans
                            .find((p) => p.seeds)
                            ?.min_score?.toFixed(5)}
                          –
                          {result.plans
                            .find((p) => p.seeds)
                            ?.max_score?.toFixed(5)}
                          . Map shows seed {inv.settings.seed}.
                        </p>
                      )}
                      {result.ties != null && (
                        <p className="score-note">
                          {result.exact_search
                            ? "Exact search over feasible subsets"
                            : "Greedy selection"}{" "}
                          · {result.ties} optimal tie(s).
                        </p>
                      )}
                      <details className="limits">
                        <summary>
                          <Info size={13} />
                          Assumptions & unresolved questions
                        </summary>
                        {result.warnings.map((w) => (
                          <p key={w}>{w}</p>
                        ))}
                        <code>
                          {result.model_version}
                          <br />
                          Input {result.input_hash.slice(0, 16)}
                        </code>
                      </details>
                    </>
                  )}
                  {inv.plan_history.length > 0 && (
                    <details className="limits">
                      <summary>
                        Previous comparisons ({inv.plan_history.length})
                      </summary>
                      {inv.plan_history.map((r, i) => (
                        <p key={i}>
                          {r.input_hash.slice(0, 12)} ·{" "}
                          {r.plans[0]?.site_ids.join(" + ") || r.status} · score{" "}
                          {r.plans[0]?.score.toFixed(5) ?? "unavailable"}
                        </p>
                      ))}
                    </details>
                  )}
                </div>
              )}
              {tab === "Scenarios" && (
                <div className="result-body">
                  <span className="pill amber">
                    EXPERIMENTAL · SYNTHETIC EVALUATION ONLY
                  </span>
                  <h2>Compare explanations, not blame.</h2>
                  <p className="muted">
                    Compare background-only and single-source explanations.
                    Source-domain anchors bound a rectangular search area; they
                    are not exact source findings. Conditional model weights are
                    not calibrated real-world probabilities.
                  </p>
                  {result && <EvidenceDetails result={result} />}
                  <button
                    className="button primary"
                    onClick={run}
                    disabled={busy}
                  >
                    {busy ? "Analyzing study…" : "Analyze current study"}
                  </button>
                  <h3>Required conditions</h3>
                  <button
                    className="button secondary"
                    onClick={async () => {
                      try {
                        if (dirty) await saveCurrent();
                        load(await api<Investigation>("/demo/campaign"));
                        setTab("Scenarios");
                      } catch (e) {
                        reportError(e);
                      }
                    }}
                  >
                    Open synthetic campaign example
                  </button>
                  {(["steady", "open_terrain", "local_weather"] as const).map(
                    (key, i) => (
                      <label className="check-field" key={key}>
                        <input
                          type="checkbox"
                          checked={inv.assumptions[key]}
                          onChange={(e) =>
                            edit({
                              assumptions: {
                                ...inv.assumptions,
                                [key]: e.target.checked,
                              },
                            })
                          }
                        />
                        {
                          [
                            "Steady wind & release within each period (≤1 hour)",
                            "Open, neutral terrain; no street canyons",
                            "Representative local measured weather",
                          ][i]
                        }
                      </label>
                    ),
                  )}
                  <label className="field">
                    Assumption evidence
                    <textarea
                      value={inv.assumptions.note}
                      onChange={(e) =>
                        edit({
                          assumptions: {
                            ...inv.assumptions,
                            note: e.target.value,
                          },
                        })
                      }
                    />
                  </label>
                  <details>
                    <summary>Campaign periods and physical metadata</summary>
                    <p>
                      Use two to six explicitly identified, non-overlapping
                      observed periods. Winds may differ between periods; each
                      period must be independently steady. Transition transport
                      is not modeled. Existing readings are never split or
                      deleted automatically.
                    </p>
                    <label className="check-field">
                      <input
                        type="checkbox"
                        checked={
                          inv.assumptions.constant_release_across_windows ??
                          false
                        }
                        onChange={(e) =>
                          edit({
                            assumptions: {
                              ...inv.assumptions,
                              constant_release_across_windows: e.target.checked,
                            },
                          })
                        }
                      />
                      Fixed source location and constant release across all
                      periods
                    </label>
                    {(inv.study_windows ?? []).map((period, index) => (
                      <div key={index} className="limits">
                        <label className="field">
                          Period identifier
                          <input
                            value={period.id}
                            onChange={(e) =>
                              edit({
                                study_windows: inv.study_windows!.map((w, i) =>
                                  i === index
                                    ? { ...w, id: e.target.value }
                                    : w,
                                ),
                              })
                            }
                          />
                        </label>
                        <label className="field">
                          Start (explicit UTC offset)
                          <input
                            value={period.start}
                            placeholder="2026-06-02T09:00:00+00:00"
                            onChange={(e) =>
                              edit({
                                study_windows: inv.study_windows!.map((w, i) =>
                                  i === index
                                    ? { ...w, start: e.target.value }
                                    : w,
                                ),
                              })
                            }
                          />
                        </label>
                        <label className="field">
                          End (explicit UTC offset)
                          <input
                            value={period.end}
                            placeholder="2026-06-02T09:15:00+00:00"
                            onChange={(e) =>
                              edit({
                                study_windows: inv.study_windows!.map((w, i) =>
                                  i === index
                                    ? { ...w, end: e.target.value }
                                    : w,
                                ),
                              })
                            }
                          />
                        </label>
                        <button
                          className="button secondary"
                          onClick={() =>
                            edit({
                              study_windows: inv.study_windows!.filter(
                                (_, i) => i !== index,
                              ),
                            })
                          }
                        >
                          Remove period
                        </button>
                      </div>
                    ))}
                    <button
                      className="button secondary"
                      disabled={(inv.study_windows?.length ?? 0) >= 6}
                      onClick={() =>
                        edit({
                          study_windows: [
                            ...(inv.study_windows ?? []),
                            {
                              id: `period-${(inv.study_windows?.length ?? 0) + 1}`,
                              start: "",
                              end: "",
                            },
                          ],
                        })
                      }
                    >
                      Add observed steady period
                    </button>
                    <p>
                      With no explicit periods, the original single-period limit
                      applies. An incomplete period must be completed or removed
                      before analysis.
                    </p>
                    <label className="field">
                      Observed wind direction uncertainty (standard deviation,
                      degrees)
                      <input
                        type="number"
                        min="0.5"
                        max="45"
                        step="0.5"
                        value={inv.settings.met_direction_sd_deg ?? 20}
                        onChange={(e) =>
                          edit({
                            settings: {
                              ...inv.settings,
                              met_direction_sd_deg: Number(e.target.value),
                            },
                          })
                        }
                      />
                    </label>
                    <label className="field">
                      Wind-speed scenario fraction
                      <input
                        type="number"
                        min="0"
                        max="0.5"
                        step="0.01"
                        value={inv.settings.met_speed_fraction ?? 0.3}
                        onChange={(e) =>
                          edit({
                            settings: {
                              ...inv.settings,
                              met_speed_fraction: Number(e.target.value),
                            },
                          })
                        }
                      />
                    </label>
                    <label className="field">
                      Meteorological uncertainty evidence
                      <textarea
                        value={
                          inv.settings.met_uncertainty_provenance ??
                          "Unverified research assumption"
                        }
                        onChange={(e) =>
                          edit({
                            settings: {
                              ...inv.settings,
                              met_uncertainty_provenance: e.target.value,
                            },
                          })
                        }
                      />
                    </label>
                    <p>
                      Use instrument or study evidence. Smaller uncertainty
                      inputs can create false precision; these settings do not
                      calibrate weather.
                    </p>
                    <label className="field">
                      Assumed release height (m)
                      <input
                        type="number"
                        min="0"
                        max="100"
                        value={inv.settings.source_height_m ?? 5}
                        onChange={(e) =>
                          edit({
                            settings: {
                              ...inv.settings,
                              source_height_m: Number(e.target.value),
                            },
                          })
                        }
                      />
                    </label>
                    <label className="field">
                      Receptor height (m)
                      <input
                        type="number"
                        min="0"
                        max="20"
                        value={inv.settings.receptor_height_m ?? 2}
                        onChange={(e) =>
                          edit({
                            settings: {
                              ...inv.settings,
                              receptor_height_m: Number(e.target.value),
                            },
                          })
                        }
                      />
                    </label>
                  </details>
                  <label className="field">
                    Default measurement uncertainty (µg/m³)
                    <input
                      type="number"
                      min="0.5"
                      max="100"
                      step="0.5"
                      value={inv.settings.noise_ug_m3}
                      onChange={(e) =>
                        edit({
                          settings: {
                            ...inv.settings,
                            noise_ug_m3: Number(e.target.value),
                          },
                        })
                      }
                    />
                  </label>
                  <p className="score-note">
                    Explicit user setting; this does not calibrate instruments.
                    Per-reading uncertainty, when supplied, overrides this for
                    fitting.
                  </p>
                  <label className="field">
                    Maximum fitted readings
                    <input
                      type="number"
                      min="40"
                      max="512"
                      step="8"
                      value={inv.settings.inference_limit ?? 128}
                      onChange={(e) =>
                        edit({
                          settings: {
                            ...inv.settings,
                            inference_limit: Number(e.target.value),
                          },
                        })
                      }
                    />
                  </label>
                  <label className="field">
                    Observation selection seed
                    <input
                      type="number"
                      min="0"
                      max="4294967295"
                      step="1"
                      value={inv.settings.selection_seed ?? 0}
                      onChange={(e) =>
                        edit({
                          settings: {
                            ...inv.settings,
                            selection_seed: Number(e.target.value),
                          },
                        })
                      }
                    />
                  </label>
                  <p className="score-note">
                    The fitting limit bounds computation. Review the reported
                    loaded, excluded, and fitted counts and compare row limits
                    or selection seeds when the investigation contains more
                    readings. This does not delete original observations.
                  </p>
                  {inv.source_locations.map((p, i) => {
                    const weight = result?.sources[i]?.weight;
                    return (
                      <div key={i} className="scenario-row">
                        <span className="source-id">S{i + 1}</span>
                        <div>
                          <b>Domain anchor {i + 1}</b>
                          <div className="weight-bar">
                            <i style={{ width: `${(weight || 0) * 100}%` }} />
                          </div>
                        </div>
                        <span>
                          {weight === undefined
                            ? "Unrun"
                            : weight.toFixed(3) + "*"}
                        </span>
                        <button
                          className="icon-button"
                          aria-label={`Remove source S${i + 1}`}
                          onClick={() =>
                            edit({
                              source_locations: inv.source_locations.filter(
                                (_, j) => i !== j,
                              ),
                            })
                          }
                        >
                          <X size={13} />
                        </button>
                      </div>
                    );
                  })}
                  <button
                    className="text-button"
                    disabled={inv.source_locations.length >= 25}
                    onClick={() => {
                      setMode("source");
                      notify("Click the map to add a source-domain anchor.");
                    }}
                  >
                    <Plus size={14} />
                    Add domain anchor
                  </button>
                  <p className="score-note">
                    *For the current model, this is the weight of the
                    nearest-anchor partition of the search domain, conditional
                    on a single source. It is not probability at the marker.
                    Archived earlier models used discrete scenario locations.
                    Neither meaning establishes responsibility or field
                    accuracy.
                  </p>
                  {result?.fitted_rmse_ug_m3 != null && (
                    <p className="score-note">
                      Fitted residual RMSE:{" "}
                      {result.fitted_rmse_ug_m3.toFixed(2)} µg/m³. This is an
                      in-sample diagnostic, not predictive validation.
                    </p>
                  )}
                  <button
                    className="button primary"
                    onClick={() => {
                      edit({
                        settings: {
                          ...inv.settings,
                          objective: "scenario_information",
                        },
                      });
                      setTab("Plan");
                    }}
                  >
                    Configure scenario plan
                    <ArrowRight size={15} />
                  </button>
                </div>
              )}
              {tab === "Sites" && (
                <div className="result-body">
                  <h2>Places you can measure.</h2>
                  <p className="muted">
                    Only confirmed permission, power, access, and the supported
                    window make a candidate eligible.
                  </p>
                  <select
                    className="site-select"
                    aria-label="Select site"
                    value={selected}
                    onChange={(e) => setSelected(e.target.value)}
                  >
                    <option value="">Choose a site…</option>
                    {inv.sites.map((s) => (
                      <option key={s.id} value={s.id}>
                        {s.id} · {s.name}
                      </option>
                    ))}
                  </select>
                  {site ? (
                    <>
                      <label className="field">
                        Site name
                        <input
                          value={site.name}
                          maxLength={100}
                          onChange={(e) => updateSite({ name: e.target.value })}
                        />
                      </label>
                      <div className="coordinate-readout">
                        {site.latitude.toFixed(5)}°, {site.longitude.toFixed(5)}
                        ° · {site.kind}
                      </div>
                      {site.kind === "candidate" && (
                        <>
                          <label className="field">
                            Deployment cost (cost units)
                            <input
                              type="number"
                              min="0"
                              value={site.cost}
                              onChange={(e) =>
                                updateSite({ cost: Number(e.target.value) })
                              }
                            />
                          </label>
                          {(["allowed", "power", "access"] as const).map(
                            (key, i) => (
                              <label className="check-field" key={key}>
                                <input
                                  type="checkbox"
                                  checked={site[key]}
                                  onChange={(e) =>
                                    updateSite({ [key]: e.target.checked })
                                  }
                                />
                                {
                                  [
                                    "Permission confirmed",
                                    "Power or battery confirmed",
                                    "Safe access confirmed",
                                  ][i]
                                }
                              </label>
                            ),
                          )}
                          <label className="check-field">
                            <input
                              type="checkbox"
                              checked={site.windows.includes("steady-window")}
                              onChange={(e) =>
                                updateSite({
                                  windows: e.target.checked
                                    ? ["steady-window"]
                                    : [],
                                })
                              }
                            />
                            Available in the observed steady window
                          </label>
                        </>
                      )}
                      <button
                        className="text-button danger"
                        onClick={() => {
                          edit({
                            sites: inv.sites.filter((s) => s.id !== selected),
                          });
                          setSelected("");
                        }}
                      >
                        Remove site marker
                      </button>
                      <p className="score-note">
                        Removing a monitor marker preserves its imported
                        readings and provenance.
                      </p>
                    </>
                  ) : (
                    <div className="empty-state">
                      Select a marker on the map or add a site below.
                    </div>
                  )}
                  <button
                    className="button secondary"
                    onClick={() => {
                      setMode("candidate");
                      notify("Click the map to mark a candidate site.");
                    }}
                  >
                    <Plus size={15} />
                    Add candidate on map
                  </button>
                </div>
              )}
            </aside>
          </div>
          <footer className="page-footer">
            <span>
              <span className="online-dot" />
              Local analysis · no paid APIs · no automatic submission
            </span>
            <button onClick={() => setDialog("help")}>
              Methods, provenance & evidence
              <ArrowUpRight size={13} />
            </button>
          </footer>
        </div>
      </main>
      {toast && (
        <div role="status" className="toast">
          <Check size={16} />
          {toast}
        </div>
      )}
      {dialog === "define" && (
        <Modal title="Define the investigation" onClose={() => setDialog(null)}>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              const d = new FormData(e.currentTarget);
              const area = ["west", "south", "east", "north"].map((k) =>
                Number(d.get(k)),
              );
              if (area[0] >= area[2] || area[1] >= area[3]) {
                setFileError(
                  "West must be less than east; south must be less than north.",
                );
                return;
              }
              edit({
                name: String(d.get("name")),
                concern: String(d.get("concern")),
                objective: String(d.get("objective")),
                area,
              });
              setDialog(null);
              setFileError("");
            }}
          >
            <label className="field">
              Investigation name
              <input
                name="name"
                required
                maxLength={120}
                defaultValue={inv.name}
              />
            </label>
            <label className="field">
              Concern
              <textarea
                name="concern"
                maxLength={4000}
                defaultValue={inv.concern}
                placeholder="What happened, and what remains unknown?"
              />
            </label>
            <label className="field">
              Monitoring objective
              <textarea
                name="objective"
                maxLength={2000}
                defaultValue={inv.objective}
              />
            </label>
            <h3>Area bounds (decimal degrees)</h3>
            <div className="field-row">
              {["west", "south", "east", "north"].map((k, i) => (
                <label className="field" key={k}>
                  {k}
                  <input
                    name={k}
                    type="number"
                    step="any"
                    min={i % 2 === 0 ? -180 : -85}
                    max={i % 2 === 0 ? 180 : 85}
                    defaultValue={inv.area[i]}
                    required
                  />
                </label>
              ))}
            </div>
            <p className="muted">
              Select a small local area. Physics uses metric projected
              coordinates. Dateline-crossing areas are unsupported.
            </p>
            {fileError && (
              <p role="alert" className="inline-warning">
                {fileError}
              </p>
            )}
            <button className="button primary" type="submit">
              Apply investigation settings
              <ArrowRight size={15} />
            </button>
          </form>
        </Modal>
      )}
      {dialog === "library" && (
        <Modal
          title="Your local investigations"
          onClose={() => setDialog(null)}
        >
          <div className="library-actions">
            <button
              className="button primary"
              onClick={() => {
                load(emptyInvestigation());
                setDirty(true);
                setDialog("define");
              }}
            >
              <Plus size={15} />
              New investigation
            </button>
            <button
              className="button secondary"
              onClick={() =>
                api<Investigation>("/demo").then(load).catch(reportError)
              }
            >
              <RotateCcw size={15} />
              Open synthetic example
            </button>
          </div>
          {saved.length === 0 && (
            <p className="muted">
              No saved investigations yet. Save your workspace to reopen it
              here.
            </p>
          )}
          {saved.map((s) => (
            <button
              className="library-row"
              key={s.id}
              onClick={() =>
                api<Investigation>("/investigations/" + s.id)
                  .then(load)
                  .catch(reportError)
              }
            >
              <FolderOpen size={18} />
              <span>
                <b>{s.name}</b>
                <small>{new Date(s.updated).toLocaleString()}</small>
              </span>
              <ArrowRight size={15} />
            </button>
          ))}
          <input
            ref={jsonRef}
            type="file"
            accept=".json,application/json"
            hidden
            onChange={async (e) => {
              const file = e.target.files?.[0];
              if (!file) return;
              try {
                if (file.size > 8_000_000)
                  throw new Error("Investigation JSON exceeds 8 MB limit");
                const imported = await api<Investigation>(
                  "/investigations/import",
                  JSON.parse(await file.text()),
                );
                load(imported);
                notify(
                  "Investigation imported and saved; stored analysis recomputed.",
                );
              } catch (e) {
                reportError(e);
              } finally {
                if (jsonRef.current) jsonRef.current.value = "";
              }
            }}
          />
          <button
            className="text-button"
            onClick={() => jsonRef.current?.click()}
          >
            <Upload size={15} />
            Restore investigation JSON
          </button>
          <p className="score-note">
            Switching investigations replaces unsaved local edits. Save first to
            preserve them.
          </p>
        </Modal>
      )}
      {dialog === "import" && (
        <Modal
          title="Import measurements or weather"
          onClose={() => setDialog(null)}
        >
          <p className="muted">
            CSV only · UTF-8 · up to 2 MB and 10,000 rows. Originals and
            transformation records are retained. Follow-up readings append to
            this investigation and invalidate its previous analysis.
          </p>
          {inv.synthetic && (
            <p className="inline-warning">
              This is a synthetic investigation. Create a new investigation for
              real data to avoid mixing evidence levels.
            </p>
          )}
          <div className="field-row">
            <label className="field">
              Table type
              <select
                value={importKind}
                onChange={(e) => {
                  const kind = e.target.value as "measurements" | "weather";
                  setImportKind(kind);
                  setUnits(
                    kind === "measurements"
                      ? "ug/m3"
                      : "m/s,degrees-from-north",
                  );
                  setImportSummary(null);
                }}
              >
                <option value="measurements">PM2.5 measurements</option>
                <option value="weather">Meteorology</option>
              </select>
            </label>
            <label className="field">
              Timezone for naive timestamps
              <input
                placeholder="e.g. America/New_York"
                value={zone}
                onChange={(e) => setZone(e.target.value)}
              />
            </label>
          </div>
          <label className="field">
            Units
            <select value={units} onChange={(e) => setUnits(e.target.value)}>
              {importKind === "measurements" ? (
                <>
                  <option value="ug/m3">µg/m³</option>
                  <option value="mg/m3">
                    mg/m³ · conversion required before import
                  </option>
                </>
              ) : (
                <>
                  <option value="m/s,degrees-from-north">
                    m/s · degrees FROM north
                  </option>
                  <option value="mph">
                    mph · conversion required before import
                  </option>
                </>
              )}
            </select>
          </label>
          <input
            ref={fileRef}
            type="file"
            accept=".csv,text/csv"
            aria-label="CSV file"
            onChange={async (e) => {
              const file = e.target.files?.[0];
              if (!file) return;
              setFileError("");
              setImportSummary(null);
              if (file.size > 2_000_000) {
                setFileError("File exceeds 2 MB limit");
                return;
              }
              setFilename(file.name);
              setCsv(await file.text());
              setMapping({});
            }}
          />
          {csv && (
            <>
              <div className="mapping">
                <h3>Map CSV columns</h3>
                <p className="score-note">
                  Required fields below. Optional canonical columns:
                  uncertainty_ug_m3, humidity_percent, temperature_c. Quoted
                  data values are supported; headers should be simple names.
                </p>
                {required.map((field) => (
                  <label className="mapping-row" key={field}>
                    <code>{field}</code>
                    <select
                      value={mapping[field] || field}
                      onChange={(e) =>
                        setMapping({ ...mapping, [field]: e.target.value })
                      }
                    >
                      {!headers.includes(field) && (
                        <option value={field}>Select column…</option>
                      )}
                      {headers.map((h, i) => (
                        <option key={i} value={h}>
                          {h}
                        </option>
                      ))}
                    </select>
                  </label>
                ))}
              </div>
              <button
                className="button primary"
                disabled={busy}
                onClick={importCSV}
              >
                {busy ? (
                  <LoaderCircle size={15} className="spin" />
                ) : (
                  <Upload size={15} />
                )}
                Validate & append CSV
              </button>
            </>
          )}
          {fileError && (
            <p role="alert" className="inline-warning">
              {fileError}
            </p>
          )}
          {importSummary && (
            <div className="import-summary" role="status">
              <h3>Import quality summary</h3>
              <p>
                {importSummary.summary.accepted} accepted ·{" "}
                {importSummary.summary.invalid} invalid ·{" "}
                {importSummary.summary.flagged} flagged
              </p>
              {importSummary.summary.issues.slice(0, 20).map((x) => (
                <p key={x.line}>
                  Row {x.line}: {x.error}
                </p>
              ))}
              <p>
                Invalid rows remain in the original CSV. Flagged rows remain in
                the normalized table. Inspect Data quality for provenance.
              </p>
              <button
                className="button secondary"
                onClick={() => {
                  setDialog(null);
                  setBottom("Data quality");
                }}
              >
                Inspect imported data
                <ArrowRight size={15} />
              </button>
            </div>
          )}
        </Modal>
      )}
      {newPoint && (
        <Modal
          title={
            mode === "source"
              ? "Add source-domain anchor"
              : mode === "observation"
                ? "Record resident observation"
                : "Add monitoring site"
          }
          onClose={() => {
            setNewPoint(null);
            setFileError("");
          }}
        >
          <form onSubmit={addPoint}>
            <p className="muted">
              {mode === "source"
                ? "Anchors bound the rectangular search domain. They do not identify an exact source or a responsible party."
                : mode === "observation"
                  ? "Describe the original observation without identifying a responsible source."
                  : "Confirm permission and safe access before a candidate can enter a plan."}
            </p>
            {mode !== "source" && (
              <label className="field">
                {mode === "observation" ? "Observation notes" : "Site name"}
                <input
                  name="name"
                  required
                  maxLength={mode === "observation" ? 2000 : 100}
                />
              </label>
            )}
            {!["source", "observation"].includes(mode) && (
              <label className="field">
                Unique site ID
                <input
                  name="id"
                  required
                  maxLength={80}
                  defaultValue={
                    (mode === "sensor" ? "M" : "C") + (inv.sites.length + 1)
                  }
                />
              </label>
            )}
            <div className="field-row">
              <label className="field">
                Latitude
                <input
                  name="latitude"
                  type="number"
                  step="any"
                  min="-85"
                  max="85"
                  required
                  defaultValue={newPoint.latitude.toFixed(6)}
                />
              </label>
              <label className="field">
                Longitude
                <input
                  name="longitude"
                  type="number"
                  step="any"
                  min="-180"
                  max="180"
                  required
                  defaultValue={newPoint.longitude.toFixed(6)}
                />
              </label>
            </div>
            {mode === "observation" && (
              <label className="field">
                Observation time (local timezone)
                <input name="timestamp" type="datetime-local" required />
              </label>
            )}
            {!["source", "observation"].includes(mode) && (
              <>
                <label className="field">
                  Deployment cost (cost units)
                  <input
                    name="cost"
                    type="number"
                    min="0"
                    max="1000000"
                    defaultValue="150"
                    required
                  />
                </label>
                {["allowed", "power", "access", "window"].map((k, i) => (
                  <label className="check-field" key={k}>
                    <input name={k} type="checkbox" />
                    {
                      [
                        "Permission confirmed",
                        "Power or battery confirmed",
                        "Safe access confirmed",
                        "Available in the observed steady window",
                      ][i]
                    }
                  </label>
                ))}
              </>
            )}
            {fileError && (
              <p className="inline-warning" role="alert">
                {fileError}
              </p>
            )}
            <button type="submit" className="button primary">
              <Plus size={15} />
              Add {mode}
            </button>
          </form>
        </Modal>
      )}
      {dialog === "exports" && (
        <Modal
          title="Save a reviewable evidence package"
          onClose={() => setDialog(null)}
        >
          <p className="muted">
            Exports save the current investigation first. Review the report and
            remove sensitive information before sharing. Nothing is submitted
            automatically.
          </p>
          <button
            className="export-option"
            onClick={() => exportFile("report")}
          >
            <FileText size={24} />
            <span>
              <b>Evidence report</b>
              <small>
                Self-contained HTML · print to PDF from your browser ·
                observations rounded to ~1 km
              </small>
            </span>
            <Download size={18} />
          </button>
          <button
            className="export-option"
            onClick={() => exportFile("export")}
          >
            <FolderOpen size={24} />
            <span>
              <b>Private investigation archive</b>
              <small>
                JSON with full coordinates, raw imports, settings, results, and
                history
              </small>
            </span>
            <Download size={18} />
          </button>
          <button
            className="export-option"
            onClick={() => exportFile("measurements.csv")}
          >
            <Activity size={24} />
            <span>
              <b>Normalized measurements</b>
              <small>
                CSV · all retained rows and quality flags · spreadsheet-safe
                text fields
              </small>
            </span>
            <Download size={18} />
          </button>
          <p className="inline-warning">
            Full coordinate archives may reveal residential locations. Reports
            retain free-text notes: review these yourself before sharing.
          </p>
        </Modal>
      )}
      {dialog === "help" && (
        <Modal
          title="Field guide & evidence levels"
          onClose={() => setDialog(null)}
        >
          <div className="help-content">
            <div className="help-step">
              <Eye />
              <div>
                <h3>Observed measurements</h3>
                <p>
                  Imported PM2.5 readings are shown only at monitor locations,
                  with an arithmetic-mean timeline. They are not street-level
                  estimates, composition measurements, or proof of an odor's
                  cause.
                </p>
              </div>
            </div>
            <div className="help-step">
              <MapPin />
              <div>
                <h3>Monitoring design</h3>
                <p>
                  Spatial coverage planning uses permitted sites and distances.
                  Experimental information planning estimates learning about
                  background-only versus broad source areas under this research
                  model, using finite mixtures and numerical integration. Both
                  obey cost, equipment, access, and observed-window constraints.
                  Information planning remains experimental and has no
                  guaranteed advantage over simple baselines in the field.
                </p>
              </div>
            </div>
            <div className="help-step">
              <FlaskConical />
              <div>
                <h3>Experimental reconstruction</h3>
                <p>
                  The steady Gaussian plume requires local wind ≥0.8 and ≤8 m/s,
                  a ≤1 hour period, and open neutral terrain. Weather must be
                  within 30 minutes and 3 km. Calm, variable winds and missing
                  weather reduce capability. A checkbox is an assertion, not
                  validation.
                </p>
                <p>
                  Implementation checks, model adequacy, identifiability, and
                  empirical reliability are separate questions. No field PM2.5
                  attribution, independent tracer validation, or external-user
                  validation has been demonstrated. Conditional regions describe
                  a model calculation, not calibrated field coverage. The
                  preserved stress report records weak-signal failures and
                  confidently wrong results under mismatch. Real openair data
                  were inspected, but missing verified station metadata and
                  blocked NOAA/EPA access prevent independent source validation.
                  See docs/STRESS_REPORT.md.
                </p>
              </div>
            </div>
            <div className="help-step">
              <MessageSquare />
              <div>
                <h3>Resident observations</h3>
                <p>
                  Keep original accounts separate from sensor readings. Use
                  approximate locations and review notes for privacy before
                  exporting.
                </p>
              </div>
            </div>
            <h3>Try the complete workflow</h3>
            <ol>
              <li>Open the synthetic example or create a new investigation.</li>
              <li>
                Import readings and weather; inspect quality and provenance.
              </li>
              <li>Mark sites, costs, permission and access.</li>
              <li>Generate plans; compare the same budget across baselines.</li>
              <li>Save, import follow-up readings, and rerun.</li>
              <li>Export and review a self-contained evidence report.</li>
            </ol>
            <p>
              Research foundations include Gaussian dispersion, Bayesian
              scenario comparison and information-based experimental design.
              These methods predate UPWIND. See the repository's
              docs/SCIENCE.md, SOURCES.md, and AI_ASSISTANCE.md for equations,
              attribution, evidence limits, and owner learning points.
            </p>
          </div>
        </Modal>
      )}
    </div>
  );
}
