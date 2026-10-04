import type { Map as MapLibreMap } from "maplibre-gl";
import type { CameraState, ContextResponse, ViewportItem } from "./types";

export const fmt = (n: number | null | undefined, places = 0) =>
  n == null || !Number.isFinite(n)
    ? "—"
    : n.toLocaleString("en-US", {
        maximumFractionDigits: places,
        minimumFractionDigits: places,
      });

export const isSameId = (a: any, b: any): boolean =>
  a != null && b != null && String(a).trim() === String(b).trim();

export function normalizeItem<T = ViewportItem>(item: any): T {
  if (!item || typeof item !== "object") return item;
  const clone = { ...item };
  if (clone.id != null) clone.id = String(clone.id);
  for (const key of [
    "model_estimates",
    "evidence_explanation",
    "estimates",
    "nearby_monitor",
    "original_coordinates",
  ]) {
    if (typeof clone[key] === "string") {
      try {
        clone[key] = JSON.parse(clone[key]);
      } catch {
        // preserve unparsed value if not JSON
      }
    }
  }
  return clone as T;
}

export const pointFeature = (
  coordinates: [number, number],
  properties: Record<string, unknown>,
) => ({
  type: "Feature" as const,
  id: properties.id != null ? String(properties.id) : undefined,
  geometry: { type: "Point" as const, coordinates },
  properties,
});

export function contextRadiusLabel(data: ContextResponse | null) {
  return data?.query?.radius_km || 50;
}

export const motionDuration = (milliseconds: number) =>
  window.matchMedia("(prefers-reduced-motion: reduce)").matches
    ? 0
    : milliseconds;

export const getSafeBounds = (m: MapLibreMap): [number, number, number, number] => {
  const b = m.getBounds();
  let w = b.getWest();
  let e = b.getEast();
  let s = Math.max(-85, Math.min(85, b.getSouth()));
  let n = Math.max(-85, Math.min(85, b.getNorth()));
  if (e - w >= 360) {
    w = -180;
    e = 180;
  } else {
    while (w < -180 && e < -180) {
      w += 360;
      e += 360;
    }
    while (w > 180 && e > 180) {
      w -= 360;
      e -= 360;
    }
    w = Math.max(-180, Math.min(180, w));
    e = Math.max(-180, Math.min(180, e));
    if (w > e) {
      w = -180;
      e = 180;
    }
  }
  if (s > n) {
    const t = s;
    s = n;
    n = t;
  }
  return [
    Number(w.toFixed(5)),
    Number(s.toFixed(5)),
    Number(e.toFixed(5)),
    Number(n.toFixed(5)),
  ];
};

export const readCamera = (params: URLSearchParams): CameraState | null => {
  if (params.get("v") !== "1") return null;
  const values = (params.get("camera") || "").split(",").map(Number);
  if (values.length !== 5 || values.some((value) => !Number.isFinite(value)))
    return null;
  const [longitude, latitude, zoom, bearing, pitch] = values;
  if (
    longitude < -180 ||
    longitude > 180 ||
    latitude < -85 ||
    latitude > 85 ||
    zoom < 2 ||
    zoom > 15 ||
    bearing < -180 ||
    bearing > 180 ||
    pitch < 0 ||
    pitch > 60
  )
    return null;
  return { longitude, latitude, zoom, bearing, pitch };
};

export const readFeature = (
  value: string | null,
): { kind: "monitors" | "sources"; id: string } | null => {
  if (!value) return null;
  const separator = value.indexOf(":");
  if (separator < 1) return null;
  const kind = value.slice(0, separator);
  const id = value.slice(separator + 1);
  return (kind === "monitors" || kind === "sources") &&
    id.length > 0 &&
    id.length <= 120
    ? { kind, id }
    : null;
};

