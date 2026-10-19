import { useEffect, useRef, useState } from "react";
import type { Map as GeographicMap } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { Layers, Compass, MapPin, Plus, Minus, Maximize2 } from "lucide-react";
import type { Investigation, Point, Site } from "./types";

interface Props {
  inv: Investigation;
  time: string;
  selected: string;
  mode: string;
  onPick: (s: Site) => void;
  onAdd: (p: Point) => void;
  onMode: (m: string) => void;
  planIndex: number;
}
export default function StudyMap({
  inv,
  time,
  selected,
  mode,
  onPick,
  onAdd,
  onMode,
  planIndex,
}: Props) {
  const [layers, setLayers] = useState({
    sensors: true,
    candidates: true,
    sources: true,
    plan: true,
    wind: true,
    observations: true,
  });
  const [showLayers, setShowLayers] = useState(false),
    [zoom, setZoom] = useState(1),
    [geo, setGeo] = useState(false),
    [tileError, setTileError] = useState(false);
  const container = useRef<HTMLDivElement>(null);
  const svgRef = useRef<SVGSVGElement>(null);
  useEffect(() => {
    if (mode) svgRef.current?.focus();
  }, [mode]);
  const [west, south, east, north] = inv.area;
  const [cx, cy] = [(west + east) / 2, (north + south) / 2];
  const [w, s, e, n] = [
    cx + (west - cx) / zoom,
    cy + (south - cy) / zoom,
    cx + (east - cx) / zoom,
    cy + (north - cy) / zoom,
  ];
  const xy = (p: Point) => [
    50 + ((p.longitude - w) / (e - w)) * 900,
    35 + ((n - p.latitude) / (n - s)) * 530,
  ];
  const chosen = inv.result?.plans[planIndex]?.site_ids || [];
  const weather = time
    ? inv.weather.find((x) => x.timestamp === time)
    : inv.weather[0];
  useEffect(() => {
    if (!geo || !container.current) return;
    let map: GeographicMap | undefined,
      cancelled = false;
    import("maplibre-gl")
      .then((maplibregl) => {
        if (cancelled || !container.current) return;
        try {
          map = new maplibregl.Map({
            container: container.current,
            style: {
              version: 8,
              sources: {
                osm: {
                  type: "raster",
                  tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
                  tileSize: 256,
                  attribution: "© OpenStreetMap contributors",
                },
              },
              layers: [{ id: "tiles", type: "raster", source: "osm" }],
            },
            center: [cx, cy],
            zoom: 14,
            attributionControl: { compact: true },
          });
          map.on("error", () => setTileError(true));
          map.addControl(new maplibregl.NavigationControl(), "top-right");
          inv.sites.forEach((site) =>
            new maplibregl.Marker({
              color: site.kind === "sensor" ? "#8ee6d5" : "#b8efb0",
            })
              .setLngLat([site.longitude, site.latitude])
              .setPopup(new maplibregl.Popup().setText(site.name))
              .addTo(map!),
          );
          map.fitBounds(
            [
              [west, south],
              [east, north],
            ],
            { padding: 45, duration: 0 },
          );
        } catch {
          setTileError(true);
          setGeo(false);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setTileError(true);
          setGeo(false);
        }
      });
    return () => {
      cancelled = true;
      map?.remove();
    };
  }, [geo, inv.sites, west, south, east, north, cx, cy]);
  return (
    <section className="map-card" aria-label="Investigation map">
      <div className="map-top">
        <div>
          <span className="eyebrow">STUDY AREA</span>
          <strong>
            {inv.synthetic
              ? "Synthetic estuary"
              : "Selected investigation area"}
          </strong>
        </div>
        <div className="map-top-actions">
          <button
            className={"mini " + (geo ? "active" : "")}
            onClick={() => {
              setGeo(!geo);
              setTileError(false);
            }}
          >
            {geo ? "Local grid" : "Geographic context"}
          </button>
          <button
            className="icon-button"
            aria-label="Map layers"
            onClick={() => setShowLayers(!showLayers)}
          >
            <Layers size={17} />
          </button>
        </div>
      </div>
      {showLayers && (
        <fieldset className="layer-pop">
          <legend>Visible layers</legend>
          {Object.entries(layers).map(([k, v]) => (
            <label key={k}>
              <input
                type="checkbox"
                checked={v}
                onChange={() => setLayers({ ...layers, [k]: !v })}
              />
              {k}
            </label>
          ))}
        </fieldset>
      )}
      <div
        className="map-canvas"
        style={{ cursor: mode ? "crosshair" : undefined }}
      >
        {geo ? (
          <>
            <div ref={container} className="geographic" />
            {tileError && (
              <div className="map-notice">
                Geographic tiles unavailable.{" "}
                <button onClick={() => setGeo(false)}>
                  Use offline local grid
                </button>
              </div>
            )}
          </>
        ) : (
          <svg
            ref={svgRef}
            tabIndex={mode ? 0 : undefined}
            role="img"
            aria-label="Local coordinate map with observed monitors, permitted candidate sites, and experimental source-domain anchors"
            viewBox="0 0 1000 600"
            onKeyDown={(ev) => {
              if (
                ev.key === "Enter" &&
                mode &&
                ev.target === ev.currentTarget
              ) {
                ev.preventDefault();
                onAdd({ latitude: cy, longitude: cx });
              }
            }}
            onClick={(ev) => {
              if (!mode) return;
              const rect = ev.currentTarget.getBoundingClientRect();
              const scale = Math.min(rect.width / 1000, rect.height / 600),
                ox = (rect.width - 1000 * scale) / 2,
                oy = (rect.height - 600 * scale) / 2;
              const px = (ev.clientX - rect.left - ox) / scale,
                py = (ev.clientY - rect.top - oy) / scale;
              if (px < 50 || px > 950 || py < 35 || py > 565) return;
              onAdd({
                longitude: w + ((px - 50) / 900) * (e - w),
                latitude: n - ((py - 35) / 530) * (n - s),
              });
            }}
          >
            <defs>
              <pattern
                id="grid"
                width="90"
                height="88.33"
                x="50"
                y="35"
                patternUnits="userSpaceOnUse"
              >
                <path
                  d="M 90 0 L 0 0 0 88.33"
                  fill="none"
                  stroke="#23323c"
                  strokeWidth="1"
                />
              </pattern>
              <radialGradient id="ambient">
                <stop stopColor="#224038" stopOpacity=".2" />
                <stop offset="1" stopColor="#10202a" stopOpacity="0" />
              </radialGradient>
            </defs>
            <rect width="1000" height="600" fill="#101c24" />
            <rect x="50" y="35" width="900" height="530" fill="url(#grid)" />
            <ellipse cx="430" cy="270" rx="430" ry="300" fill="url(#ambient)" />
            <rect
              x="75"
              y="60"
              width="850"
              height="480"
              rx="6"
              fill="none"
              stroke="#6a8e82"
              strokeDasharray="6 7"
              opacity=".35"
            />
            {[0, 1, 2, 3, 4].map((i) => (
              <text key={i} x="15" y={45 + i * 128} className="coordinate">
                {(n - ((n - s) * i) / 4).toFixed(3)}°
              </text>
            ))}
            {[0, 1, 2, 3, 4].map((i) => (
              <text key={i} x={55 + i * 218} y="590" className="coordinate">
                {(w + ((e - w) * i) / 4).toFixed(3)}°
              </text>
            ))}
            {layers.sources &&
              inv.result?.source_region90?.cells.map((cell, i) => (
                <polygon
                  key={`region-${i}`}
                  points={cell.polygon
                    .map((point) => xy(point).join(","))
                    .join(" ")}
                  fill="#d8aa5e"
                  fillOpacity=".14"
                  stroke="#d8aa5e"
                  strokeOpacity=".25"
                  strokeWidth=".5"
                  pointerEvents="none"
                >
                  <title>
                    Conditional single-source model region; geographic coverage
                    is not field calibrated.
                  </title>
                </polygon>
              ))}
            {layers.sources &&
              inv.source_locations.map((p, i) => {
                const [x, y] = xy(p);
                return (
                  <g key={i}>
                    <circle
                      cx={x}
                      cy={y}
                      r="22"
                      fill="#d8aa5e"
                      fillOpacity=".045"
                      stroke="#d8aa5e"
                      strokeOpacity=".35"
                      strokeDasharray="4 5"
                    />
                    <path
                      d={`M ${x} ${y - 7} l 7 7 -7 7 -7 -7 Z`}
                      fill="#d8aa5e"
                    />
                    <text x={x + 14} y={y + 4} className="source-label">
                      S{i + 1}
                    </text>
                    <title>
                      Domain anchor S{i + 1}; this marker is not a source
                      finding or a probability at an exact point.
                    </title>
                  </g>
                );
              })}
            {layers.plan && chosen.length > 1 && (
              <polyline
                points={chosen
                  .map((id) => inv.sites.find((s) => s.id === id))
                  .filter(Boolean)
                  .map((p) => xy(p!).join(","))
                  .join(" ")}
                fill="none"
                stroke="#b8efb0"
                strokeWidth="2"
                strokeDasharray="7 6"
                opacity=".7"
              />
            )}
            {inv.sites
              .filter(
                (p) => layers[p.kind === "sensor" ? "sensors" : "candidates"],
              )
              .map((p) => {
                const selectedPlan = layers.plan && chosen.includes(p.id);
                const reading = inv.measurements
                  .filter(
                    (m) =>
                      m.sensor_id === p.id && (!time || m.timestamp === time),
                  )
                  .at(-1);
                const [x, y] = xy(p.kind === "sensor" && reading ? reading : p);
                const eligible =
                  p.allowed &&
                  p.power &&
                  p.access &&
                  p.windows.includes(inv.settings.window) &&
                  p.cost <= inv.settings.budget;
                return (
                  <g
                    key={p.id}
                    role="button"
                    tabIndex={0}
                    aria-label={`Select ${p.name}`}
                    onClick={(ev) => {
                      ev.stopPropagation();
                      onPick(p);
                    }}
                    onKeyDown={(ev) => {
                      if (ev.key === "Enter" || ev.key === " ") {
                        ev.preventDefault();
                        onPick(p);
                      }
                    }}
                    className="map-site"
                  >
                    <title>{p.name}</title>
                    <rect
                      x={x - 12}
                      y={y - 22}
                      width="44"
                      height="45"
                      fill="transparent"
                    />
                    {(selectedPlan || selected === p.id) && (
                      <circle
                        cx={x}
                        cy={y}
                        r="21"
                        fill="#b8efb0"
                        fillOpacity=".12"
                        stroke="#b8efb0"
                        strokeWidth="1.5"
                      />
                    )}
                    <circle
                      cx={x}
                      cy={y}
                      r={p.kind === "sensor" ? 9 : 6}
                      fill={
                        p.kind === "sensor"
                          ? "#8ce0d1"
                          : selectedPlan
                            ? "#b8efb0"
                            : "#17262d"
                      }
                      stroke={
                        p.kind === "sensor"
                          ? "#b6f1e6"
                          : p.allowed
                            ? "#b8efb0"
                            : "#65747e"
                      }
                      strokeWidth="2"
                    />
                    <text
                      x={p.kind === "sensor" ? x - 10 : x + 15}
                      y={p.kind === "sensor" ? y + 26 : y - 10}
                      className="site-label"
                    >
                      {p.id}
                    </text>
                    <text
                      x={p.kind === "sensor" ? x + 18 : x + 15}
                      y={p.kind === "sensor" ? y + 26 : y + 8}
                      className="site-sub"
                    >
                      {p.kind === "sensor"
                        ? reading
                          ? `${reading.pm25_ug_m3.toFixed(1)} µg/m³`
                          : "no selected reading"
                        : `${p.id} · ${eligible ? "feasible" : p.allowed ? "check constraints" : "no permission"}`}
                    </text>
                  </g>
                );
              })}
            {layers.observations &&
              inv.observations.map((p, i) => {
                const [x, y] = xy(p);
                return (
                  <g key={i}>
                    <text x={x} y={y} fontSize="20" fill="#d3b4e9">
                      ◇
                    </text>
                    <title>{p.note}</title>
                  </g>
                );
              })}
            {layers.wind && weather && (
              <g transform="translate(815 82)">
                <circle r="38" fill="#162832" stroke="#2d414b" />
                <g transform={`rotate(${weather.wind_from_deg + 180})`}>
                  <path
                    d="M 0 22 L 0 -22 M -7 -12 L 0 -22 7 -12"
                    fill="none"
                    stroke="#9cd4dc"
                    strokeWidth="2"
                  />
                </g>
                <text y="58" textAnchor="middle" className="site-sub">
                  {weather.wind_speed_m_s.toFixed(1)} m/s · from{" "}
                  {weather.wind_from_deg.toFixed(0)}°
                </text>
                <text y="73" textAnchor="middle" className="site-sub">
                  {new Date(weather.timestamp).toISOString().slice(11, 16)} UTC
                  · recorded
                </text>
              </g>
            )}
            {!inv.sites.length && (
              <text x="500" y="270" textAnchor="middle" className="site-label">
                Add sites with the toolbar or import measurements to begin.
              </text>
            )}
          </svg>
        )}
        <div className="map-tools">
          <button
            aria-label="Zoom in"
            onClick={() => {
              setGeo(false);
              setZoom(Math.min(zoom * 1.35, 5));
            }}
          >
            <Plus size={17} />
          </button>
          <button
            aria-label="Zoom out"
            onClick={() => {
              setGeo(false);
              setZoom(Math.max(zoom / 1.35, 0.5));
            }}
          >
            <Minus size={17} />
          </button>
          <button
            aria-label="Fit study area"
            onClick={() => {
              setGeo(false);
              setZoom(1);
            }}
          >
            <Maximize2 size={16} />
          </button>
        </div>
        <div className="north">
          <Compass size={20} />
          <span>N</span>
        </div>
        <div className="map-add">
          <MapPin size={15} />
          <select
            aria-label="Add to map"
            value={mode}
            onChange={(e) => {
              setGeo(false);
              onMode(e.target.value);
            }}
          >
            <option value="">Add to map…</option>
            <option value="candidate" disabled={inv.sites.length >= 100}>
              Candidate site
            </option>
            <option value="sensor" disabled={inv.sites.length >= 100}>
              Existing monitor
            </option>
            <option value="source" disabled={inv.source_locations.length >= 25}>
              Source-domain anchor
            </option>
            <option
              value="observation"
              disabled={inv.observations.length >= 500}
            >
              Resident observation
            </option>
          </select>
        </div>
        {mode && (
          <div className="mode-hint">
            Click map or press Enter to enter coordinates.{" "}
            <button onClick={() => onMode("")}>Cancel</button>
          </div>
        )}
      </div>
      <div className="map-legend">
        <span>
          <i className="dot sensor" />
          Measured at monitor
        </span>
        <span>
          <i className="dot candidate" />
          Candidate site
        </span>
        <span>
          <i className="diamond" />
          Source-domain anchor
        </span>
        {inv.result?.source_region90 && (
          <span>Shading: conditional 90% model region*</span>
        )}
        {chosen.length > 0 && (
          <span>
            <i className="dot selected" />
            Selected plan
          </span>
        )}
        <small>
          {geo
            ? "Optional external tiles"
            : "Offline local grid · no interpolated measurements"}
        </small>
      </div>
      {inv.result?.source_region90 && (
        <p className="score-note">
          *Conditional on one source inside the marked domain and this model.
          Shading is not a calibrated geographic confidence region. See
          Scenarios for evidence and predictive checks.
        </p>
      )}
    </section>
  );
}
