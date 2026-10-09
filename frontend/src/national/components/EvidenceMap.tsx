import { useEffect, useRef, useState } from "react";
import type { PointerEvent as ReactPointerEvent } from "react";
import { Map as MapLibreMap, Marker as MapLibreMarker } from "maplibre-gl";
import type {
  ErrorEvent,
  GeoJSONSource as MapGeoJSONSource,
  MapLayerMouseEvent,
} from "maplibre-gl";
import { LocateFixed, Minus, Plus, SquareDashedMousePointer } from "lucide-react";
import type { CameraState, Layer, NationalPlace, ViewportItem } from "../types";
import { getSafeBounds, motionDuration, normalizeItem, pointFeature, readCamera } from "../utils";

export default function EvidenceMap({
  year,
  layer,
  showSources,
  initialCamera,
  selected,
  selectedPoint,
  onSelect,
  onCluster,
  onBounds,
  onCamera,
  places,
  monitors,
  sources,
}: {
  year: number;
  layer: Layer;
  showSources: boolean;
  initialCamera: CameraState | null;
  selected: NationalPlace | null;
  selectedPoint: [number, number] | null;
  onSelect: (
    kind: Layer,
    id: string,
    coords?: [number, number],
    item?: ViewportItem,
  ) => void;
  onCluster: (
    kind: Layer,
    id: string,
    count: number,
    coordinates: [number, number],
  ) => void;
  onBounds: (bounds: [number, number, number, number], zoom: number) => void;
  onCamera: (camera: CameraState) => void;
  places: ViewportItem[];
  monitors: ViewportItem[];
  sources: ViewportItem[];
}) {
  const target = useRef<HTMLDivElement>(null);
  const map = useRef<MapLibreMap | null>(null);
  const callbacks = useRef({ onBounds, onSelect, onCluster, onCamera });
  useEffect(() => {
    callbacks.current = { onBounds, onSelect, onCluster, onCamera };
  }, [onBounds, onSelect, onCluster, onCamera]);
  const [tileError, setTileError] = useState(false);
  const [areaMode, setAreaMode] = useState(false);
  const areaStart = useRef<{ x: number; y: number } | null>(null);
  const [areaRect, setAreaRect] = useState<{
    left: number;
    top: number;
    width: number;
    height: number;
  } | null>(null);
  const [ready, setReady] = useState(false);
  useEffect(() => {
    if (!target.current) return;
    let restoreCamera: (() => void) | undefined;
    const m = new MapLibreMap({
      container: target.current,
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
        layers: [{ id: "base", type: "raster", source: "osm" }],
      },
      center: initialCamera
        ? [initialCamera.longitude, initialCamera.latitude]
        : [-98.5, 39.8],
      zoom: initialCamera?.zoom ?? 3.1,
      bearing: initialCamera?.bearing ?? 0,
      pitch: initialCamera?.pitch ?? 0,
      minZoom: 2,
      maxZoom: 15,
      attributionControl: { compact: true },
    });
    map.current = m;
    m.on("error", (event: ErrorEvent) => {
      const mapEvent = event as ErrorEvent & {
        sourceId?: string;
        tile?: unknown;
      };
      if (
        event.error &&
        (mapEvent.sourceId === "osm" ||
          mapEvent.tile ||
          /tile|raster/i.test(event.error.message || ""))
      )
        setTileError(true);
    });
    m.on("load", () => {
      m.addSource("countries", { type: "geojson", data: "/countries.geojson" });
      m.addLayer({
        id: "country-coverage",
        type: "fill",
        source: "countries",
        filter: ["!=", ["get", "iso_a2"], "US"],
        paint: { "fill-color": "#66727a", "fill-opacity": 0.035 },
      });
      m.addLayer({
        id: "country-supported",
        type: "fill",
        source: "countries",
        filter: ["==", ["get", "iso_a2"], "US"],
        paint: { "fill-color": "#2a8f82", "fill-opacity": 0.035 },
      });
      m.addLayer({
        id: "country-borders",
        type: "line",
        source: "countries",
        paint: {
          "line-color": "#627079",
          "line-width": ["interpolate", ["linear"], ["zoom"], 2, 0.45, 8, 1.1],
          "line-opacity": 0.5,
        },
      });
      m.addLayer({
        id: "country-unavailable-boundary",
        type: "line",
        source: "countries",
        filter: ["!=", ["get", "iso_a2"], "US"],
        paint: {
          "line-color": "#64736f",
          "line-width": ["interpolate", ["linear"], ["zoom"], 2, 0.7, 8, 1.25],
          "line-opacity": 0.58,
          "line-dasharray": [2, 2],
        },
      });
      m.addSource("places", {
        type: "geojson",
        data: { type: "FeatureCollection", features: [] },
      });
      m.addSource("monitors", {
        type: "geojson",
        data: { type: "FeatureCollection", features: [] },
      });
      m.addSource("facilities", {
        type: "geojson",
        data: { type: "FeatureCollection", features: [] },
      });
      m.addSource("hover-marker", {
        type: "geojson",
        data: { type: "FeatureCollection", features: [] },
      });

      m.addLayer({
        id: "place-clusters",
        type: "circle",
        source: "places",
        filter: ["==", ["get", "is_cluster"], true],
        paint: {
          "circle-color": "#1f6e63",
          "circle-radius": [
            "interpolate",
            ["linear"],
            ["get", "member_count"],
            2,
            4.5,
            10,
            5.5,
            50,
            8,
            200,
            11,
            1000,
            14,
          ],
          "circle-opacity": 0.86,
          "circle-stroke-color": "#ffffff",
          "circle-stroke-width": 1.25,
          "circle-radius-transition": {
            duration: motionDuration(350),
            delay: 0,
          },
          "circle-color-transition": {
            duration: motionDuration(350),
            delay: 0,
          },
          "circle-opacity-transition": {
            duration: motionDuration(250),
            delay: 0,
          },
        },
      });
      m.addLayer({
        id: "place-cluster-count",
        type: "symbol",
        source: "places",
        layout: {
          "text-field": ["to-string", ["get", "member_count"]],
          "text-size": 9,
          "text-allow-overlap": true,
        },
        filter: [
          "all",
          ["==", ["get", "is_cluster"], true],
          [">=", ["get", "member_count"], 5],
        ],
        paint: {
          "text-color": "#ffffff",
          "text-opacity": [
            "interpolate",
            ["linear"],
            ["zoom"],
            2,
            0,
            4.8,
            0,
            6,
            1,
          ],
        },
      });
      m.addLayer({
        id: "place-estimates",
        type: "circle",
        source: "places",
        filter: ["!=", ["get", "is_cluster"], true],
        paint: {
          "circle-radius": [
            "interpolate",
            ["linear"],
            ["zoom"],
            2,
            1.35,
            3.5,
            1.8,
            5.5,
            3,
            7.5,
            4.5,
            9.5,
            7,
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
              "#d6533f",
            ],
          ],
          "circle-opacity": [
            "interpolate",
            ["linear"],
            ["zoom"],
            2,
            0.66,
            3.5,
            0.76,
            5.5,
            0.9,
            8,
            0.96,
          ],
          "circle-stroke-width": [
            "interpolate",
            ["linear"],
            ["zoom"],
            2,
            0.35,
            5,
            0.65,
            8,
            1.25,
          ],
          "circle-stroke-color": "#ffffff",
          "circle-stroke-opacity": 0.95,
          "circle-radius-transition": {
            duration: motionDuration(350),
            delay: 0,
          },
          "circle-color-transition": {
            duration: motionDuration(350),
            delay: 0,
          },
          "circle-opacity-transition": {
            duration: motionDuration(250),
            delay: 0,
          },
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
            "interpolate",
            ["linear"],
            ["get", "member_count"],
            2,
            7,
            10,
            9,
            50,
            12,
            200,
            15,
            1000,
            18,
          ],
          "circle-opacity": 0.92,
          "circle-stroke-color": "#ffffff",
          "circle-stroke-width": 2,
          "circle-radius-transition": {
            duration: motionDuration(350),
            delay: 0,
          },
          "circle-color-transition": {
            duration: motionDuration(350),
            delay: 0,
          },
          "circle-opacity-transition": {
            duration: motionDuration(250),
            delay: 0,
          },
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
            "interpolate",
            ["linear"],
            ["zoom"],
            2,
            3.5,
            4,
            5,
            7,
            7,
            9,
            9,
          ],
          "circle-color": "#2c7ab3",
          "circle-stroke-width": 1.6,
          "circle-stroke-color": "#ffffff",
          "circle-opacity": 0.92,
          "circle-radius-transition": {
            duration: motionDuration(350),
            delay: 0,
          },
          "circle-color-transition": {
            duration: motionDuration(350),
            delay: 0,
          },
          "circle-opacity-transition": {
            duration: motionDuration(250),
            delay: 0,
          },
        },
      });
      m.addLayer({
        id: "facility-clusters",
        type: "circle",
        source: "facilities",
        filter: ["==", ["get", "is_cluster"], true],
        paint: {
          "circle-color": "#c5452d",
          "circle-radius": [
            "interpolate",
            ["linear"],
            ["get", "member_count"],
            2,
            8,
            10,
            10,
            50,
            13,
            200,
            16,
            1000,
            19,
          ],
          "circle-opacity": 0.92,
          "circle-stroke-color": "#ffffff",
          "circle-stroke-width": 2,
          "circle-radius-transition": {
            duration: motionDuration(350),
            delay: 0,
          },
          "circle-color-transition": {
            duration: motionDuration(350),
            delay: 0,
          },
          "circle-opacity-transition": {
            duration: motionDuration(250),
            delay: 0,
          },
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
            "interpolate",
            ["linear"],
            ["zoom"],
            2,
            2.8,
            4,
            3.5,
            7,
            5,
            9,
            7,
          ],
          "circle-color": "#c5452d",
          "circle-stroke-color": "#ffffff",
          "circle-stroke-width": 1.5,
          "circle-opacity": 0.98,
          "circle-radius-transition": {
            duration: motionDuration(350),
            delay: 0,
          },
          "circle-color-transition": {
            duration: motionDuration(350),
            delay: 0,
          },
          "circle-opacity-transition": {
            duration: motionDuration(250),
            delay: 0,
          },
        },
      });
      m.addLayer({
        id: "hover-marker-halo",
        type: "circle",
        source: "hover-marker",
        paint: {
          "circle-radius": [
            "interpolate",
            ["linear"],
            ["zoom"],
            2,
            7,
            5,
            10,
            8,
            14,
          ],
          "circle-color": "#1f6f7d",
          "circle-opacity": 0.25,
          "circle-stroke-width": 1.5,
          "circle-stroke-color": "#123f4a",
          "circle-stroke-opacity": 0.75,
        },
      });
      const interactiveLayers = [
        "place-estimates",
        "place-clusters",
        "place-cluster-count",
        "monitor-clusters",
        "monitor-cluster-count",
        "monitor-points",
        "facility-clusters",
        "facility-cluster-count",
        "facility-points",
      ];
      let lastClickTimestamp = 0;
      const handleFeatureHit = (f: any) => {
        const now = Date.now();
        if (now - lastClickTimestamp < 60) return;
        lastClickTimestamp = now;

        const layerId = String(f.layer?.id || "");
        if (f.properties?.is_cluster) {
          const coordinates = (f.geometry as GeoJSON.Point).coordinates as [
            number,
            number,
          ];
          const kind: Layer = layerId.startsWith("place-")
            ? "estimates"
            : layerId.startsWith("monitor-")
              ? "monitors"
              : "sources";
          callbacks.current.onCluster(
            kind,
            String(f.properties.cluster_id),
            Number(f.properties.member_count),
            coordinates,
          );
          m.easeTo({
            center: coordinates,
            zoom: Math.min(15, m.getZoom() + 2),
            duration: motionDuration(380),
          });
          return;
        }
        const coords = (f.geometry as GeoJSON.Point).coordinates as [
          number,
          number,
        ];
        const properties = normalizeItem<ViewportItem>(f.properties);
        const featureId = String(properties?.id ?? f.id ?? "");
        const kind: Layer = layerId.startsWith("place-")
          ? "estimates"
          : layerId.startsWith("monitor-")
            ? "monitors"
            : "sources";
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
            const coords = (f.geometry as GeoJSON.Point).coordinates as [
              number,
              number,
            ];
            (
              m.getSource("hover-marker") as MapGeoJSONSource | undefined
            )?.setData({
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
            return (
              m.getLayer(id) && m.getLayoutProperty(id, "visibility") !== "none"
            );
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
        if (target.current) {
          target.current.dataset.longitude = center.lng.toFixed(4);
          target.current.dataset.latitude = center.lat.toFixed(4);
          target.current.dataset.zoom = m.getZoom().toFixed(2);
        }
        callbacks.current.onCamera({
          longitude: center.lng,
          latitude: center.lat,
          zoom: m.getZoom(),
          bearing: m.getBearing(),
          pitch: m.getPitch(),
        });
      });
      restoreCamera = () => {
        const camera = readCamera(new URLSearchParams(location.search));
        if (camera)
          m.jumpTo({
            center: [camera.longitude, camera.latitude],
            zoom: camera.zoom,
            bearing: camera.bearing,
            pitch: camera.pitch,
          });
        else
          m.jumpTo({ center: [-98.5, 39.8], zoom: 3.1, bearing: 0, pitch: 0 });
      };
      window.addEventListener("popstate", restoreCamera);
      m.on("boxzoomend", () => setAreaMode(false));
      setReady(true);
      callbacks.current.onBounds(getSafeBounds(m), m.getZoom());
      const center = m.getCenter();
      if (target.current) {
        target.current.dataset.longitude = center.lng.toFixed(4);
        target.current.dataset.latitude = center.lat.toFixed(4);
        target.current.dataset.zoom = m.getZoom().toFixed(2);
      }
      callbacks.current.onCamera({
        longitude: center.lng,
        latitude: center.lat,
        zoom: m.getZoom(),
        bearing: m.getBearing(),
        pitch: m.getPitch(),
      });
    });
    return () => {
      if (restoreCamera) window.removeEventListener("popstate", restoreCamera);
      pulseMarkerRef.current?.remove();
      pulseMarkerRef.current = null;
      m.remove();
      map.current = null;
    };
  }, []);
  useEffect(() => {
    if (!ready || !map.current) return;
    const features = places.map((p) => {
      const rawVal =
        p.value ??
        p.estimate?.value_ug_m3 ??
        p.model_estimates?.[String(year)]?.value_ug_m3;
      const numVal =
        typeof rawVal === "number" && Number.isFinite(rawVal) ? rawVal : null;
      return pointFeature(
        [p.render_longitude ?? p.longitude, p.render_latitude ?? p.latitude],
        { ...p, id: String(p.id), value: numVal },
      );
    });
    (map.current.getSource("places") as MapGeoJSONSource | undefined)?.setData({
      type: "FeatureCollection",
      features,
    } as GeoJSON.FeatureCollection);
  }, [places, year, ready]);
  useEffect(() => {
    if (!ready || !map.current) return;
    const features = monitors.map((p) => {
      const rawVal = p.value ?? p.pm25_ug_m3;
      const numVal =
        typeof rawVal === "number" && Number.isFinite(rawVal) ? rawVal : null;
      return pointFeature(
        [p.render_longitude ?? p.longitude, p.render_latitude ?? p.latitude],
        { ...p, id: String(p.id), name: p.name ?? p.id, value: numVal },
      );
    });
    (
      map.current.getSource("monitors") as MapGeoJSONSource | undefined
    )?.setData({
      type: "FeatureCollection",
      features,
    } as GeoJSON.FeatureCollection);
  }, [monitors, ready]);
  useEffect(() => {
    if (!ready || !map.current) return;
    const features = sources.map((p) => {
      const rawVal = p.value ?? p.emissions;
      const numVal =
        typeof rawVal === "number" && Number.isFinite(rawVal) ? rawVal : null;
      return pointFeature(
        [p.render_longitude ?? p.longitude, p.render_latitude ?? p.latitude],
        { ...p, id: String(p.id), name: p.name, value: numVal },
      );
    });
    (
      map.current.getSource("facilities") as MapGeoJSONSource | undefined
    )?.setData({
      type: "FeatureCollection",
      features,
    } as GeoJSON.FeatureCollection);
  }, [sources, ready]);
  useEffect(() => {
    const m = map.current;
    if (!ready || !m) return;
    const showPlaces = layer === "estimates";
    const showMonitors = layer === "monitors";
    const showFacilities = layer === "sources" || showSources;
    for (const id of [
      "place-estimates",
      "place-clusters",
      "place-cluster-count",
    ])
      m.setLayoutProperty(id, "visibility", showPlaces ? "visible" : "none");
    for (const id of [
      "monitor-clusters",
      "monitor-cluster-count",
      "monitor-points",
    ])
      m.setLayoutProperty(id, "visibility", showMonitors ? "visible" : "none");
    for (const id of [
      "facility-clusters",
      "facility-cluster-count",
      "facility-points",
    ])
      m.setLayoutProperty(
        id,
        "visibility",
        showFacilities ? "visible" : "none",
      );
    (m.getSource("hover-marker") as MapGeoJSONSource | undefined)?.setData({
      type: "FeatureCollection",
      features: [],
    } as GeoJSON.FeatureCollection);
  }, [layer, showSources, ready]);
  const pulseMarkerRef = useRef<MapLibreMarker | null>(null);
  const previousSelectedPointRef = useRef<[number, number] | null>(null);
  const selectionAnimationRef = useRef<number | null>(null);
  useEffect(() => {
    if (!ready || !map.current) return;
    const target =
      selectedPoint ||
      (selected
        ? ([
            (selected as any).render_longitude ?? selected.longitude,
            (selected as any).render_latitude ?? selected.latitude,
          ] as [number, number])
        : null);
    if (target) {
      const previous = previousSelectedPointRef.current;
      const changed =
        !previous || previous[0] !== target[0] || previous[1] !== target[1];
      previousSelectedPointRef.current = target;
      if (!pulseMarkerRef.current && map.current) {
        const el = document.createElement("div");
        el.className = "map-selected-pulse-marker";
        el.innerHTML =
          '<span class="pulse-beacon-ring"></span><span class="pulse-beacon-ring ring-delayed"></span><span class="pulse-beacon-core"></span>';
        pulseMarkerRef.current = new MapLibreMarker({ element: el })
          .setLngLat(target)
          .addTo(map.current);
      } else if (pulseMarkerRef.current) {
        window.cancelAnimationFrame(selectionAnimationRef.current ?? 0);
        if (previous && changed) {
          const started = performance.now();
          const from = previous;
          const tick = (now: number) => {
            const progress = Math.min(1, (now - started) / 520);
            const eased = 1 - Math.pow(1 - progress, 3);
            pulseMarkerRef.current?.setLngLat([
              from[0] + (target[0] - from[0]) * eased,
              from[1] + (target[1] - from[1]) * eased,
            ]);
            if (progress < 1)
              selectionAnimationRef.current =
                window.requestAnimationFrame(tick);
          };
          selectionAnimationRef.current = window.requestAnimationFrame(tick);
        } else {
          pulseMarkerRef.current.setLngLat(target);
        }
      }
      const markerElement = pulseMarkerRef.current?.getElement();
      if (markerElement) {
        markerElement.classList.remove("is-selection-change");
        void markerElement.offsetWidth;
        markerElement.classList.add("is-selection-change");
      }
      if (changed) {
        const narrow = window.matchMedia("(max-width: 1000px)").matches;
        map.current.flyTo({
          center: target,
          zoom: Math.max(map.current.getZoom(), 7.5),
          duration: motionDuration(720),
          essential: true,
          offset: narrow
            ? [0, -Math.min(window.innerHeight * 0.36, 260)]
            : [0, 0],
        });
      }
    } else {
      window.cancelAnimationFrame(selectionAnimationRef.current ?? 0);
      previousSelectedPointRef.current = null;
      pulseMarkerRef.current?.remove();
      pulseMarkerRef.current = null;
    }
  }, [
    selectedPoint,
    selected?.longitude,
    selected?.latitude,
    (selected as any)?.render_longitude,
    (selected as any)?.render_latitude,
    ready,
  ]);
  const resetView = () =>
    map.current?.easeTo({
      center: [-98.5, 39.8],
      zoom: 3.1,
      bearing: 0,
      pitch: 0,
      duration: motionDuration(500),
    });
  const areaPointer = (event: ReactPointerEvent<HTMLDivElement>) => {
    const rect = target.current?.getBoundingClientRect();
    if (!rect) return;
    if (event.type === "pointerdown") {
      event.currentTarget.setPointerCapture(event.pointerId);
      areaStart.current = {
        x: event.clientX - rect.left,
        y: event.clientY - rect.top,
      };
      setAreaRect({
        left: areaStart.current.x,
        top: areaStart.current.y,
        width: 0,
        height: 0,
      });
    } else if (event.type === "pointermove" && areaStart.current) {
      const x = event.clientX - rect.left,
        y = event.clientY - rect.top;
      setAreaRect({
        left: Math.min(x, areaStart.current.x),
        top: Math.min(y, areaStart.current.y),
        width: Math.abs(x - areaStart.current.x),
        height: Math.abs(y - areaStart.current.y),
      });
    } else if (event.type === "pointerup" && areaStart.current && map.current) {
      const start = areaStart.current,
        end = { x: event.clientX - rect.left, y: event.clientY - rect.top };
      areaStart.current = null;
      setAreaRect(null);
      setAreaMode(false);
      if (Math.abs(end.x - start.x) > 12 && Math.abs(end.y - start.y) > 12) {
        const a = map.current.unproject([start.x, start.y]),
          b = map.current.unproject([end.x, end.y]);
        map.current.fitBounds(
          [
            [Math.min(a.lng, b.lng), Math.min(a.lat, b.lat)],
            [Math.max(a.lng, b.lng), Math.max(a.lat, b.lat)],
          ],
          { padding: 42, duration: motionDuration(420) },
        );
      }
    }
  };
  return (
    <div className="national-map-wrap">
      <div
        className="national-map"
        ref={target}
        role="application"
        aria-label="Map of historical U.S. air quality evidence"
      />
      <div
        className={`map-area-capture${areaMode ? " active" : ""}`}
        onPointerDown={areaPointer}
        onPointerMove={areaPointer}
        onPointerUp={areaPointer}
        aria-hidden="true"
      >
        {areaRect && (
          <span
            style={{
              left: areaRect.left,
              top: areaRect.top,
              width: areaRect.width,
              height: areaRect.height,
            }}
          />
        )}
      </div>
      <div className="map-floating-controls" aria-label="Map controls">
        <button
          type="button"
          aria-label="Select map area"
          aria-pressed={areaMode}
          title={
            areaMode
              ? "Drag a rectangle to zoom into an area"
              : "Select an area to zoom into"
          }
          onClick={() => setAreaMode((value) => !value)}
        >
          <SquareDashedMousePointer size={16} />
        </button>
        <button
          type="button"
          aria-label="Zoom in"
          title="Zoom in"
          onClick={() => map.current?.zoomIn()}
        >
          <Plus size={16} />
        </button>
        <button
          type="button"
          aria-label="Zoom out"
          title="Zoom out"
          onClick={() => map.current?.zoomOut()}
        >
          <Minus size={16} />
        </button>
        <button
          type="button"
          aria-label="Reset map view"
          title="Reset map view"
          onClick={resetView}
        >
          <LocateFixed size={16} />
        </button>
      </div>
      {tileError && (
        <div className="national-map-fallback">
          <strong>Map tiles are temporarily unavailable.</strong>
          <span>
            Data, search, comparisons, and exports remain available.
            OpenStreetMap tiles need an internet connection.
          </span>
        </div>
      )}
      <div className="map-source-stamp">
        {layer === "estimates"
          ? `Model estimates · ${year}${showSources ? " + EPA NEI sources" : ""}`
          : layer === "monitors"
            ? `EPA monitors · ${year}${showSources ? " + EPA NEI sources" : ""}`
            : "EPA NEI facilities · 2023"}
      </div>
    </div>
  );
}

