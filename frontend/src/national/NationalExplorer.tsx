import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { KeyboardEvent, PointerEvent as ReactPointerEvent } from "react";
import { Map as MapLibreMap } from "maplibre-gl";
import type { ErrorEvent, GeoJSONSource as MapGeoJSONSource, MapLayerMouseEvent } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import {
  Activity, AlertCircle, ArrowRight, Bookmark, ChevronDown, CircleHelp, Download,
  ExternalLink, FileText, Layers3, MapPin, Search, Share2, Wind, X, Plus, Minus, LocateFixed, SquareDashedMousePointer,
  PanelRightClose, PanelRightOpen,
} from "lucide-react";
import {
  CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import LoadingScreen from "../LoadingScreen";
import type { Facility, Monitor, NationalManifest, NationalPlace, NationalSnapshot } from "./types";

type Layer = "estimates" | "monitors" | "sources";
type CameraState = { longitude: number; latitude: number; zoom: number; bearing: number; pitch: number };
const readCamera = (params: URLSearchParams): CameraState | null => {
  if (params.get("v") !== "1") return null;
  const values = (params.get("camera") || "").split(",").map(Number);
  if (values.length !== 5 || values.some((value) => !Number.isFinite(value))) return null;
  const [longitude, latitude, zoom, bearing, pitch] = values;
  if (longitude < -180 || longitude > 180 || latitude < -85 || latitude > 85 || zoom < 2 || zoom > 15 || bearing < -180 || bearing > 180 || pitch < 0 || pitch > 60) return null;
  return { longitude, latitude, zoom, bearing, pitch };
};
const readFeature = (value: string | null): { kind: "monitors" | "sources"; id: string } | null => {
  if (!value) return null;
  const separator = value.indexOf(":");
  if (separator < 1) return null;
  const kind = value.slice(0, separator);
  const id = value.slice(separator + 1);
  return (kind === "monitors" || kind === "sources") && id.length > 0 && id.length <= 120 ? { kind, id } : null;
};
type ViewportItem = Record<string, any> & { id: string; cluster_id: string; member_count: number; is_cluster: boolean; render_latitude?: number; render_longitude?: number };
type ViewportResult = { items: ViewportItem[]; represented_records: number; symbol_count: number; complete: boolean; aggregation_zoom: number; dataset_version: string };
type ClusterSelection = { kind: Layer; id: string; count: number; members: any[]; nextOffset: number | null; loading: boolean };
type ContextItem = {
  evidence_class: "measured_monitor_summary" | "facility_inventory_estimate";
  id: string;
  distance_km: number;
  relation: string;
  year?: number;
  value_ug_m3?: number;
  units?: string;
  inventory_year?: number;
  pollutant_code?: string;
  emissions?: number;
  category?: string;
  source?: string;
  source_url?: string | null;
  interpretation: string;
};
type ContextResponse = {
  items: ContextItem[];
  nearest_monitors: ContextItem[];
  closest_facilities: ContextItem[];
  largest_compatible_inventory_groups: { pollutant_code: string; units: string; compatible_record_count: number; ranking_meaning: string; records: ContextItem[] }[];
  counts: { measured_monitor_summaries: number; facility_inventory_summary_rows: number; distinct_facilities: number };
  monitoring_gap: { status: string; monitor_summary_count: number; radius_km: number; meaning: string };
  provenance: { monitor_year: number; inventory_year: number };
  limitations: string[];
};
const API = "/api/national";
const fmt = (n: number | null | undefined, places = 0) =>
  n == null || !Number.isFinite(n) ? "—" : n.toLocaleString("en-US", { maximumFractionDigits: places, minimumFractionDigits: places });
const isSameId = (a: any, b: any): boolean =>
  a != null && b != null && String(a).trim() === String(b).trim();

function normalizeItem<T = ViewportItem>(item: any): T {
  if (!item || typeof item !== "object") return item;
  const clone = { ...item };
  if (clone.id != null) clone.id = String(clone.id);
  for (const key of ["model_estimates", "evidence_explanation", "estimates", "nearby_monitor", "original_coordinates"]) {
    if (typeof clone[key] === "string") {
      try {
        clone[key] = JSON.parse(clone[key]);
      } catch {
        // preserve original string
      }
    }
  }
  return clone as T;
}

const pointFeature = (coordinates: [number, number], properties: Record<string, unknown>) => ({
  type: "Feature" as const,
  id: properties.id != null ? String(properties.id) : undefined,
  geometry: { type: "Point" as const, coordinates },
  properties,
});

function ContextRecord({ item, monitor = false }: { item: ContextItem; monitor?: boolean }) {
  return <article className="evidence-context-record">
    <div><strong>{monitor ? `AQS monitor ${item.id}` : item.id}</strong>
      <span>{monitor ? `Measured annual PM2.5 · ${item.year}` : `${item.pollutant_code || "PM2.5"} · ${item.category || "EPA inventory record"} · ${item.inventory_year}`}</span>
      <small>{fmt(item.distance_km, 1)} km from selected point · {monitor ? "instrument-site distance" : "reported facility-coordinate distance"}</small>
    </div>
    <b>{monitor ? `${fmt(item.value_ug_m3, 2)} µg/m³` : `${fmt(item.emissions, 2)} ${item.units || ""}`}</b>
    {item.source_url && <a href={item.source_url} target="_blank" rel="noreferrer" aria-label={`Open provenance for ${item.id}`}><ExternalLink size={14}/></a>}
  </article>;
}

function EvidenceExplanation({ place, year }: { place: NationalPlace; year: number }) {
  const estimate = place.model_estimates?.[String(year)];
  const explanation = place.evidence_explanation;
  return <section className="detail-section evidence-explanation">
    <div className="section-title-line"><h3>Why this estimate?</h3><span>{explanation?.period || `Annual ${year}`}</span></div>
    <p>{explanation?.why_this_appears || (estimate ? `A released annual PM2.5 estimate is available for ${year}.` : `No model estimate is published for this place in ${year}.`)}</p>
    {estimate && <dl>
      <div><dt>Method</dt><dd>{explanation?.method || "Nearest eligible EPA AQS monitor"}</dd></div>
      <div><dt>Supporting monitor</dt><dd>AQS {estimate.reference_monitor_id || "ID unavailable"} · {fmt(estimate.nearest_monitor_km, 1)} km away{estimate.reference_monitor_value_ug_m3 != null ? ` · ${fmt(estimate.reference_monitor_value_ug_m3, 2)} µg/m³` : ""}</dd></div>
      <div><dt>Location</dt><dd>{explanation?.location_meaning || "Census Gazetteer internal point; not a place average."}</dd></div>
      <div><dt>Uncertainty</dt><dd>{explanation?.uncertainty_interpretation || "Spatial out-of-fold monitor-site error band; not a local guarantee."}</dd></div>
    </dl>}
    {!estimate && <p>{place.withheld_reason || `The release has no supported estimate for ${year}.`}</p>}
    <p className="evidence-limits">Does not establish: {(explanation?.does_not_establish || ["current conditions", "citywide concentration", "personal exposure", "source contribution or responsibility"]).join("; ")}.</p>
  </section>;
}

function SourceContext({ data, loading, error, radius, onRadiusChange }: { data: ContextResponse | null; loading: boolean; error: string; radius: number; onRadiusChange: (radius: number) => void }) {
  return <section className="detail-section source-context">
    <div className="section-title-line"><div><h3>Nearby documented evidence</h3><span>{data ? `${data.counts.measured_monitor_summaries} monitor summaries · ${data.counts.distinct_facilities} facilities` : "AQS + EPA inventory"}</span></div>
      <label className="context-radius"><span>Radius</span><select aria-label="Context search radius" value={radius} onChange={(event)=>onRadiusChange(Number(event.target.value))}><option value={25}>25 km</option><option value={50}>50 km</option><option value={100}>100 km</option><option value={250}>250 km</option></select></label>
    </div>
    {loading && <p className="muted-note" role="status">Updating evidence for the selected radius and year…</p>}
    {error && <p className="muted-note" role="status">{error}</p>}
    {!loading && !error && data && <>
      <div className="monitoring-gap" role="status"><strong>{data.monitoring_gap.monitor_summary_count ? `${data.monitoring_gap.monitor_summary_count} AQS annual site summaries in ${data.provenance.monitor_year}` : `No AQS annual site summary within ${radius} km for ${data.provenance.monitor_year}`}</strong><span>{data.monitoring_gap.meaning}</span></div>
      {data.nearest_monitors.length > 0 && <div className="context-group"><h4>Closest monitor summaries</h4>{data.nearest_monitors.slice(0,4).map((item,index)=><ContextRecord key={`m:${item.id}:${index}`} item={item} monitor/>)}</div>}
      {data.closest_facilities.length > 0 && <div className="context-group"><h4>Closest inventoried facilities</h4>{data.closest_facilities.slice(0,4).map((item,index)=><ContextRecord key={`c:${item.id}:${index}`} item={item}/>)}</div>}
      {data.largest_compatible_inventory_groups.map((group)=><div className="context-group" key={`${group.pollutant_code}:${group.units}`}><h4>Largest compatible inventory rows <span>{group.pollutant_code} · {group.units} · {group.compatible_record_count} rows</span></h4>{group.records.slice(0,4).map((item,index)=><ContextRecord key={`l:${item.id}:${index}`} item={item}/>)}</div>)}
      {!data.nearest_monitors.length && !data.closest_facilities.length && <p className="muted-note">No qualifying summaries or inventory rows were found within {radius} km.</p>}
      <p className="source-disclaimer">EPA AQS values are measured annual concentrations at monitor sites. EPA NEI rows are annual reported emissions; closest and largest describe inventory records only. Neither distance nor emissions magnitude establishes local contribution or responsibility. No compatible wind-linked evidence is available here to rank likely contributors.</p>
    </>}
  </section>;
}

const getSafeBounds = (m: MapLibreMap): [number, number, number, number] => {
  const b = m.getBounds();
  let w = b.getWest();
  let e = b.getEast();
  let s = Math.max(-85, Math.min(85, b.getSouth()));
  let n = Math.max(-85, Math.min(85, b.getNorth()));
  if (e - w >= 360) {
    w = -180;
    e = 180;
  } else {
    while (w < -180 && e < -180) { w += 360; e += 360; }
    while (w > 180 && e > 180) { w -= 360; e -= 360; }
    w = Math.max(-180, Math.min(180, w));
    e = Math.max(-180, Math.min(180, e));
    if (w > e) {
      w = -180;
      e = 180;
    }
  }
  if (s > n) { const t = s; s = n; n = t; }
  return [Number(w.toFixed(5)), Number(s.toFixed(5)), Number(e.toFixed(5)), Number(n.toFixed(5))];
};

function EvidenceMap({
  year, layer, showSources, initialCamera, selected, selectedPoint, onSelect, onCluster, onBounds, onCamera, places, monitors, sources,
}: {
  year: number; layer: Layer; showSources: boolean; initialCamera: CameraState | null; selected: NationalPlace | null; selectedPoint: [number, number] | null;
  onSelect: (kind: Layer, id: string, coords?: [number, number], item?: ViewportItem) => void;
  onCluster: (kind: Layer, id: string, count: number, coordinates: [number, number]) => void;
  onBounds: (bounds: [number, number, number, number], zoom: number) => void;
  onCamera: (camera: CameraState) => void;
  places: ViewportItem[]; monitors: ViewportItem[]; sources: ViewportItem[];
}) {
  const target = useRef<HTMLDivElement>(null);
  const map = useRef<MapLibreMap | null>(null);
  const callbacks = useRef({ onBounds, onSelect, onCluster, onCamera });
  useEffect(() => { callbacks.current = { onBounds, onSelect, onCluster, onCamera }; }, [onBounds, onSelect, onCluster, onCamera]);
  const [tileError, setTileError] = useState(false);
  const [areaMode, setAreaMode] = useState(false);
  const areaStart = useRef<{ x: number; y: number } | null>(null);
  const [areaRect, setAreaRect] = useState<{ left: number; top: number; width: number; height: number } | null>(null);
  const [ready, setReady] = useState(false);
  useEffect(() => {
    if (!target.current) return;
    let restoreCamera: (() => void) | undefined;
    const m = new MapLibreMap({
      container: target.current,
      style: { version: 8, sources: { osm: { type: "raster", tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"], tileSize: 256, attribution: "© OpenStreetMap contributors" } }, layers: [{ id: "base", type: "raster", source: "osm" }] },
      center: initialCamera ? [initialCamera.longitude, initialCamera.latitude] : [-98.5, 39.8], zoom: initialCamera?.zoom ?? 3.1,
      bearing: initialCamera?.bearing ?? 0, pitch: initialCamera?.pitch ?? 0, minZoom: 2, maxZoom: 15, attributionControl: { compact: true },
    });
    map.current = m;
    m.on("error", (event: ErrorEvent) => {
      const mapEvent = event as ErrorEvent & { sourceId?: string; tile?: unknown };
      if (event.error && (mapEvent.sourceId === "osm" || mapEvent.tile || /tile|raster/i.test(event.error.message || ""))) setTileError(true);
    });
    m.on("load", () => {
      m.addSource("countries", { type: "geojson", data: "/countries.geojson" });
      // Keep unsupported countries legible on the basemap. A large opaque mask
      // made the map look disabled and obscured the geography it was meant to
      // explain, so coverage is communicated with a quiet tint and boundary.
      m.addLayer({ id: "country-coverage", type: "fill", source: "countries", filter: ["!=", ["get", "iso_a2"], "US"], paint: { "fill-color": "#66727a", "fill-opacity": 0.035 } });
      m.addLayer({ id: "country-supported", type: "fill", source: "countries", filter: ["==", ["get", "iso_a2"], "US"], paint: { "fill-color": "#2a8f82", "fill-opacity": 0.035 } });
      m.addLayer({ id: "country-borders", type: "line", source: "countries", paint: { "line-color": "#627079", "line-width": ["interpolate", ["linear"], ["zoom"], 2, 0.45, 8, 1.1], "line-opacity": 0.5 } });
      m.addLayer({ id: "country-unavailable-boundary", type: "line", source: "countries", filter: ["!=", ["get", "iso_a2"], "US"], paint: { "line-color": "#64736f", "line-width": ["interpolate", ["linear"], ["zoom"], 2, 0.7, 8, 1.25], "line-opacity": 0.58, "line-dasharray": [2, 2] } });
      m.addSource("places", { type: "geojson", data: { type: "FeatureCollection", features: [] } });
      m.addSource("monitors", { type: "geojson", data: { type: "FeatureCollection", features: [] } });
      m.addSource("facilities", { type: "geojson", data: { type: "FeatureCollection", features: [] } });
      m.addSource("selected-marker", { type: "geojson", data: { type: "FeatureCollection", features: [] } });
      m.addSource("hover-marker", { type: "geojson", data: { type: "FeatureCollection", features: [] } });

      m.addLayer({
        id: "place-clusters",
        type: "circle",
        source: "places",
        filter: ["==", ["get", "is_cluster"], true],
        paint: {
          "circle-color": "#1f6e63",
          "circle-radius": [
            "interpolate", ["linear"], ["get", "member_count"],
            2, 11,
            10, 13,
            50, 16,
            200, 19,
            1000, 23
          ],
          "circle-opacity": 0.9,
          "circle-stroke-color": "#ffffff",
          "circle-stroke-width": 2,
        },
      });
      m.addLayer({
        id: "place-cluster-count",
        type: "symbol",
        source: "places",
        filter: ["==", ["get", "is_cluster"], true],
        layout: {
          "text-field": ["to-string", ["get", "member_count"]],
          "text-size": 10.5,
          "text-allow-overlap": true,
        },
        paint: { "text-color": "#ffffff" },
      });
      m.addLayer({
        id: "place-estimates",
        type: "circle",
        source: "places",
        filter: ["!=", ["get", "is_cluster"], true],
        paint: {
          "circle-radius": [
            "interpolate", ["linear"], ["zoom"],
            2, 3,
            3.5, 4.2,
            5.5, 5.8,
            7.5, 7.5,
            9.5, 9.5
          ],
          "circle-color": [
            "case",
            ["==", ["to-number", ["get", "value"], -1], -1],
            "#8ea19d",
            [
              "step",
              ["to-number", ["get", "value"], 0],
              "#2da895",
              6,
              "#dfa338",
              10,
              "#d6533f"
            ]
          ],
          "circle-opacity": 0.88,
          "circle-stroke-width": [
            "interpolate", ["linear"], ["zoom"],
            2, 0.9,
            5, 1.4,
            8, 1.8
          ],
          "circle-stroke-color": "#ffffff",
          "circle-stroke-opacity": 0.95,
        },
      });
      m.addLayer({
        id: "monitor-clusters",
        type: "circle",
        source: "monitors",
        filter: ["==", ["get", "is_cluster"], true],
        paint: {
          "circle-color": "#1e608f",
          "circle-radius": [
            "interpolate", ["linear"], ["get", "member_count"],
            2, 11,
            10, 13,
            50, 16,
            200, 19,
            1000, 23
          ],
          "circle-opacity": 0.92,
          "circle-stroke-color": "#ffffff",
          "circle-stroke-width": 2,
        },
      });
      m.addLayer({
        id: "monitor-cluster-count",
        type: "symbol",
        source: "monitors",
        filter: ["==", ["get", "is_cluster"], true],
        layout: {
          "text-field": ["to-string", ["get", "member_count"]],
          "text-size": 10.5,
          "text-allow-overlap": true,
        },
        paint: { "text-color": "#ffffff" },
      });
      m.addLayer({
        id: "monitor-points",
        type: "circle",
        source: "monitors",
        filter: ["!=", ["get", "is_cluster"], true],
        paint: {
          "circle-radius": [
            "interpolate", ["linear"], ["zoom"],
            2, 3.5,
            4, 5,
            7, 7,
            9, 9
          ],
          "circle-color": "#2c7ab3",
          "circle-stroke-width": 1.6,
          "circle-stroke-color": "#ffffff",
          "circle-opacity": 0.92,
        },
      });
      m.addLayer({
        id: "facility-clusters",
        type: "circle",
        source: "facilities",
        filter: ["==", ["get", "is_cluster"], true],
        paint: {
          "circle-color": "#b85333",
          "circle-radius": [
            "interpolate", ["linear"], ["get", "member_count"],
            2, 11,
            10, 13,
            50, 16,
            200, 19,
            1000, 23
          ],
          "circle-opacity": 0.92,
          "circle-stroke-color": "#ffffff",
          "circle-stroke-width": 2,
        },
      });
      m.addLayer({
        id: "facility-cluster-count",
        type: "symbol",
        source: "facilities",
        filter: ["==", ["get", "is_cluster"], true],
        layout: {
          "text-field": ["to-string", ["get", "member_count"]],
          "text-size": 10.5,
          "text-allow-overlap": true,
        },
        paint: { "text-color": "#ffffff" },
      });
      m.addLayer({
        id: "facility-points",
        type: "circle",
        source: "facilities",
        filter: ["!=", ["get", "is_cluster"], true],
        paint: {
          "circle-radius": [
            "interpolate", ["linear"], ["zoom"],
            2, 3,
            4, 4.5,
            7, 6,
            9, 8
          ],
          "circle-color": "#d96543",
          "circle-stroke-color": "#ffffff",
          "circle-stroke-width": 1.5,
          "circle-opacity": 0.92,
        },
      });
      m.addLayer({
        id: "hover-marker-halo",
        type: "circle",
        source: "hover-marker",
        paint: {
          "circle-radius": ["interpolate", ["linear"], ["zoom"], 2, 7, 5, 10, 8, 14],
          "circle-color": "#1f6f7d",
          "circle-opacity": 0.25,
          "circle-stroke-width": 1.5,
          "circle-stroke-color": "#123f4a",
          "circle-stroke-opacity": 0.75,
        },
      });
      m.addLayer({
        id: "selected-marker-halo",
        type: "circle",
        source: "selected-marker",
        paint: {
          "circle-radius": ["interpolate", ["linear"], ["zoom"], 3, 13, 8, 20],
          "circle-color": "#123f4a",
          "circle-opacity": 0.22,
          "circle-stroke-width": 2,
          "circle-stroke-color": "#123f4a",
          "circle-stroke-opacity": 0.85,
        },
      });
      m.addLayer({
        id: "selected-marker-dot",
        type: "circle",
        source: "selected-marker",
        paint: {
          "circle-radius": ["interpolate", ["linear"], ["zoom"], 3, 5.5, 8, 8],
          "circle-color": "#ffffff",
          "circle-stroke-width": 3,
          "circle-stroke-color": "#123f4a",
        },
      });
      const interactiveLayers = [
        "place-estimates", "place-clusters", "place-cluster-count",
        "monitor-clusters", "monitor-cluster-count", "monitor-points",
        "facility-clusters", "facility-cluster-count", "facility-points",
      ];
      let lastClickTimestamp = 0;
      const handleFeatureHit = (f: any) => {
        const now = Date.now();
        if (now - lastClickTimestamp < 60) return;
        lastClickTimestamp = now;

        const layerId = String(f.layer?.id || "");
        if (f.properties?.is_cluster) {
          const coordinates = (f.geometry as GeoJSON.Point).coordinates as [number, number];
          const kind: Layer = layerId.startsWith("place-") ? "estimates" : layerId.startsWith("monitor-") ? "monitors" : "sources";
          callbacks.current.onCluster(kind, String(f.properties.cluster_id), Number(f.properties.member_count), coordinates);
          m.easeTo({ center: coordinates, zoom: Math.min(15, m.getZoom() + 2), duration: 380 });
          return;
        }
        const coords = (f.geometry as GeoJSON.Point).coordinates as [number, number];
        const properties = normalizeItem<ViewportItem>(f.properties);
        const featureId = String(properties?.id ?? f.id ?? "");
        const kind: Layer = layerId.startsWith("place-") ? "estimates" : layerId.startsWith("monitor-") ? "monitors" : "sources";
        callbacks.current.onSelect(kind, featureId, coords, properties);
      };

      const clearHover = () => {
        (m.getSource("hover-marker") as MapGeoJSONSource | undefined)?.setData({
          type: "FeatureCollection",
          features: [],
        } as GeoJSON.FeatureCollection);
      };

      for (const id of interactiveLayers) {
        m.on("click", id, (ev: MapLayerMouseEvent) => {
          const f = ev.features?.[0];
          if (f) handleFeatureHit(f);
        });
        m.on("mousemove", id, (ev: MapLayerMouseEvent) => {
          m.getCanvas().style.cursor = "pointer";
          const f = ev.features?.[0];
          if (f && f.geometry.type === "Point") {
            const coords = (f.geometry as GeoJSON.Point).coordinates as [number, number];
            (m.getSource("hover-marker") as MapGeoJSONSource | undefined)?.setData({
              type: "FeatureCollection",
              features: [pointFeature(coords, {})],
            } as GeoJSON.FeatureCollection);
          }
        });
        m.on("mouseleave", id, () => {
          m.getCanvas().style.cursor = "";
          clearHover();
        });
      }
      m.getCanvas().addEventListener("mouseleave", clearHover);

      m.on("click", (ev: MapLayerMouseEvent) => {
        if (Date.now() - lastClickTimestamp < 60) return;
        const bbox: [[number, number], [number, number]] = [
          [ev.point.x - 9, ev.point.y - 9],
          [ev.point.x + 9, ev.point.y + 9],
        ];
        const activeLayers = interactiveLayers.filter((id) => {
          try {
            return m.getLayer(id) && m.getLayoutProperty(id, "visibility") !== "none";
          } catch {
            return false;
          }
        });
        const hits = m.queryRenderedFeatures(bbox, { layers: activeLayers });
        if (hits && hits.length > 0) {
          handleFeatureHit(hits[0]);
        }
      });
      m.on("moveend", () => {
        callbacks.current.onBounds(getSafeBounds(m), m.getZoom());
        const center = m.getCenter();
        if (target.current) { target.current.dataset.longitude = center.lng.toFixed(4); target.current.dataset.latitude = center.lat.toFixed(4); target.current.dataset.zoom = m.getZoom().toFixed(2); }
        callbacks.current.onCamera({ longitude: center.lng, latitude: center.lat, zoom: m.getZoom(), bearing: m.getBearing(), pitch: m.getPitch() });
      });
      restoreCamera = () => {
        const camera = readCamera(new URLSearchParams(location.search));
        if (camera) m.jumpTo({ center: [camera.longitude, camera.latitude], zoom: camera.zoom, bearing: camera.bearing, pitch: camera.pitch });
        else m.jumpTo({ center: [-98.5, 39.8], zoom: 3.1, bearing: 0, pitch: 0 });
      };
      window.addEventListener("popstate", restoreCamera);
      m.on("boxzoomend", () => setAreaMode(false));
      setReady(true);
      callbacks.current.onBounds(getSafeBounds(m), m.getZoom());
      const center = m.getCenter();
      if (target.current) { target.current.dataset.longitude = center.lng.toFixed(4); target.current.dataset.latitude = center.lat.toFixed(4); target.current.dataset.zoom = m.getZoom().toFixed(2); }
      callbacks.current.onCamera({ longitude: center.lng, latitude: center.lat, zoom: m.getZoom(), bearing: m.getBearing(), pitch: m.getPitch() });
    });
    return () => { if (restoreCamera) window.removeEventListener("popstate", restoreCamera); m.remove(); map.current = null; };
  }, []);
  useEffect(() => {
    if (!ready || !map.current) return;
    const features = places.map((p) => {
      const rawVal = p.value ?? p.estimate?.value_ug_m3 ?? p.model_estimates?.[String(year)]?.value_ug_m3;
      const numVal = typeof rawVal === "number" && Number.isFinite(rawVal) ? rawVal : null;
      return pointFeature(
        [p.render_longitude ?? p.longitude, p.render_latitude ?? p.latitude],
        { ...p, id: String(p.id), value: numVal }
      );
    });
    (map.current.getSource("places") as MapGeoJSONSource | undefined)?.setData({ type: "FeatureCollection", features } as GeoJSON.FeatureCollection);
  }, [places, year, ready]);
  useEffect(() => {
    if (!ready || !map.current) return;
    const features = monitors.map((p) => {
      const rawVal = p.value ?? p.pm25_ug_m3;
      const numVal = typeof rawVal === "number" && Number.isFinite(rawVal) ? rawVal : null;
      return pointFeature(
        [p.render_longitude ?? p.longitude, p.render_latitude ?? p.latitude],
        { ...p, id: String(p.id), name: p.name ?? p.id, value: numVal }
      );
    });
    (map.current.getSource("monitors") as MapGeoJSONSource | undefined)?.setData({ type: "FeatureCollection", features } as GeoJSON.FeatureCollection);
  }, [monitors, ready]);
  useEffect(() => {
    if (!ready || !map.current) return;
    const features = sources.map((p) => {
      const rawVal = p.value ?? p.emissions;
      const numVal = typeof rawVal === "number" && Number.isFinite(rawVal) ? rawVal : null;
      return pointFeature(
        [p.render_longitude ?? p.longitude, p.render_latitude ?? p.latitude],
        { ...p, id: String(p.id), name: p.name, value: numVal }
      );
    });
    (map.current.getSource("facilities") as MapGeoJSONSource | undefined)?.setData({ type: "FeatureCollection", features } as GeoJSON.FeatureCollection);
  }, [sources, ready]);
  useEffect(() => {
    const m = map.current; if (!ready || !m) return;
    const showPlaces = layer === "estimates";
    const showMonitors = layer === "monitors";
    const showFacilities = layer === "sources" || showSources;
    for (const id of ["place-estimates", "place-clusters", "place-cluster-count"]) m.setLayoutProperty(id, "visibility", showPlaces ? "visible" : "none");
    for (const id of ["monitor-clusters", "monitor-cluster-count", "monitor-points"]) m.setLayoutProperty(id, "visibility", showMonitors ? "visible" : "none");
    for (const id of ["facility-clusters", "facility-cluster-count", "facility-points"]) m.setLayoutProperty(id, "visibility", showFacilities ? "visible" : "none");
    (m.getSource("hover-marker") as MapGeoJSONSource | undefined)?.setData({ type: "FeatureCollection", features: [] } as GeoJSON.FeatureCollection);
  }, [layer, showSources, ready]);
  useEffect(() => {
    if (!ready || !map.current) return;
    const source = map.current.getSource("selected-marker") as MapGeoJSONSource | undefined;
    const target = selectedPoint || (selected ? [((selected as any).render_longitude ?? selected.longitude), ((selected as any).render_latitude ?? selected.latitude)] as [number, number] : null);
    if (target) {
      source?.setData({ type: "FeatureCollection", features: [pointFeature(target, {})] } as GeoJSON.FeatureCollection);
      const cameraInUrl = readCamera(new URLSearchParams(location.search));
      if (!cameraInUrl) map.current.flyTo({ center: target, zoom: Math.max(map.current.getZoom(), 7.5), speed: 1.15, curve: 1.35, essential: true });
    } else {
      source?.setData({ type: "FeatureCollection", features: [] } as GeoJSON.FeatureCollection);
    }
  }, [selectedPoint, selected?.longitude, selected?.latitude, (selected as any)?.render_longitude, (selected as any)?.render_latitude, ready]);
  const resetView = () => map.current?.easeTo({ center: [-98.5, 39.8], zoom: 3.1, bearing: 0, pitch: 0, duration: 500 });
  const areaPointer = (event: ReactPointerEvent<HTMLDivElement>) => {
    const rect = target.current?.getBoundingClientRect(); if (!rect) return;
    if (event.type === "pointerdown") { event.currentTarget.setPointerCapture(event.pointerId); areaStart.current = { x: event.clientX - rect.left, y: event.clientY - rect.top }; setAreaRect({ left: areaStart.current.x, top: areaStart.current.y, width: 0, height: 0 }); }
    else if (event.type === "pointermove" && areaStart.current) { const x = event.clientX - rect.left, y = event.clientY - rect.top; setAreaRect({ left: Math.min(x, areaStart.current.x), top: Math.min(y, areaStart.current.y), width: Math.abs(x - areaStart.current.x), height: Math.abs(y - areaStart.current.y) }); }
    else if (event.type === "pointerup" && areaStart.current && map.current) { const start = areaStart.current, end = { x: event.clientX - rect.left, y: event.clientY - rect.top }; areaStart.current = null; setAreaRect(null); setAreaMode(false); if (Math.abs(end.x - start.x) > 12 && Math.abs(end.y - start.y) > 12) { const a = map.current.unproject([start.x, start.y]), b = map.current.unproject([end.x, end.y]); map.current.fitBounds([[Math.min(a.lng,b.lng),Math.min(a.lat,b.lat)],[Math.max(a.lng,b.lng),Math.max(a.lat,b.lat)]], { padding: 42, duration: 420 }); } }
  };
  return <div className="national-map-wrap"><div className="national-map" ref={target} role="application" aria-label="Map of historical U.S. air quality evidence" />
    <div className={`map-area-capture${areaMode ? " active" : ""}`} onPointerDown={areaPointer} onPointerMove={areaPointer} onPointerUp={areaPointer} aria-hidden="true">{areaRect&&<span style={{left:areaRect.left,top:areaRect.top,width:areaRect.width,height:areaRect.height}}/>}</div>
    <div className="map-floating-controls" aria-label="Map controls">
      <button type="button" aria-label="Select map area" aria-pressed={areaMode} title={areaMode ? "Drag a rectangle to zoom into an area" : "Select an area to zoom into"} onClick={()=>setAreaMode((value)=>!value)}><SquareDashedMousePointer size={16}/></button>
      <button type="button" aria-label="Zoom in" title="Zoom in" onClick={() => map.current?.zoomIn()}><Plus size={16}/></button>
      <button type="button" aria-label="Zoom out" title="Zoom out" onClick={() => map.current?.zoomOut()}><Minus size={16}/></button>
      <button type="button" aria-label="Reset map view" title="Reset map view" onClick={resetView}><LocateFixed size={16}/></button>
    </div>
    {tileError && <div className="national-map-fallback"><strong>Map tiles are temporarily unavailable.</strong><span>Data, search, comparisons, and exports remain available. OpenStreetMap tiles require an internet connection.</span></div>}<div className="map-source-stamp">{layer === "estimates" ? `MODEL ESTIMATES · ${year}${showSources ? " + EPA NEI SOURCES" : ""}` : layer === "monitors" ? `EPA MONITORS · ${year}${showSources ? " + EPA NEI SOURCES" : ""}` : "EPA NEI FACILITIES · 2023"}</div></div>;
}

export default function NationalExplorer() {
  const params = new URLSearchParams(location.search);
  const [manifest, setManifest] = useState<NationalManifest | null>(null);
  const [places, setPlaces] = useState<NationalPlace[]>([]);
  const [visiblePlaces, setVisiblePlaces] = useState<ViewportItem[]>([]);
  const [monitors, setMonitors] = useState<any[]>([]);
  const [sources, setSources] = useState<any[]>([]);
  const [contextData, setContextData] = useState<ContextResponse | null>(null);
  const [contextLoading, setContextLoading] = useState(false);
  const [contextError, setContextError] = useState("");
  const [year, setYear] = useState(Number(params.get("year")) || 2024);
  const requestedLayer = params.get("layer");
  const [layer, setLayer] = useState<Layer>(requestedLayer === "monitors" || requestedLayer === "sources" ? requestedLayer : "estimates");
  const [showSources, setShowSources] = useState(params.get("sources") === "1" || requestedLayer === "combined");
  const [query, setQuery] = useState("");
  const [searchResults, setSearchResults] = useState<NationalPlace[]>([]);
  const [searchIndex, setSearchIndex] = useState(0);
  const [searchLoading, setSearchLoading] = useState(false);
  const searchRequest = useRef(0);
  const [active, setActive] = useState<{ kind: Layer; id: string } | null>(() => readFeature(params.get("feature")));
  const [activeMapItem, setActiveMapItem] = useState<ViewportItem | null>(null);
  const [selectedCluster, setSelectedCluster] = useState<ClusterSelection | null>(null);
  const [comparisonIds, setComparisonIds] = useState<string[]>(() => {
    const shared = params.get("compare");
    if (shared) return shared.split(",").filter((id) => /^\d{7}$/.test(id)).slice(0, 4);
    try { const stored = JSON.parse(localStorage.getItem("upwind-national-compare") || "[]"); return Array.isArray(stored) ? stored.filter((id) => typeof id === "string" && /^\d{7}$/.test(id)).slice(0, 4) : []; } catch { return []; }
  });
  const [selectedId, setSelectedId] = useState(params.get("place"));
  const [contextRadius, setContextRadius] = useState(() => {
    const requested = Number(params.get("radius"));
    return [25, 50, 100, 250].includes(requested) ? requested : 50;
  });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [mapDataError, setMapDataError] = useState("");
  const [searchError, setSearchError] = useState("");
  const [printError, setPrintError] = useState("");
  const [exportError, setExportError] = useState("");
  const [printSnapshot, setPrintSnapshot] = useState<NationalSnapshot | null>(null);
  const [tab, setTab] = useState<"place" | "methodology">("place");
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [shareCopied, setShareCopied] = useState(false);
  const searchTimer = useRef<number | undefined>(undefined);
  const viewportTimer = useRef<number | undefined>(undefined);
  const viewportRequest = useRef(0);
  const viewportController = useRef<AbortController | null>(null);
  const boundsRef = useRef<[number, number, number, number] | null>(null);
  const zoomRef = useRef(3);
  const cameraRef = useRef<CameraState | null>(readCamera(params));
  const cameraWriteTimer = useRef<number | undefined>(undefined);
  const [selectedPoint, setSelectedPoint] = useState<[number, number] | null>(null);
  const activePlace = useMemo(() => {
    if (active?.kind === "estimates") {
      const foundInPlaces = places.find((p) => isSameId(p.id, active.id));
      if (foundInPlaces) return foundInPlaces;
      const foundInVisible = visiblePlaces.find((p) => isSameId(p.id, active.id));
      if (foundInVisible) return normalizeItem<NationalPlace>(foundInVisible);
      if (activeMapItem && isSameId(activeMapItem.id, active.id)) return normalizeItem<NationalPlace>(activeMapItem);
    }
    if (selectedId) {
      const found = places.find((p) => isSameId(p.id, selectedId));
      if (found) return found;
    }
    return null;
  }, [active, places, visiblePlaces, activeMapItem, selectedId]);
  const availableYears = useMemo(() => Object.keys(manifest?.annual_monitor_audit || {}).map(Number).sort((a,b) => b-a), [manifest]);
  useEffect(() => {
    if (activePlace && !selectedPoint) {
      setSelectedPoint([((activePlace as any).render_longitude ?? activePlace.longitude), ((activePlace as any).render_latitude ?? activePlace.latitude)]);
    }
  }, [activePlace?.id, activePlace?.latitude, activePlace?.longitude, selectedPoint]);
  useEffect(() => { const clear = () => setPrintSnapshot(null); window.addEventListener("afterprint", clear); return () => window.removeEventListener("afterprint", clear); }, []);
  useEffect(() => {
    const handleKeyDown = (e: globalThis.KeyboardEvent) => {
      const tag = (e.target as HTMLElement)?.tagName?.toLowerCase();
      if (tag === "input" || tag === "select" || tag === "textarea") return;
      if (e.key === "[" || e.key === "\\") {
        e.preventDefault();
        setSidebarOpen((prev) => !prev);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  useEffect(() => {
    Promise.all([
      fetch(`${API}/manifest`).then((r) => { if (!r.ok) throw new Error("National release is not built yet."); return r.json(); }),
    ]).then(async ([m]) => {
      setManifest(m);
      const ids = [params.get("place"), ...comparisonIds].filter((id): id is string => !!id);
      const loaded = await Promise.all(ids.map((id) => fetch(`${API}/places?geoid=${encodeURIComponent(id)}&year=${year}`).then((r) => r.ok ? r.json() : ({items:[]})).catch(() => ({items:[]}))));
      setPlaces(loaded.flatMap((result) => result.items || []));
      setLoading(false);
    }).catch((e) => { setError(String(e)); setLoading(false); });
  }, []);
  useEffect(() => {
    const restore = () => {
      const p = new URLSearchParams(location.search);
      const restoredYear = Number(p.get("year"));
      const restoredLayer = p.get("layer");
      const ids = (p.get("compare") || "").split(",").filter((id) => /^\d{7}$/.test(id)).slice(0, 4);
      const place = p.get("place");
      setYear(Number.isFinite(restoredYear) && restoredYear > 0 ? restoredYear : 2024);
      setLayer(restoredLayer === "monitors" || restoredLayer === "sources" ? restoredLayer : "estimates");
      setShowSources(p.get("sources") === "1" || restoredLayer === "combined");
      setSelectedId(place && /^\d{7}$/.test(place) ? place : null);
      const restoredRadius = Number(p.get("radius"));
      setContextRadius([25, 50, 100, 250].includes(restoredRadius) ? restoredRadius : 50);
      setComparisonIds(ids);
      setActive(readFeature(p.get("feature")));
      setActiveMapItem(null);
      const requested = [...new Set([place, ...ids].filter((id): id is string => !!id && /^\d{7}$/.test(id)))];
      if (requested.length) Promise.all(requested.map((id) => fetch(`${API}/places?geoid=${encodeURIComponent(id)}&year=${restoredYear || 2024}`).then((r) => r.ok ? r.json() : ({items:[]})).catch(() => ({items:[]})))).then((rows) => setPlaces((old) => {
        const all = new Map(old.map((x) => [x.id, x]));
        rows.flatMap((x) => x.items || []).forEach((x: NationalPlace) => all.set(x.id, x));
        return [...all.values()];
      }));
    };
    window.addEventListener("popstate", restore);
    return () => window.removeEventListener("popstate", restore);
  }, []);
  useEffect(() => {
    if (!active || active.kind === "estimates") return;
    const endpoint = active.kind === "monitors"
      ? `${API}/monitors?site_id=${encodeURIComponent(active.id)}&year=-1`
      : `${API}/sources?facility_id=${encodeURIComponent(active.id)}&limit=100`;
    fetch(endpoint).then((response) => response.ok ? response.json() : null).then((body) => {
      const rows = (body?.items || []).map((row: any) => normalizeItem(row));
      if (active.kind === "monitors") setMonitors((old) => [...old.filter((row) => !isSameId(row.id, active.id)), ...rows]);
      else setSources((old) => [...old.filter((row) => !isSameId(row.id, active.id)), ...rows]);
      const first = rows[0];
      if (first) setSelectedPoint([first.longitude, first.latitude]);
    }).catch(() => undefined);
  }, [active?.kind, active?.id]);
  useEffect(() => {
    window.clearTimeout(searchTimer.current);
    if (!query.trim()) { setSearchResults([]); return; }
    searchTimer.current = window.setTimeout(() => {
      const [nameQuery, stateQuery] = query.split(",").map((part) => part.trim());
      const stateParam = stateQuery ? `&state=${encodeURIComponent(stateQuery)}` : "";
      const requestId = ++searchRequest.current;
      setSearchLoading(true);
      setSearchError("");
      fetch(`${API}/places?q=${encodeURIComponent(nameQuery)}${stateParam}&limit=30&year=${year}`)
        .then((r) => { if (!r.ok) throw new Error("Place search is temporarily unavailable."); return r.json(); })
        .then((d) => { if (requestId === searchRequest.current) { setSearchResults(d.items || []); setSearchIndex(0); } })
        .catch((e: Error) => { if (requestId === searchRequest.current) { setSearchResults([]); setSearchError(e.message); } })
        .finally(() => { if (requestId === searchRequest.current) setSearchLoading(false); });
    }, 180);
    return () => window.clearTimeout(searchTimer.current);
  }, [query, year]);
  useEffect(() => {
    const siteId = activePlace?.nearby_monitor?.monitor_id;
    if (!siteId) return;
    let cancelled = false;
    fetch(`${API}/monitors?site_id=${encodeURIComponent(siteId)}&year=-1`)
      .then((r) => r.json())
      .then((d) => { if (!cancelled) setMonitors((old) => [...old.filter((m) => m.id !== siteId), ...d.items]); })
      .catch(() => undefined);
    return () => { cancelled = true; };
  }, [activePlace?.nearby_monitor?.monitor_id]);
  useEffect(() => {
    if (!activePlace) {
      setContextData(null);
      setContextError("");
      return;
    }
    const controller = new AbortController();
    setContextLoading(true);
    setContextError("");
    const params = new URLSearchParams({
      latitude: String(activePlace.latitude),
      longitude: String(activePlace.longitude),
      radius_km: String(contextRadius),
      monitor_year: String(year),
      limit: "24",
    });
    fetch(`${API}/context?${params.toString()}`, { signal: controller.signal })
      .then((response) => {
        if (!response.ok) throw new Error("Nearby context is temporarily unavailable.");
        return response.json() as Promise<ContextResponse>;
      })
      .then((body) => setContextData(body))
      .catch((reason: unknown) => {
        if ((reason as Error)?.name !== "AbortError") {
          setContextData(null);
          setContextError("Nearby evidence context could not be loaded.");
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setContextLoading(false);
      });
    return () => controller.abort();
  }, [activePlace?.id, activePlace?.latitude, activePlace?.longitude, contextRadius, year]);
  const onBounds = useCallback((bounds: [number, number, number, number], zoom: number) => {
    boundsRef.current = bounds;
    zoomRef.current = zoom;
    window.clearTimeout(viewportTimer.current);
    viewportTimer.current = window.setTimeout(() => {
      const requestId = ++viewportRequest.current;
      viewportController.current?.abort();
      const controller = new AbortController();
      viewportController.current = controller;
      const [west, south, east, north] = bounds;
      const requestedLayers: Layer[] = [...new Set<Layer>([layer, ...(showSources && layer !== "sources" ? ["sources" as const] : [])])];
      const perLayerBudget = requestedLayers.length > 1 ? "1500" : "3000";
      const box = (requested: Layer) => new URLSearchParams({ west: String(west), south: String(south), east: String(east), north: String(north), zoom: String(zoom), year: String(year), layer: requested, budget: perLayerBudget }).toString();
      setMapDataError("");
      const current = () => requestId === viewportRequest.current && !controller.signal.aborted;
      Promise.all(requestedLayers.map((requested) => fetch(`${API}/viewport?${box(requested)}`, { signal: controller.signal }).then((r) => { if (!r.ok) throw new Error(); return r.json() as Promise<ViewportResult>; }).then((data) => [requested, data] as const))).then((entries) => {
        if (!current()) return;
        for (const [requested, data] of entries) {
          if (requested === "estimates") {
            setVisiblePlaces(data.items);
            setPlaces((old) => { const merged = new Map(old.map((p) => [p.id, p])); for (const item of data.items) if (!item.is_cluster) merged.set(item.id, item as unknown as NationalPlace); return [...merged.values()]; });
          } else if (requested === "monitors") setMonitors(data.items);
          else setSources(data.items);
        }
      }).catch((e) => { if (current() && e?.name !== "AbortError") setMapDataError("Map evidence could not be loaded. The previous view remains available; try moving the map again."); });
    }, 100);
  }, [year, layer, showSources]);
  const onCamera = useCallback((camera: CameraState) => {
    cameraRef.current = camera;
    window.clearTimeout(cameraWriteTimer.current);
    cameraWriteTimer.current = window.setTimeout(() => {
      const url = new URL(location.href);
      url.searchParams.set("v", "1");
      url.searchParams.set("camera", [camera.longitude.toFixed(4), camera.latitude.toFixed(4), camera.zoom.toFixed(2), camera.bearing.toFixed(1), camera.pitch.toFixed(1)].join(","));
      history.replaceState(null, "", `${url.pathname}${url.search}`);
    }, 180);
  }, []);
  useEffect(() => { if (boundsRef.current && !loading) onBounds(boundsRef.current, zoomRef.current); }, [year, layer, loading, onBounds]);
  const onMapSelect = useCallback((kind: Layer, id: string, coords?: [number, number], item?: ViewportItem) => {
    const normId = String(id).trim();
    const normalizedItem = item ? normalizeItem<ViewportItem>(item) : undefined;
    setSidebarOpen(true);
    setTab("place");
    setSelectedCluster(null);
    if (kind === "estimates") {
      setSelectedId(normId);
    } else {
      setSelectedId(null);
    }
    setActive({ kind, id: normId });
    const matched = normalizedItem || (
      kind === "estimates"
        ? visiblePlaces.find((p) => isSameId(p.id, normId)) || places.find((p) => isSameId(p.id, normId))
        : kind === "monitors"
        ? monitors.find((p) => isSameId(p.id, normId))
        : sources.find((p) => isSameId(p.id, normId))
    );
    const resolvedItem = matched ? normalizeItem<ViewportItem>(matched) : null;
    setActiveMapItem(resolvedItem);
    if (resolvedItem) {
      if (kind === "estimates") {
        setPlaces((old) => old.some((p) => isSameId(p.id, normId)) ? old.map((p) => isSameId(p.id, normId) ? { ...p, ...resolvedItem } : p) : [...old, resolvedItem as unknown as NationalPlace]);
      }
      if (kind === "monitors") {
        setMonitors((old) => old.some((p) => isSameId(p.id, normId)) ? old.map((p) => isSameId(p.id, normId) ? { ...p, ...resolvedItem } : p) : [...old, resolvedItem]);
      }
      if (kind === "sources") {
        setSources((old) => old.some((p) => isSameId(p.id, normId)) ? old.map((p) => isSameId(p.id, normId) ? { ...p, ...resolvedItem } : p) : [...old, resolvedItem]);
      }
    }
    if (coords) {
      setSelectedPoint(coords);
    } else if (resolvedItem) {
      const pt: [number, number] | null = (resolvedItem.render_longitude != null && resolvedItem.render_latitude != null)
        ? [resolvedItem.render_longitude, resolvedItem.render_latitude]
        : (resolvedItem.longitude != null && resolvedItem.latitude != null)
        ? [resolvedItem.longitude, resolvedItem.latitude]
        : null;
      if (pt) setSelectedPoint(pt);
    } else if (kind === "estimates") {
      const match = visiblePlaces.find((p) => isSameId(p.id, normId)) || places.find((p) => isSameId(p.id, normId));
      if (match) setSelectedPoint([((match as any).render_longitude ?? match.longitude), ((match as any).render_latitude ?? match.latitude)]);
    } else if (kind === "monitors") {
      const match = monitors.find((m) => isSameId(m.id, normId));
      if (match) setSelectedPoint([((match as any).render_longitude ?? match.longitude), ((match as any).render_latitude ?? match.latitude)]);
    } else if (kind === "sources") {
      const match = sources.find((s) => isSameId(s.id, normId));
      if (match) setSelectedPoint([((match as any).render_longitude ?? match.longitude), ((match as any).render_latitude ?? match.latitude)]);
    }
    if (kind === "estimates") {
      fetch(`${API}/places?geoid=${encodeURIComponent(normId)}&year=${year}`)
        .then((response) => response.ok ? response.json() : null)
        .then((body) => {
          const detail = body?.items?.[0] as NationalPlace | undefined;
          if (!detail) return;
          const normDetail = normalizeItem<NationalPlace>(detail);
          setPlaces((old) => {
            const merged = new Map(old.map((place) => [String(place.id), place]));
            merged.set(String(normDetail.id), { ...merged.get(String(normDetail.id)), ...normDetail });
            return [...merged.values()];
          });
        }).catch(() => undefined);
    }
  }, [visiblePlaces, places, monitors, sources, year]);
  const onCluster = useCallback((kind: Layer, id: string, count: number, coordinates: [number, number]) => {
    setSidebarOpen(true);
    setTab("place");
    setActive(null);
    setActiveMapItem(null);
    setSelectedId(null);
    setSelectedPoint(coordinates);
    const bounds = boundsRef.current;
    const selection: ClusterSelection = { kind, id, count, members: [], nextOffset: 0, loading: true };
    setSelectedCluster(selection);
    if (!bounds) return;
    const [west, south, east, north] = bounds;
    const params = new URLSearchParams({ layer: kind, cluster_id: id, west: String(west), south: String(south), east: String(east), north: String(north), year: String(year), offset: "0", limit: "50" });
    fetch(`${API}/viewport-members?${params}`).then((r) => { if (!r.ok) throw new Error(); return r.json(); }).then((d) => setSelectedCluster((old) => old?.id === id ? { ...old, members: d.items, nextOffset: d.next_offset, count: d.total, loading: false } : old)).catch(() => setSelectedCluster((old) => old?.id === id ? { ...old, loading: false, nextOffset: null } : old));
  }, [year]);
  const loadMoreClusterMembers = () => {
    if (!selectedCluster || selectedCluster.nextOffset == null || !boundsRef.current) return;
    const [west, south, east, north] = boundsRef.current;
    const offset = selectedCluster.nextOffset;
    const params = new URLSearchParams({ layer: selectedCluster.kind, cluster_id: selectedCluster.id, west: String(west), south: String(south), east: String(east), north: String(north), year: String(year), offset: String(offset), limit: "50" });
    setSelectedCluster({ ...selectedCluster, loading: true });
    fetch(`${API}/viewport-members?${params}`).then((r) => { if (!r.ok) throw new Error(); return r.json(); }).then((d) => setSelectedCluster((old) => old?.id === selectedCluster.id ? { ...old, members: [...old.members, ...d.items], nextOffset: d.next_offset, loading: false } : old)).catch(() => setSelectedCluster((old) => old?.id === selectedCluster.id ? { ...old, loading: false } : old));
  };
  useEffect(() => {
    if (!manifest) return;
    const search = new URLSearchParams(); search.set("year", String(year)); search.set("layer", layer);
    if (showSources) search.set("sources", "1");
    if (selectedId) search.set("place", selectedId);
    if (active && active.kind !== "estimates") search.set("feature", `${active.kind}:${active.id}`);
    if (comparisonIds.length) search.set("compare", comparisonIds.join(","));
    search.set("radius", String(contextRadius));
    if (cameraRef.current) {
      search.set("v", "1");
      search.set("camera", [cameraRef.current.longitude.toFixed(4), cameraRef.current.latitude.toFixed(4), cameraRef.current.zoom.toFixed(2), cameraRef.current.bearing.toFixed(1), cameraRef.current.pitch.toFixed(1)].join(","));
    }
    const next = `${location.pathname}?${search.toString()}`;
    if (`${location.pathname}${location.search}` !== next) history.replaceState(null, "", next);
  }, [manifest,year,layer,showSources,selectedId,active?.kind,active?.id,comparisonIds,contextRadius]);
  const selectedMonitor = useMemo(() => {
    if (active?.kind !== "monitors") return null;
    const found = monitors.find((m) => isSameId(m.id, active.id));
    if (found) return normalizeItem<Monitor>(found);
    if (activeMapItem && isSameId(activeMapItem.id, active.id)) return normalizeItem<Monitor>(activeMapItem);
    return null;
  }, [active, monitors, activeMapItem]);

  const selectedFacility = useMemo(() => {
    if (active?.kind !== "sources") return null;
    const found = sources.find((s) => isSameId(s.id, active.id));
    if (found) return normalizeItem<Facility>(found);
    if (activeMapItem && isSameId(activeMapItem.id, active.id)) return normalizeItem<Facility>(activeMapItem);
    return null;
  }, [active, sources, activeMapItem]);

  const nearbyMonitors = useMemo(() => activePlace?.nearby_monitor ? monitors.filter((m) => isSameId(m.id, activePlace.nearby_monitor?.monitor_id)).sort((a,b)=>a.year-b.year) : [], [activePlace,monitors]);
  const nearbyYearMonitor = useMemo(() => nearbyMonitors.find((m) => m.year === year), [nearbyMonitors, year]);
  const chartData = nearbyMonitors.map((m) => ({ year: m.year, measured: m.pm25_ug_m3 }));
  const comparisons = comparisonIds.map((id) => places.find((p) => isSameId(p.id, id))).filter((p): p is NationalPlace => !!p);
  const comparisonPlaces = activePlace && !comparisons.some((p) => isSameId(p.id, activePlace.id)) ? [activePlace, ...comparisons] : comparisons;
  const ranking = useMemo(() => places.filter((p) => p.model_estimates?.[String(year)]).sort((a,b)=>(b.model_estimates?.[String(year)]?.value_ug_m3 || 0)-(a.model_estimates?.[String(year)]?.value_ug_m3 || 0)).slice(0,8), [places,year]);
  const selectPlace = (place: NationalPlace) => {
    setSidebarOpen(true);
    setActiveMapItem(null);
    history.pushState(null, "", `${location.pathname}?${new URLSearchParams({year:String(year),layer,place:String(place.id),...(comparisonIds.length?{compare:comparisonIds.join(",")}:{})}).toString()}`);
    setPlaces((old) => old.some((p) => isSameId(p.id, place.id)) ? old : [...old, place]);
    setSelectedId(String(place.id));
    setActive({ kind: "estimates", id: String(place.id) });
    setSelectedPoint([((place as any).render_longitude ?? place.longitude), ((place as any).render_latitude ?? place.latitude)]);
    setQuery("");
    setSearchResults([]);
    setTab("place");
  };
  const closeDetail = () => {
    setActive(null);
    setActiveMapItem(null);
    setSelectedId(null);
    setSelectedPoint(null);
    setSelectedCluster(null);
  };
  const toggleCompare = (id: string) => {
    const next = comparisonIds.some((cid) => isSameId(cid, id)) ? comparisonIds.filter((x) => !isSameId(x, id)) : comparisonIds.length < 4 ? [...comparisonIds, id] : [...comparisonIds.slice(1), id];
    history.pushState(null, "", `${location.pathname}?${new URLSearchParams({year:String(year),layer,...(selectedId?{place:selectedId}:{}),...(next.length?{compare:next.join(",")}:{})}).toString()}`);
    localStorage.setItem("upwind-national-compare",JSON.stringify(next)); setComparisonIds(next);
  };
  const snapshotIds = [...new Set([selectedId, ...comparisonIds].filter((id): id is string => !!id))].slice(0, 5);
  const snapshotUrl = (format: "json" | "csv" | "geojson") => `${API}/snapshot${format === "json" ? "" : `.${format}`}?geoids=${snapshotIds.join(",")}&year=${year}`;
  const exportSnapshot = async (format: "csv" | "geojson") => {
    if (!snapshotIds.length) return;
    setExportError("");
    try {
      const response = await fetch(snapshotUrl(format));
      if (!response.ok) throw new Error("The selected place snapshot could not be exported.");
      const filename = response.headers.get("content-disposition")?.match(/filename\*?=(?:UTF-8''|\")?([^\";]+)/i)?.[1];
      const link = document.createElement("a"); const href = URL.createObjectURL(await response.blob());
      link.href = href; link.download = filename ? decodeURIComponent(filename.replaceAll('"', "")) : `upwind-national-${year}-snapshot.${format}`;
      document.body.appendChild(link); link.click(); link.remove(); window.setTimeout(() => URL.revokeObjectURL(href), 1000);
    } catch { setExportError("Export could not be loaded. Check the connection and try again."); }
  };
  const printBrief = async () => {
    setPrintError("");
    if (!snapshotIds.length) { window.print(); return; }
    try {
      const response = await fetch(snapshotUrl("json"));
      if (!response.ok) throw new Error("The print snapshot could not be prepared.");
      setPrintSnapshot(await response.json() as NationalSnapshot);
      window.setTimeout(() => window.print(), 50);
    } catch { setPrintError("The print snapshot could not be loaded. Check the connection and try again."); }
  };
  const share = async () => {
    const url = new URL(location.href);
    if (cameraRef.current) {
      url.searchParams.set("v", "1");
      url.searchParams.set("camera", [cameraRef.current.longitude.toFixed(4), cameraRef.current.latitude.toFixed(4), cameraRef.current.zoom.toFixed(2), cameraRef.current.bearing.toFixed(1), cameraRef.current.pitch.toFixed(1)].join(","));
    }
    try { await navigator.clipboard.writeText(url.toString()); setShareCopied(true); window.setTimeout(() => setShareCopied(false), 2200); } catch { window.prompt("Copy this link",url.toString()); }
  };
  const onSearchKey = (event: KeyboardEvent<HTMLInputElement>) => { if (event.key === "ArrowDown" && searchResults.length) { event.preventDefault(); setSearchIndex((i)=>(i+1)%searchResults.length); } else if (event.key === "ArrowUp" && searchResults.length) { event.preventDefault(); setSearchIndex((i)=>(i+searchResults.length-1)%searchResults.length); } else if (event.key === "Enter" && searchResults[searchIndex]) selectPlace(searchResults[searchIndex]); if (event.key === "Escape") { setQuery(""); setSearchResults([]); } };

  return <main className={`national-shell${sidebarOpen ? "" : " sidebar-collapsed"}`}>
    {printSnapshot && <section className="print-snapshot" aria-label="Printable evidence snapshot"><header><strong>UPWIND · Historical air quality evidence</strong><span>Release {printSnapshot.release} · built {printSnapshot.built_utc || "not recorded"} · generated {printSnapshot.generated_utc || "not recorded"}</span></header><h1>Place evidence · {printSnapshot.year}</h1><p>PM2.5 annual mean at Census Gazetteer internal points. These are point estimates, not place averages, current conditions, exposure, forecasts, or source attribution. The empirical spatial out-of-fold interval does not guarantee local coverage.</p><div className="print-snapshot-grid">{printSnapshot.items.map((item) => <article key={item.id}><h2>{item.name}, {item.state}</h2><p>GEOID {item.id} · {item.place_type}</p><strong>{item.estimate ? `${fmt(item.estimate.value_ug_m3,2)} µg/m³` : "Estimate withheld"}</strong><p>{item.estimate ? `${fmt(item.estimate.interval90_low_ug_m3,2)}–${fmt(item.estimate.interval90_high_ug_m3,2)} µg/m³ · ${item.estimate.interval_interpretation}` : item.unsupported_reason || "No supported estimate for this place and year."}</p><p>WGS84 internal point: {item.coordinates[1].toFixed(5)}, {item.coordinates[0].toFixed(5)} · {item.coordinate_meaning}</p><p>Supporting AQS monitor: {item.estimate?.reference_monitor_id || "not identified"} · {fmt(item.estimate?.nearest_monitor_km)} km</p><p>{item.evidence_explanation?.why_this_appears || `Annual ${item.year} model evidence at this point.`}</p>{!!item.nearby_inventory_records?.length && <><h3>Nearby EPA NEI inventory records · not ambient measurements</h3>{item.nearby_inventory_records.slice(0,3).map((record,index)=><p key={`${record.facility_id || record.summary_row_id}:${index}`}>{String(record.name || record.facility_id || "EPA inventory record")} · {String(record.pollutant_code || "pollutant not specified")} · {fmt(Number(record.emissions),2)} {String(record.units || "")} · inventory {String(record.inventory_year || "year unavailable")} · {fmt(Number(record.distance_km),1)} km from internal point</p>)}</>}<p>Population 2024: {item.population_2024 == null ? "not reported" : fmt(item.population_2024)} · vintage {item.population_vintage || "not recorded"}</p></article>)}</div><p>Sources and provenance are available from the versioned dataset release. EPA NEI facility rows describe inventory estimates and do not show contribution to ambient concentration.</p><h2>Questions for further investigation</h2><ul><li>Are the annual observation period and nearby AQS monitor suitable for the local question being asked?</li><li>Which local, tribal, or community monitoring records could fill gaps in this release?</li><li>Can listed inventory facilities be verified against current records, permits, or mapped facility boundaries?</li><li>What timestamped weather and independent measurements would be needed before testing a non-causal association?</li></ul></section>}
    <header className="national-header">
      <a className="national-brand" href="/"><span className="national-brand-icon"><Wind size={23}/></span><span>UPWIND<small>HISTORICAL AIR ATLAS</small></span></a>
      <div className="national-head-copy"><span className="national-kicker">PUBLIC DATA EXPLORER</span><h1>Air quality, seen across place and time.</h1></div>
      <div className="national-header-actions"><button onClick={share} className="soft-button"><Share2 size={15}/> {shareCopied ? "Link copied" : "Share view"}</button></div>
    </header>
    {error && (
      <div className="national-alert" role="alert">
        <div className="alert-content">
          <AlertCircle size={15}/>
          <div>
            <strong>National release unavailable</strong>
            <span>{error} Run the data acquisition and model build commands in docs/NATIONAL_EXPLORER.md.</span>
          </div>
        </div>
        <button type="button" className="alert-dismiss" aria-label="Dismiss notice" onClick={() => setError("")}><X size={14}/></button>
      </div>
    )}
    {mapDataError && !loading && (
      <div className="national-alert" role="alert">
        <div className="alert-content">
          <AlertCircle size={15}/>
          <div>
            <strong>Some map evidence is unavailable</strong>
            <span>{mapDataError}</span>
          </div>
        </div>
        <button type="button" className="alert-dismiss" aria-label="Dismiss notice" onClick={() => setMapDataError("")}><X size={14}/></button>
      </div>
    )}
    <section className="national-toolbar" aria-label="Explorer controls">
      <div className="national-search"><Search size={17}/><input aria-label="Search Census places" aria-expanded={!!searchResults.length} aria-controls="national-place-results" aria-activedescendant={searchResults[searchIndex]?`national-place-${searchResults[searchIndex].id}`:undefined} placeholder="Search a Census place or state" value={query} onChange={(e)=>setQuery(e.target.value)} onKeyDown={onSearchKey}/>{query&&<button aria-label="Clear search" onClick={()=>{setQuery("");setSearchResults([]);setSearchError("")}}><X size={15}/></button>}
        {!!searchResults.length&&<div id="national-place-results" className="search-results" role="listbox">{searchResults.map((p,i)=><button id={`national-place-${p.id}`} role="option" aria-selected={i===searchIndex} key={p.id} onMouseEnter={()=>setSearchIndex(i)} onClick={()=>selectPlace(p)}><span>{p.name}</span><small>{p.state} · {p.place_type}</small></button>)}</div>}
        {!!query.trim()&&searchLoading&&<div className="search-results" role="status">Searching Census places…</div>}
        {!!query.trim()&&!searchLoading&&!searchResults.length&&<div className="search-results" role="status">{searchError || `No Census places match “${query}”. Include the state name to distinguish places.`}</div>}
      </div>
      <label className="national-select"><span>Historical year</span><select value={year} onChange={(e)=>{
        const next = Number(e.target.value);
        const modelingYear = manifest?.selected_modeling_year ?? 2024;
        let nextLayer = layer;
        if (layer === "estimates" && next !== modelingYear) {
          nextLayer = "monitors";
        }
        setYear(next);
        if (nextLayer !== layer) setLayer(nextLayer);
        history.pushState(null,"",`${location.pathname}?${new URLSearchParams({year:String(next),layer:nextLayer,...(selectedId?{place:selectedId}:{}),...(comparisonIds.length?{compare:comparisonIds.join(",")}:{})}).toString()}`);
      }}>{availableYears.map((y)=><option key={y} value={y}>{y}{y===manifest?.selected_modeling_year?" · modeled estimates & monitors":y===2025?" · preliminary monitors":" · measured monitors"}</option>)}</select><ChevronDown size={14}/></label>
      <div className="national-layer-controls">
        <div className="national-layers" role="group" aria-label="Map evidence layer">
          <button
            type="button"
            aria-pressed={layer === "estimates"}
            className={layer === "estimates" ? "selected" : ""}
            title={year !== (manifest?.selected_modeling_year ?? 2024) ? `Modeled place estimates (${manifest?.selected_modeling_year ?? 2024})` : "Model estimates"}
            onClick={() => {
              const modelingYear = manifest?.selected_modeling_year ?? 2024;
              const targetYear = year !== modelingYear ? modelingYear : year;
              if (targetYear !== year) setYear(targetYear);
              setLayer("estimates");
              history.pushState(null, "", `${location.pathname}?${new URLSearchParams({ year: String(targetYear), layer: "estimates", ...(selectedId ? { place: selectedId } : {}), ...(comparisonIds.length ? { compare: comparisonIds.join(",") } : {}) }).toString()}`);
            }}
          >
            <Activity size={15} /> Estimates
          </button>
          <button
            type="button"
            aria-pressed={layer === "monitors"}
            className={layer === "monitors" ? "selected" : ""}
            onClick={() => {
              history.pushState(null, "", `${location.pathname}?${new URLSearchParams({ year: String(year), layer: "monitors", ...(selectedId ? { place: selectedId } : {}), ...(comparisonIds.length ? { compare: comparisonIds.join(",") } : {}) }).toString()}`);
              setLayer("monitors");
            }}
          >
            <MapPin size={15} /> Monitors
          </button>
        </div>
        <div className="national-overlay-control" role="group" aria-label="Evidence overlays">
          <button
            type="button"
            aria-pressed={showSources || layer === "sources"}
            className={`source-overlay-toggle${showSources || layer === "sources" ? " is-active" : ""}`}
            title="Quick toggle to overlay EPA NEI emissions source facilities on top of the map"
            onClick={() => {
              if (layer === "sources") {
                setLayer("estimates");
                setShowSources(false);
              } else {
                setShowSources((value) => !value);
              }
            }}
          >
            <span className="source-toggle-indicator" aria-hidden="true" />
            <Layers3 size={15} />
            <span>{showSources || layer === "sources" ? "Sources on" : "Show sources"}</span>
          </button>
        </div>
      </div>
    </section>
    {loading ? (
      <LoadingScreen
        message="Loading versioned EPA and Census release…"
        submessage="Streaming EPA regulatory monitors, Census boundaries, and historical PM2.5 estimates"
      />
    ) : <>
      <div className={`national-main-grid${activePlace || active || selectedCluster ? " has-selection" : ""}`}>
        <section className="national-map-panel" aria-label="National evidence map">
          <div className="national-map-heading"><div className="national-map-title-card"><span className="national-kicker">UNITED STATES · {layer==="estimates"?"ANNUAL PM2.5":layer==="monitors"?"REGULATORY MONITOR SITES":"DOCUMENTED EMISSIONS INVENTORY"}</span><h2>{activePlace?.name ? `${activePlace.name}, ${activePlace.state}` : "Explore the national pattern"}</h2></div><span className="map-data-pill">{layer === "estimates" ? `${fmt(manifest?.counts.supported_model_places)} supported places` : layer === "monitors" ? `${fmt(manifest?.annual_monitor_audit?.[String(year)]?.unique_spatial_site_years)} monitor site-years in ${year}` : `EPA inventory · 2023`}</span></div>
          <EvidenceMap year={year} layer={layer} showSources={showSources} initialCamera={readCamera(params)} selected={activePlace} selectedPoint={selectedPoint} onSelect={onMapSelect} onCluster={onCluster} onBounds={onBounds} onCamera={onCamera} places={visiblePlaces} monitors={monitors.filter((m)=>m.year===year)} sources={sources}/>
          <div className="map-hud-stack" role="region" aria-label="Map status and legend">
            {layer === "estimates" && !visiblePlaces.some((p) => p.model_estimates?.[String(year)]) && (
              year !== (manifest?.selected_modeling_year ?? 2024) ? (
                <div className="map-empty map-year-notice" role="status">
                  <div className="map-notice-header"><AlertCircle size={15}/><strong>Model estimates are published for {manifest?.selected_modeling_year ?? 2024}</strong></div>
                  <p>EPA measured monitor observations are available for {year}.</p>
                  <div className="map-notice-actions">
                    <button type="button" className="notice-btn primary" onClick={() => {
                      setLayer("monitors");
                      history.pushState(null, "", `${location.pathname}?${new URLSearchParams({year: String(year), layer: "monitors", ...(selectedId ? { place: selectedId } : {}), ...(comparisonIds.length ? { compare: comparisonIds.join(",") } : {})}).toString()}`);
                    }}><MapPin size={13}/> View {year} EPA monitors</button>
                    <button type="button" className="notice-btn secondary" onClick={() => {
                      const mYear = manifest?.selected_modeling_year ?? 2024;
                      setYear(mYear);
                      history.pushState(null, "", `${location.pathname}?${new URLSearchParams({year: String(mYear), layer: "estimates", ...(selectedId ? { place: selectedId } : {}), ...(comparisonIds.length ? { compare: comparisonIds.join(",") } : {})}).toString()}`);
                    }}>Switch to {manifest?.selected_modeling_year ?? 2024} estimates</button>
                  </div>
                </div>
              ) : (
                <p className="map-empty" role="status">No supported place estimates are loaded in this map view for {year}. Search a place or pan the map.</p>
              )
            )}
            {layer === "monitors" && !monitors.some((m) => m.year === year) && <p className="map-empty" role="status">No measured EPA AQS monitor records are loaded in this map view for {year}.</p>}
            {(layer === "sources" || showSources) && !sources.length && <p className="map-empty" role="status">No EPA NEI facility records are loaded in this map view.</p>}
            <div className={`map-legend ${layer === "monitors" ? "legend-monitors" : layer === "sources" ? "legend-sources" : "legend-estimates"}`} aria-label={`Legend: ${layer === "monitors" ? "measured monitor values" : "modeled point estimates"}${showSources || layer === "sources" ? " and facility inventory" : ""}`}>
              {layer==="sources"?<><span><i className="legend-dot facility"/>EPA inventory facility</span><span className="legend-note">Primary PM2.5 · reported source units · NEI 2023</span></>:<>{layer==="monitors"?<><span><i className="legend-dot measured"/>Measured AQS site</span><span className="legend-note">{year} annual mean · µg/m³</span></>:<><span><i className="legend-dot low"/>&lt;6 µg/m³</span><span><i className="legend-dot mid"/>6–10 µg/m³</span><span><i className="legend-dot high"/>&gt;10 µg/m³</span><span className="legend-note">Model estimate · {year} annual mean</span></>}{showSources&&<span><i className="legend-dot facility"/>EPA NEI facility · reported annual emissions</span>}</>}
            </div>
            <div className="map-caveat"><CircleHelp size={14}/><span>{layer==="estimates"?"Point estimates at Census Gazetteer locations (U.S. release) · historical, not live or citywide.":layer==="monitors"?"Measured annual summaries at EPA monitoring sites (U.S. release) · historical, not live.":"Annual EPA inventory records (U.S. release) · proximity does not establish contribution."}{(showSources || layer==="sources")&&" Inventory locations are separate records, not proven contributors."}</span><button type="button" className="map-method-link" onClick={()=>setTab("methodology")}>Read limits</button></div>
          </div>
        </section>
        {!sidebarOpen && (
          <button
            type="button"
            className="floating-sidebar-toggle"
            aria-label="Show sidebar details"
            title="Show sidebar details (Press [)"
            onClick={() => setSidebarOpen(true)}
          >
            <PanelRightOpen size={16} />
            <span>{activePlace ? activePlace.name : "Places & Details"}</span>
          </button>
        )}
        <aside className={`national-detail-panel${sidebarOpen ? "" : " is-hidden"}`} aria-label="Place details and evidence sidebar">
          {tab === "methodology" ? <Methodology manifest={manifest} onBack={()=>setTab("place")} onToggleSidebar={()=>setSidebarOpen(false)}/> : activePlace ? <>
            <div className="detail-title-row"><div><span className="national-kicker">CENSUS {(activePlace.place_type || "PLACE").toUpperCase()}</span><h2>{activePlace.name || "Selected Census place"}</h2><p>{activePlace.state || "State unavailable"} · GEOID {activePlace.id}</p></div><div className="detail-header-actions"><button type="button" className="sidebar-toggle-btn" aria-label="Hide sidebar" title="Hide sidebar (Press [)" onClick={() => setSidebarOpen(false)}><PanelRightClose size={14}/><span>Hide</span></button><button className="icon-action" aria-label="Close selected place" onClick={closeDetail}><X size={17}/></button></div></div>
            <div className="detail-metric"><div><span>{activePlace.model_estimates?.[String(year)] ? `MODEL ESTIMATE · ${year}` : nearbyYearMonitor ? `NEARBY AQS MONITOR · ${year}` : `MODEL ESTIMATE · ${year}`}</span><strong>{activePlace.model_estimates?.[String(year)] ? fmt(activePlace.model_estimates[String(year)].value_ug_m3,2) : nearbyYearMonitor ? fmt(nearbyYearMonitor.pm25_ug_m3,2) : fmt(undefined,2)} <small>µg/m³</small></strong></div><div className="metric-chip">{activePlace.model_estimates?.[String(year)]?.evidence_status === "low_evidence_estimate" ? "Low evidence" : activePlace.model_estimates?.[String(year)] ? "Estimated" : nearbyYearMonitor ? `AQS measured (${year})` : "Insufficient evidence"}</div></div>
            {activePlace.model_estimates?.[String(year)] ? <><div className="uncertainty-block"><span>{activePlace.model_estimates[String(year)].evidence_status === "low_evidence_estimate" ? "Low-evidence estimate · spatial OOF 90% error band" : "Estimated point · spatial OOF 90% error band"}</span><strong>{fmt(activePlace.model_estimates[String(year)].interval90_low_ug_m3,2)} – {fmt(activePlace.model_estimates[String(year)].interval90_high_ug_m3,2)} µg/m³</strong><small>Band from geographic out-of-fold monitor-site errors. It is broad, describes this model evaluation, and does not guarantee local coverage or an area-average bound.</small></div><div className="fact-grid"><div><span>Nearest training monitor</span><b>{fmt(activePlace.model_estimates[String(year)].nearest_monitor_km)} km · AQS {activePlace.model_estimates[String(year)].reference_monitor_id || "ID unavailable"}</b></div><div><span>Population · 2024</span><b>{activePlace.estimates?.["2024"]?fmt(activePlace.estimates["2024"]):"Not reported"}</b></div></div></> : <div className="no-estimate"><strong>Estimate withheld for {year}</strong><p>{activePlace.withheld_reason || `No supported model estimate is published for this place in ${year}. The release supports ${manifest?.selected_modeling_year} only and withholds locations outside its geographic or monitor-distance support.`}</p>{nearbyYearMonitor && <div className="nearby-monitor-callout"><span>Nearest measured EPA monitor in {year}</span><b>{fmt(nearbyYearMonitor.pm25_ug_m3, 2)} <small>µg/m³</small></b><small>AQS Site {nearbyYearMonitor.id} · {fmt(activePlace.nearby_monitor?.distance_km, 1)} km from Census internal point</small></div>}<button onClick={()=>{history.pushState(null,"",`${location.pathname}?${new URLSearchParams({year:String(year),layer:"monitors",...(selectedId?{place:selectedId}:{}),...(comparisonIds.length?{compare:comparisonIds.join(",")}:{})}).toString()}`);setLayer("monitors")}}>View {year} measured monitors</button></div>}
            <div className="detail-actions"><button className="soft-button" onClick={()=>toggleCompare(activePlace.id)}><Bookmark size={15}/>{comparisonIds.includes(activePlace.id)?"Remove comparison":"Compare place"}</button><button className="soft-button" onClick={share}><Share2 size={15}/>{shareCopied?"Link copied":"Share"}</button><button className="soft-button" onClick={()=>exportSnapshot("csv")}><Download size={15}/> Export place</button></div>
            <section className="detail-section"><div className="section-title-line"><h3>Nearby measured history</h3><span>EPA AQS annual summaries</span></div>{chartData.length>1?<div className="history-chart"><ResponsiveContainer width="100%" height={160}><LineChart data={chartData} margin={{left:-25,right:8,top:8,bottom:2}}><CartesianGrid stroke="#e6e8e3" vertical={false}/><XAxis dataKey="year" tick={{fontSize:10,fill:"#637079"}} axisLine={false} tickLine={false}/><YAxis tick={{fontSize:10,fill:"#637079"}} axisLine={false} tickLine={false}/><Tooltip formatter={(v)=>[`${fmt(Number(v),2)} µg/m³`,"Measured annual PM2.5"]}/><Line type="monotone" dataKey="measured" stroke="#247b70" strokeWidth={2.5} dot={{r:3,fill:"#247b70"}}/></LineChart></ResponsiveContainer></div>:<p className="muted-note">No consistent nearby monitor history under the 5 km Gazetteer-point rule. Monitor-site history remains separately searchable.</p>}</section><EvidenceExplanation place={activePlace} year={year}/><SourceContext data={contextData} loading={contextLoading} error={contextError} radius={contextRadius} onRadiusChange={(next)=>{setContextRadius(next);const nextParams=new URLSearchParams(location.search);nextParams.set("radius",String(next));history.pushState(null,"",`${location.pathname}?${nextParams.toString()}`)}}/>
          </> : selectedCluster ? <><div className="detail-title-row"><div><span className="national-kicker">{selectedCluster.kind === "estimates" ? "PLACE ESTIMATES" : selectedCluster.kind === "monitors" ? "EPA MONITORS" : "EPA INVENTORY SOURCES"}</span><h2>{fmt(selectedCluster.count)} records nearby</h2><p>Choose a record to inspect its details.</p></div><div className="detail-header-actions"><button type="button" className="sidebar-toggle-btn" aria-label="Hide sidebar" title="Hide sidebar (Press [)" onClick={() => setSidebarOpen(false)}><PanelRightClose size={14}/><span>Hide</span></button><button className="icon-action" aria-label="Close record details" onClick={closeDetail}><X size={17}/></button></div></div><div className="detail-section"><h3>Records</h3>{selectedCluster.loading&&!selectedCluster.members.length&&<p role="status">Loading records…</p>}{selectedCluster.members.map((member,index)=><div className="source-row" key={`${member.id}:${index}`} style={{cursor:"pointer"}} onClick={()=>{const coords: [number, number] | undefined = (member.render_longitude != null && member.render_latitude != null) ? [member.render_longitude, member.render_latitude] : (member.longitude != null && member.latitude != null) ? [member.longitude, member.latitude] : undefined; onMapSelect(selectedCluster.kind, String(member.id), coords, member);}}><span><b>{member.name || member.id}</b><small>{member.state || member.category || (member.year ? `EPA AQS · ${member.year}` : selectedCluster.kind === "estimates" ? "Census place estimate" : "EPA inventory record")}</small></span><span>{selectedCluster.kind === "estimates" ? `${fmt(member.model_estimates?.[String(year)]?.value_ug_m3,2)} µg/m³` : selectedCluster.kind === "monitors" ? `${fmt(member.pm25_ug_m3,2)} µg/m³` : `${fmt(member.emissions,2)} ${member.units || ""}`}</span></div>)}{selectedCluster.nextOffset != null&&<button className="soft-button" onClick={loadMoreClusterMembers} disabled={selectedCluster.loading}>{selectedCluster.loading?"Loading…":"Load more records"}</button>}</div></> : selectedMonitor ? <><div className="detail-title-row"><div><span className="national-kicker">MEASURED · EPA AQS</span><h2>Monitor {selectedMonitor.id}</h2><p>{selectedMonitor.year} annual PM2.5 summary</p></div><div className="detail-header-actions"><button type="button" className="sidebar-toggle-btn" aria-label="Hide sidebar" title="Hide sidebar (Press [)" onClick={() => setSidebarOpen(false)}><PanelRightClose size={14}/><span>Hide</span></button><button className="icon-action" aria-label="Close monitor details" onClick={closeDetail}><X size={17}/></button></div></div><div className="detail-metric"><div><span>MEASURED ANNUAL MEAN</span><strong>{fmt(selectedMonitor.pm25_ug_m3,2)} <small>µg/m³</small></strong></div></div><div className="detail-facts"><p>Completeness indicator: <b>{selectedMonitor.sample_completeness}</b></p><p>Event treatment: <b>{selectedMonitor.event_treatment}</b></p><p>Pollutant standard: <b>{selectedMonitor.pollutant_standard}</b></p><p>Metric: <b>{selectedMonitor.metric}</b></p><p>Coordinates: {selectedMonitor.latitude.toFixed(4)}, {selectedMonitor.longitude.toFixed(4)}</p></div></> : selectedFacility ? <><div className="detail-title-row"><div><span className="national-kicker">INVENTORY ESTIMATE · EPA NEI {selectedFacility.inventory_year}</span><h2>{selectedFacility.name}</h2><p>EIS facility ID {selectedFacility.facility_id || selectedFacility.id} · {selectedFacility.pollutant_code} · {selectedFacility.category}</p></div><div className="detail-header-actions"><button type="button" className="sidebar-toggle-btn" aria-label="Hide sidebar" title="Hide sidebar (Press [)" onClick={() => setSidebarOpen(false)}><PanelRightClose size={14}/><span>Hide</span></button><button className="icon-action" aria-label="Close source details" onClick={closeDetail}><X size={17}/></button></div></div><div className="detail-metric"><div><span>{selectedFacility.pollutant_code} · REPORTED EMISSIONS</span><strong>{fmt(selectedFacility.emissions,2)} <small>{selectedFacility.units}</small></strong></div></div><div className="detail-facts"><p>Location: <b>Approximate inventory facility coordinate</b></p><p>Coordinate role: {selectedFacility.coordinate_role || "Reported facility coordinate; not a release point."}</p><p>WGS84: {(selectedFacility.original_coordinates || [selectedFacility.longitude, selectedFacility.latitude]).map((value: number) => value.toFixed(5)).join(", ")}</p><p>Identity: <b>{selectedFacility.match_method || "Exact EPA EIS facility identifier"}</b> · canonical {selectedFacility.canonical_facility_id || `epa-eis:${selectedFacility.id}`}</p><p>Verified address or footprint: <b>{selectedFacility.address || "not available in this release"}</b></p></div><p className="source-disclaimer">This is a facility-level annual inventory estimate for {selectedFacility.inventory_year}, not ambient concentration. It does not show the facility's contribution to a nearby monitor. The map retains the original NEI coordinate; it is not snapped to a building or treated as a release point.</p><a className="external-link" href={selectedFacility.url} target="_blank" rel="noreferrer">Open EPA inventory source data <ExternalLink size={14}/></a></> : active ? <div className="detail-loading-state" role="status"><div className="detail-title-row"><div><span className="national-kicker">LOADING EVIDENCE</span><h2>Loading {active.kind === "estimates" ? "place estimate" : active.kind === "monitors" ? "monitor site" : "inventory source"}…</h2><p>Retrieving documented record {active.id}.</p></div><div className="detail-header-actions"><button type="button" className="sidebar-toggle-btn" aria-label="Hide sidebar" title="Hide sidebar (Press [)" onClick={() => setSidebarOpen(false)}><PanelRightClose size={14}/><span>Hide</span></button><button className="icon-action" aria-label="Close" onClick={closeDetail}><X size={17}/></button></div></div></div> : <>
            <div className="detail-title-row"><div><span className="national-kicker">A PLACE-BASED VIEW</span><h2>Start with a place.</h2><p>Search a Census place or select evidence from the map.</p></div><div className="detail-header-actions"><button type="button" className="sidebar-toggle-btn" aria-label="Hide sidebar" title="Hide sidebar (Press [)" onClick={() => setSidebarOpen(false)}><PanelRightClose size={14}/><span>Hide</span></button></div></div><div className="quick-places"><span>Try Charlotte, Durham, Raleigh, or Denver</span>{[{name:"Charlotte",state:"North Carolina"},{name:"Durham",state:"North Carolina"},{name:"Raleigh",state:"North Carolina"},{name:"Denver",state:"Colorado"}].map(({name,state})=><button key={name} onClick={()=>{setQuery(`${name}, ${state}`);fetch(`${API}/places?q=${encodeURIComponent(name)}&state=${encodeURIComponent(state)}&limit=10&year=${year}`).then((r)=>{if(!r.ok)throw new Error();return r.json()}).then((d)=>d.items?.[0]&&selectPlace(d.items[0])).catch(()=>setSearchError("Place search is temporarily unavailable."));}}>{name}<ArrowRight size={13}/></button>)}</div><div className="rank-list"><div className="section-title-line"><h3>Higher estimates in loaded map view</h3><span>{year} · supported only</span></div>{ranking.slice(0,6).map((p,i)=><button key={p.id} onClick={()=>selectPlace(p)} className="rank-row"><span className="rank-number">{String(i+1).padStart(2,"0")}</span><span><b>{p.name}</b><small>{p.state}</small></span><strong>{fmt(p.model_estimates?.[String(year)]?.value_ug_m3,2)}<small>µg/m³</small></strong></button>)}</div><div className="detail-footnote">Sorted point estimates are not precise ranks or a “most dangerous” list. Differences can be too small to distinguish within the broad error band.</div>
          </>}
        </aside>
      </div>
      {(comparisons.length>0 || !!activePlace)&&<section className="comparison-panel"><div className="comparison-heading"><div><span className="national-kicker">SIDE BY SIDE · SAME YEAR</span><h2>Place comparison <small>{year}</small></h2></div><div className="export-actions"><button onClick={()=>exportSnapshot("csv")}><Download size={15}/> CSV</button><button onClick={()=>exportSnapshot("geojson")}>GeoJSON</button><button aria-label="Print brief" onClick={printBrief}><FileText size={15}/> Create community report</button><button aria-label="Clear comparisons" onClick={()=>{setComparisonIds([]);localStorage.removeItem("upwind-national-compare");history.pushState(null,"",`${location.pathname}?${new URLSearchParams({year:String(year),layer,...(selectedId?{place:selectedId}:{})}).toString()}`)}}><X size={16}/></button></div></div>{printError&&<p className="national-alert" role="alert">{printError}</p>}{exportError&&<p className="national-alert" role="alert">{exportError}</p>}<p className="source-disclaimer">Estimates that share a reference monitor are not independent. Overlapping broad error bands mean their ordering is uncertain; differences are descriptive and may not be distinguishable within the empirical spatial error band.</p><div className="comparison-cards">{comparisonPlaces.map((p)=><article key={p.id}><button className="comparison-remove" onClick={()=>toggleCompare(p.id)} aria-label={`Remove ${p.name}`}><X size={13}/></button><span>{p.state} · {p.place_type}</span><h3>{p.name}</h3><strong>{fmt(p.model_estimates?.[String(year)]?.value_ug_m3,2)} <small>µg/m³</small></strong><p>{p.model_estimates?.[String(year)]?`90% band ${fmt(p.model_estimates[String(year)].interval90_low_ug_m3,2)}–${fmt(p.model_estimates[String(year)].interval90_high_ug_m3,2)}`:"Estimate withheld for selected period"}</p>{comparisonPlaces.some((other)=>other.id!==p.id&&other.model_estimates?.[String(year)]?.reference_monitor_id===p.model_estimates?.[String(year)]?.reference_monitor_id)&&<small>Shares the same reference monitor as another selected place; comparison is correlated.</small>}</article>)}</div></section>}
      <section className="national-bottom"><div className="coverage-card"><span className="national-kicker">RELEASE COVERAGE COUNTS</span><div className="coverage-numbers"><div><strong>{fmt(manifest?.counts.searchable_census_places)}</strong><span>searchable Census places</span></div><div><strong>{fmt(manifest?.counts.supported_model_places)}</strong><span>with supported estimates</span></div><div><strong>{fmt(manifest?.counts.places_with_nearby_monitor_proxy ?? manifest?.counts.monitor_sites_selected_year)}</strong><span>{manifest?.counts.places_with_nearby_monitor_proxy != null ? "monitor within 5 km of place point*" : `EPA monitor sites in ${manifest?.selected_modeling_year ?? 2024}`}</span></div><div><strong>{manifest?.counts.population_covered?fmt(manifest.counts.population_covered):"Not calculated"}</strong><span>residents in modeled places with published 2024 estimate</span></div></div><p>{manifest?.counts.places_with_nearby_monitor_proxy != null ? "*This is a proximity proxy, not a legal-boundary overlap count. " : ""}Population sum uses unique Census place GEOIDs with available estimates; it describes release coverage, not users or exposure impact.</p></div><button className="methodology-card" onClick={()=>setTab("methodology")}><span className="national-kicker">HOW TO READ THIS ATLAS</span><h3>Evidence, model evaluation & coverage</h3><p>Review the target definition, spatial holdout, uncertainty, source data, and unsupported places.</p><span>Open methodology <ArrowRight size={14}/></span></button></section>
      <footer className="national-footer"><span>UPWIND · DATED HISTORICAL ATLAS · NO LIVE CONDITIONS</span><span>Historical concentration estimates do not identify sources or responsibility.</span></footer>
    </>}
  </main>;
}

function Methodology({manifest,onBack,onToggleSidebar}:{manifest:NationalManifest|null;onBack:()=>void;onToggleSidebar?:()=>void}) {
  const v2=manifest?.model_evaluation_v2; const cv=manifest?.counts;
  const r24=v2?.years["2024"]; const r25=v2?.years["2025"];
  return <><div className="detail-title-row"><div><span className="national-kicker">METHODOLOGY · {v2?.protocol||"RELEASE"}</span><h2>What this map can say</h2><p>Historical annual PM2.5 at a specified point, separate from source attribution.</p></div><div className="detail-header-actions">{onToggleSidebar&&<button type="button" className="sidebar-toggle-btn" aria-label="Hide sidebar" title="Hide sidebar (Press [)" onClick={onToggleSidebar}><PanelRightClose size={14}/><span>Hide</span></button>}<button className="icon-action" onClick={onBack} aria-label="Back to explorer"><X size={17}/></button></div></div><div className="methodology-copy"><h3>Target and deployed model</h3><p>Target: EPA AQS annual PM2.5 summary (parameter 88101; annual standard; quarterly means of daily means; completeness flag Y), in µg/m³. The deployed model is {manifest?.model?.method}. It predicts at the Census Gazetteer internal point. Gazetteer points are not place polygons; results are not citywide or neighborhood averages.</p><p>The deployed model transfers the nearest eligible monitor value. The fixed 150 km Gaussian kernel and a Gaussian-plus-PRISM-temperature candidate were evaluated with spatial folds. Neither candidate met the predeclared requirement of at least four of five fold wins in both years; the deployed model therefore remains nearest-monitor. Fold outcomes are development evidence; all 2024 results had already been inspected. No untouched final set remains for this release, so no fresh final-accuracy claim is made.</p><h3>Geographic development comparison</h3><p>Spatial out-of-fold scores use the training-fold mean as the R² reference. On all corrected eligible monitor sites: 2024 (n={fmt(r24?.nearest_monitor?.n)}) nearest-monitor MAE {fmt(r24?.nearest_monitor?.mae_ug_m3,2)}, RMSE {fmt(r24?.nearest_monitor?.rmse_ug_m3,2)}, bias {fmt(r24?.nearest_monitor?.bias_ug_m3,2)}; Gaussian MAE {fmt(r24?.gaussian_kernel_ridge_150km?.mae_ug_m3,2)}, RMSE {fmt(r24?.gaussian_kernel_ridge_150km?.rmse_ug_m3,2)}. Provisional 2025 (n={fmt(r25?.nearest_monitor?.n)}) nearest-monitor MAE {fmt(r25?.nearest_monitor?.mae_ug_m3,2)}, RMSE {fmt(r25?.nearest_monitor?.rmse_ug_m3,2)}; Gaussian MAE {fmt(r25?.gaussian_kernel_ridge_150km?.mae_ug_m3,2)}, RMSE {fmt(r25?.gaussian_kernel_ridge_150km?.rmse_ug_m3,2)}. On the matched PRISM comparison rows (2024 n=872; provisional 2025 n=882), Gaussian plus PRISM temperature scored MAE/RMSE/bias 1.320/1.859/−0.081 and 1.384/1.872/−0.202 µg/m³ respectively. It won 5/5 2024 folds but only 3/5 provisional 2025 folds. The existing rule requires at least four wins in both years, so this candidate is not deployed. PRISM annual grids are retrospective, not available for a beginning-of-year forecast. Negative R² means squared error exceeded the training-fold mean reference. The 2025 archive is provisional and supplementary.</p><p>The symmetric 90th-percentile absolute error band is ±{fmt(v2?.deployment.calibration_abs_residual_90pct_ug_m3,2)} µg/m³, estimated from spatial out-of-fold monitor-site residuals. It is not a local guarantee. Publication withholds locations outside the contiguous-U.S. domain or beyond {fmt(v2?.deployment.oof_nearest_monitor_distance_p90_support_km)} km from an eligible monitor; farther places remain searchable without a prediction. The low-evidence label marks places beyond the 75th percentile of observed out-of-fold monitor distance; it is a distance evidence tier, not a validated local uncertainty class.</p><h3>Coverage</h3><p>{fmt(cv?.searchable_census_places)} Census places are searchable; {fmt(cv?.supported_model_places)} have a 2024 estimate; {fmt(v2?.deployment.withheld_places)} are withheld. Population coverage sums available 2024 Census estimates for unique modeled place GEOIDs ({fmt(cv?.population_covered)} residents); it is geographic coverage, not users reached or impact. EPA monitor proximity uses 5 km from the Gazetteer internal point, not legal-boundary containment.</p><h3>Data and limitations</h3><ul>{Object.entries(manifest?.dataset_sources||{}).map(([name,src])=><li key={name}><a href={src.url} target="_blank" rel="noreferrer">{name} <ExternalLink size={12}/></a>{src.vintage?` · vintage ${src.vintage}`:""}{src.period?` · ${src.period}`:""}</li>)}</ul><p>EPA AQS annual observations retain parameter, metric, units, sample completeness, event treatment, certification, and selected colocated POC provenance. The release selects one ambient summary per POC: Events Included when present, otherwise No Events; event-excluded alternatives are not substituted. EPA NEI rows are facility-level primary-PM2.5 annual inventory estimates in source units. Inventory proximity does not identify contribution or responsibility.</p><ul><li>2024 evaluation data and previous evaluation results were inspected; these folds are development evidence, not a fresh final test.</li><li>2025 monitor summaries are provisional; no year forecasting is claimed.</li><li>Population and facility proximity are not used as pollution proxies.</li><li>No independent between-monitor field validation, personal exposure, current conditions, forecast, source attribution, or health interpretation is established.</li></ul><div className="method-commands"><code>python scripts/build_national_dataset.py --start-year 2018 --end-year 2025</code><code>OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python scripts/evaluate_national_v2.py</code><code>python scripts/evaluate_national_v3.py</code></div></div></>;
}

