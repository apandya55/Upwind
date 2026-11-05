import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { KeyboardEvent } from "react";
import {
  Activity,
  AlertCircle,
  ArrowRight,
  Bookmark,
  Check,
  ChevronDown,
  CircleHelp,
  Compass,
  Copy,
  Download,
  ExternalLink,
  FileText,
  Layers3,
  MapPin,
  PanelRightClose,
  PanelRightOpen,
  Search,
  Share2,
  Wind,
  X,
} from "lucide-react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import LoadingScreen from "../LoadingScreen";
import Navbar from "../Navbar";
import type {
  CameraState,
  ClusterSelection,
  ContextResponse,
  Facility,
  Layer,
  Monitor,
  NationalManifest,
  NationalPlace,
  NationalSnapshot,
  ViewportItem,
  ViewportResult,
} from "./types";
import { fmt, isSameId, normalizeItem, readCamera, readFeature } from "./utils";
import EvidenceMap from "./components/EvidenceMap";
import EvidenceExplanation from "./components/EvidenceExplanation";
import SourceContext from "./components/SourceContext";
import InvestigationPanel from "./components/InvestigationPanel";
import Methodology from "./components/MethodologyView";

const API_ORIGIN =
  import.meta.env.VITE_API_BASE_URL?.trim().replace(/\/$/, "") || "";
const API = `${API_ORIGIN}/api/national`;

let fallbackDataPromise: Promise<{
  manifest: NationalManifest;
  places: any[];
  monitors: any[];
  sources: any[];
} | null> | null = null;

function getFallbackData() {
  if (!fallbackDataPromise) {
    fallbackDataPromise = fetch("/data/national-fallback.json")
      .then((r) => (r.ok ? r.json() : null))
      .catch(() => null);
  }
  return fallbackDataPromise;
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
  const [investigationOpen, setInvestigationOpen] = useState(false);
  const [year, setYear] = useState(Number(params.get("year")) || 2024);
  const requestedLayer = params.get("layer");
  const [layer, setLayer] = useState<Layer>(
    requestedLayer === "monitors" || requestedLayer === "sources"
      ? requestedLayer
      : "estimates",
  );
  // Facility inventory is a core evidence layer, so keep it visible beside the
  // selected primary layer unless a shared URL explicitly turns the overlay off.
  const [showSources, setShowSources] = useState(
    params.has("sources") ? params.get("sources") === "1" : true,
  );
  const [query, setQuery] = useState("");
  const searchInputRef = useRef<HTMLInputElement>(null);
  const [copiedField, setCopiedField] = useState<string | null>(null);
  const copyToClipboard = async (text: string, field: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedField(field);
      window.setTimeout(() => setCopiedField(null), 1800);
    } catch {
      const ta = document.createElement("textarea");
      ta.value = text;
      ta.style.position = "fixed";
      ta.style.opacity = "0";
      document.body.appendChild(ta);
      ta.select();
      try {
        document.execCommand("copy");
        setCopiedField(field);
        window.setTimeout(() => setCopiedField(null), 1800);
      } finally {
        ta.remove();
      }
    }
  };
  const [searchResults, setSearchResults] = useState<NationalPlace[]>([]);
  const [searchIndex, setSearchIndex] = useState(0);
  const [searchLoading, setSearchLoading] = useState(false);
  const searchRequest = useRef(0);
  const [active, setActive] = useState<{ kind: Layer; id: string } | null>(() =>
    readFeature(params.get("feature")),
  );
  const [activeMapItem, setActiveMapItem] = useState<ViewportItem | null>(null);
  const [selectedCluster, setSelectedCluster] =
    useState<ClusterSelection | null>(null);
  const [comparisonIds, setComparisonIds] = useState<string[]>(() => {
    const shared = params.get("compare");
    if (shared)
      return shared
        .split(",")
        .filter((id) => /^\d{7}$/.test(id))
        .slice(0, 4);
    try {
      const stored = JSON.parse(
        localStorage.getItem("upwind-national-compare") || "[]",
      );
      return Array.isArray(stored)
        ? stored
            .filter((id) => typeof id === "string" && /^\d{7}$/.test(id))
            .slice(0, 4)
        : [];
    } catch {
      return [];
    }
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
  const [printSnapshot, setPrintSnapshot] = useState<NationalSnapshot | null>(
    null,
  );
  const [tab, setTab] = useState<"place" | "methodology">("place");
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [selectionChanging, setSelectionChanging] = useState(false);
  const selectionTimer = useRef<number | undefined>(undefined);
  const [shareCopied, setShareCopied] = useState(false);
  const searchTimer = useRef<number | undefined>(undefined);
  const viewportTimer = useRef<number | undefined>(undefined);
  const viewportRequest = useRef(0);
  const viewportController = useRef<AbortController | null>(null);
  const boundsRef = useRef<[number, number, number, number] | null>(null);
  const zoomRef = useRef(3);
  const cameraRef = useRef<CameraState | null>(readCamera(params));
  const cameraWriteTimer = useRef<number | undefined>(undefined);
  const [selectedPoint, setSelectedPoint] = useState<[number, number] | null>(
    null,
  );
  const pulseSelection = useCallback(() => {
    window.clearTimeout(selectionTimer.current);
    setSelectionChanging(true);
    selectionTimer.current = window.setTimeout(
      () => setSelectionChanging(false),
      260,
    );
  }, []);
  const activePlace = useMemo(() => {
    if (active?.kind === "estimates") {
      const foundInPlaces = places.find((p) => isSameId(p.id, active.id));
      if (foundInPlaces) return foundInPlaces;
      const foundInVisible = visiblePlaces.find((p) =>
        isSameId(p.id, active.id),
      );
      if (foundInVisible) return normalizeItem<NationalPlace>(foundInVisible);
      if (activeMapItem && isSameId(activeMapItem.id, active.id))
        return normalizeItem<NationalPlace>(activeMapItem);
    }
    if (selectedId) {
      const found = places.find((p) => isSameId(p.id, selectedId));
      if (found) return found;
    }
    return null;
  }, [active, places, visiblePlaces, activeMapItem, selectedId]);
  const availableYears = useMemo(
    () =>
      Object.keys(manifest?.annual_monitor_audit || {})
        .map(Number)
        .sort((a, b) => b - a),
    [manifest],
  );
  useEffect(() => {
    if (activePlace && !selectedPoint) {
      setSelectedPoint([
        (activePlace as any).render_longitude ?? activePlace.longitude,
        (activePlace as any).render_latitude ?? activePlace.latitude,
      ]);
    }
  }, [
    activePlace?.id,
    activePlace?.latitude,
    activePlace?.longitude,
    selectedPoint,
  ]);
  useEffect(() => {
    const clear = () => setPrintSnapshot(null);
    window.addEventListener("afterprint", clear);
    return () => window.removeEventListener("afterprint", clear);
  }, []);
  useEffect(() => {
    const handleKeyDown = (e: globalThis.KeyboardEvent) => {
      const tag = (e.target as HTMLElement)?.tagName?.toLowerCase();
      const isInput = tag === "input" || tag === "select" || tag === "textarea";

      // Shortcut: '/' or 'Cmd/Ctrl+K' focuses the search input
      if (!isInput && (e.key === "/" || ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k"))) {
        e.preventDefault();
        searchInputRef.current?.focus();
        searchInputRef.current?.select();
        return;
      }

      if (isInput) return;

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
      fetch(`${API}/manifest`)
        .then(async (r) => {
          if (r.status >= 500) throw new Error("API server error " + r.status);
          const ct = r.headers.get("content-type") || "";
          if (!r.ok || ct.includes("text/html")) {
            const fallback = await getFallbackData();
            if (fallback?.manifest) return fallback.manifest;
            throw new Error("National release is not built yet.");
          }
          return r.json();
        })
        .catch(async (err) => {
          if (err?.message && err.message.startsWith("API server error")) {
            throw new Error("National release is not built yet.");
          }
          const fallback = await getFallbackData();
          if (fallback?.manifest) return fallback.manifest;
          throw new Error("National release is not built yet.");
        }),
    ])
      .then(async ([m]) => {
        setManifest(m);
        const ids = [params.get("place"), ...comparisonIds].filter(
          (id): id is string => !!id,
        );
        const loaded = await Promise.all(
          ids.map((id) =>
            fetch(`${API}/places?geoid=${encodeURIComponent(id)}&year=${year}`)
              .then((r) => (r.ok ? r.json() : { items: [] }))
              .catch(async () => {
                const fallback = await getFallbackData();
                const match = fallback?.places?.find((p: any) => p.id === id);
                return { items: match ? [match] : [] };
              }),
          ),
        );
        const loadedPlaces = loaded.flatMap((result) => result.items || []);
        if (loadedPlaces.length > 0) {
          setPlaces(loadedPlaces);
        } else {
          const fallback = await getFallbackData();
          if (fallback?.places) {
            setPlaces(fallback.places.slice(0, 50));
          }
        }
        setLoading(false);
      })
      .catch((e) => {
        setError(String(e));
        setLoading(false);
      });
  }, []);
  useEffect(() => {
    const restore = () => {
      const p = new URLSearchParams(location.search);
      const restoredYear = Number(p.get("year"));
      const restoredLayer = p.get("layer");
      const ids = (p.get("compare") || "")
        .split(",")
        .filter((id) => /^\d{7}$/.test(id))
        .slice(0, 4);
      const place = p.get("place");
      setYear(
        Number.isFinite(restoredYear) && restoredYear > 0 ? restoredYear : 2024,
      );
      setLayer(
        restoredLayer === "monitors" || restoredLayer === "sources"
          ? restoredLayer
          : "estimates",
      );
      setShowSources(p.has("sources") ? p.get("sources") === "1" : true);
      setSelectedId(place && /^\d{7}$/.test(place) ? place : null);
      const restoredRadius = Number(p.get("radius"));
      setContextRadius(
        [25, 50, 100, 250].includes(restoredRadius) ? restoredRadius : 50,
      );
      setComparisonIds(ids);
      setActive(readFeature(p.get("feature")));
      setActiveMapItem(null);
      const requested = [
        ...new Set(
          [place, ...ids].filter(
            (id): id is string => !!id && /^\d{7}$/.test(id),
          ),
        ),
      ];
      if (requested.length)
        Promise.all(
          requested.map((id) =>
            fetch(
              `${API}/places?geoid=${encodeURIComponent(id)}&year=${restoredYear || 2024}`,
            )
              .then((r) => (r.ok ? r.json() : { items: [] }))
              .catch(() => ({ items: [] })),
          ),
        ).then((rows) =>
          setPlaces((old) => {
            const all = new Map(old.map((x) => [x.id, x]));
            rows
              .flatMap((x) => x.items || [])
              .forEach((x: NationalPlace) => all.set(x.id, x));
            return [...all.values()];
          }),
        );
    };
    window.addEventListener("popstate", restore);
    return () => window.removeEventListener("popstate", restore);
  }, []);
  useEffect(() => {
    if (!active || active.kind === "estimates") return;
    const endpoint =
      active.kind === "monitors"
        ? `${API}/monitors?site_id=${encodeURIComponent(active.id)}&year=-1`
        : `${API}/sources?facility_id=${encodeURIComponent(active.id)}&limit=100`;
    fetch(endpoint)
      .then((response) => (response.ok ? response.json() : null))
      .then((body) => {
        const rows = (body?.items || []).map((row: any) => normalizeItem(row));
        if (active.kind === "monitors")
          setMonitors((old) => [
            ...old.filter((row) => !isSameId(row.id, active.id)),
            ...rows,
          ]);
        else
          setSources((old) => [
            ...old.filter((row) => !isSameId(row.id, active.id)),
            ...rows,
          ]);
        const first = rows[0];
        if (first) setSelectedPoint([first.longitude, first.latitude]);
      })
      .catch(() => undefined);
  }, [active?.kind, active?.id]);
  useEffect(() => {
    window.clearTimeout(searchTimer.current);
    if (!query.trim()) {
      // A quick-place selection can clear the input while its earlier request
      // is still in flight. Ignore that response so it cannot reopen the menu.
      searchRequest.current += 1;
      setSearchLoading(false);
      setSearchResults([]);
      return;
    }
    searchTimer.current = window.setTimeout(() => {
      const [nameQuery, stateQuery] = query
        .split(",")
        .map((part) => part.trim());
      const stateParam = stateQuery
        ? `&state=${encodeURIComponent(stateQuery)}`
        : "";
      const requestId = ++searchRequest.current;
      setSearchLoading(true);
      setSearchError("");
      fetch(
        `${API}/places?q=${encodeURIComponent(nameQuery)}${stateParam}&limit=30&year=${year}`,
      )
        .then((r) => {
          if (!r.ok)
            throw new Error("Place search is temporarily unavailable.");
          return r.json();
        })
        .then((d) => {
          if (requestId === searchRequest.current) {
            setSearchResults(d.items || []);
            setSearchIndex(0);
          }
        })
        .catch(async (e: Error) => {
          if (requestId === searchRequest.current) {
            const fallback = await getFallbackData();
            if (fallback?.places) {
              const lowerName = nameQuery.toLowerCase();
              const lowerState = stateQuery?.toLowerCase();
              const filtered = fallback.places
                .filter((p: any) => {
                  const matchName = p.name.toLowerCase().includes(lowerName);
                  const matchState =
                    !lowerState || p.state.toLowerCase().includes(lowerState);
                  return matchName && matchState;
                })
                .slice(0, 30);
              setSearchResults(filtered);
              setSearchIndex(0);
            } else {
              setSearchResults([]);
              setSearchError(e.message);
            }
          }
        })
        .finally(() => {
          if (requestId === searchRequest.current) setSearchLoading(false);
        });
    }, 180);
    return () => window.clearTimeout(searchTimer.current);
  }, [query, year]);
  useEffect(() => {
    const siteId = activePlace?.nearby_monitor?.monitor_id;
    if (!siteId) return;
    let cancelled = false;
    fetch(`${API}/monitors?site_id=${encodeURIComponent(siteId)}&year=-1`)
      .then((r) => r.json())
      .then((d) => {
        if (!cancelled)
          setMonitors((old) => [
            ...old.filter((m) => m.id !== siteId),
            ...d.items,
          ]);
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, [activePlace?.nearby_monitor?.monitor_id]);
  useEffect(() => {
    if (!activePlace) {
      setContextData(null);
      setContextError("");
      setInvestigationOpen(false);
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
      geoid: activePlace.id,
    });
    fetch(`${API}/context?${params.toString()}`, { signal: controller.signal })
      .then((response) => {
        if (!response.ok)
          throw new Error("Nearby context is temporarily unavailable.");
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
  }, [
    activePlace?.id,
    activePlace?.latitude,
    activePlace?.longitude,
    contextRadius,
    year,
  ]);
  const onBounds = useCallback(
    (bounds: [number, number, number, number], zoom: number) => {
      boundsRef.current = bounds;
      zoomRef.current = zoom;
      window.clearTimeout(viewportTimer.current);
      viewportTimer.current = window.setTimeout(() => {
        const requestId = ++viewportRequest.current;
        viewportController.current?.abort();
        const controller = new AbortController();
        viewportController.current = controller;
        const [west, south, east, north] = bounds;
        const requestedLayers: Layer[] = [
          ...new Set<Layer>([
            layer,
            ...(showSources && layer !== "sources" ? ["sources" as const] : []),
          ]),
        ];
        const perLayerBudget = requestedLayers.length > 1 ? "1500" : "3000";
        const box = (requested: Layer) =>
          new URLSearchParams({
            west: String(west),
            south: String(south),
            east: String(east),
            north: String(north),
            zoom: String(zoom),
            year: String(year),
            layer: requested,
            budget: perLayerBudget,
          }).toString();
        setMapDataError("");
        const current = () =>
          requestId === viewportRequest.current && !controller.signal.aborted;
        Promise.all(
          requestedLayers.map((requested) =>
            fetch(`${API}/viewport?${box(requested)}`, {
              signal: controller.signal,
            })
              .then(async (r) => {
                if (r.status >= 500) {
                  throw new Error(`Server error ${r.status}`);
                }
                const ct = r.headers.get("content-type") || "";
                if (!r.ok || ct.includes("text/html")) {
                  const fallback = await getFallbackData();
                  if (!fallback)
                    throw new Error(`Viewport failed with status ${r.status}`);
                  const list =
                    requested === "estimates"
                      ? fallback.places
                      : ((fallback as any)[requested] || []);
                  const inBounds = list.filter(
                    (item: any) =>
                      item.longitude >= west &&
                      item.longitude <= east &&
                      item.latitude >= south &&
                      item.latitude <= north,
                  );
                  const limit = Math.min(inBounds.length, parseInt(perLayerBudget, 10));
                  return {
                    items: inBounds.slice(0, limit),
                    total: inBounds.length,
                    represented_records: inBounds.length,
                    symbol_count: limit,
                    complete: true,
                    aggregation_zoom: 6,
                    dataset_version: "0.3.0",
                    layer: requested,
                  } as unknown as ViewportResult;
                }
                return r.json() as Promise<ViewportResult>;
              })
              .then((data) => [requested, data] as const)
              .catch(async (err) => {
                if (
                  err?.name === "AbortError" ||
                  (err?.message && err.message.startsWith("Server error"))
                ) {
                  throw err;
                }
                const fallback = await getFallbackData();
                if (!fallback) throw err;
                const list =
                  requested === "estimates"
                    ? fallback.places
                    : ((fallback as any)[requested] || []);
                const inBounds = list.filter(
                  (item: any) =>
                    item.longitude >= west &&
                    item.longitude <= east &&
                    item.latitude >= south &&
                    item.latitude <= north,
                );
                const limit = Math.min(inBounds.length, parseInt(perLayerBudget, 10));
                return [
                  requested,
                  {
                    items: inBounds.slice(0, limit),
                    total: inBounds.length,
                    represented_records: inBounds.length,
                    symbol_count: limit,
                    complete: true,
                    aggregation_zoom: 6,
                    dataset_version: "0.3.0",
                    layer: requested,
                  } as unknown as ViewportResult,
                ] as const;
              }),
          ),
        )
          .then((entries) => {
            if (!current()) return;
            for (const [requested, data] of entries) {
              if (requested === "estimates") {
                setVisiblePlaces(data.items);
                setPlaces((old) => {
                  const merged = new Map(old.map((p) => [p.id, p]));
                  for (const item of data.items)
                    if (!item.is_cluster)
                      merged.set(item.id, item as unknown as NationalPlace);
                  return [...merged.values()];
                });
              } else if (requested === "monitors") setMonitors(data.items);
              else setSources(data.items);
            }
          })
          .catch((e) => {
            if (current() && e?.name !== "AbortError")
              setMapDataError(
                "Map evidence could not be loaded. The previous view remains available; try moving the map again.",
              );
          });
      }, 100);
    },
    [year, layer, showSources],
  );
  const onCamera = useCallback((camera: CameraState) => {
    cameraRef.current = camera;
    window.clearTimeout(cameraWriteTimer.current);
    cameraWriteTimer.current = window.setTimeout(() => {
      const url = new URL(location.href);
      url.searchParams.set("v", "1");
      url.searchParams.set(
        "camera",
        [
          camera.longitude.toFixed(4),
          camera.latitude.toFixed(4),
          camera.zoom.toFixed(2),
          camera.bearing.toFixed(1),
          camera.pitch.toFixed(1),
        ].join(","),
      );
      history.replaceState(null, "", `${url.pathname}${url.search}`);
    }, 180);
  }, []);
  useEffect(() => {
    if (boundsRef.current && !loading)
      onBounds(boundsRef.current, zoomRef.current);
  }, [year, layer, loading, onBounds]);
  const onMapSelect = useCallback(
    (
      kind: Layer,
      id: string,
      coords?: [number, number],
      item?: ViewportItem,
    ) => {
      const normId = String(id).trim();
      const normalizedItem = item
        ? normalizeItem<ViewportItem>(item)
        : undefined;
      pulseSelection();
      setSidebarOpen(true);
      setTab("place");
      setSelectedCluster(null);
      if (kind === "estimates") {
        setSelectedId(normId);
      } else {
        setSelectedId(null);
      }
      setActive({ kind, id: normId });
      const matched =
        normalizedItem ||
        (kind === "estimates"
          ? visiblePlaces.find((p) => isSameId(p.id, normId)) ||
            places.find((p) => isSameId(p.id, normId))
          : kind === "monitors"
            ? monitors.find((p) => isSameId(p.id, normId))
            : sources.find((p) => isSameId(p.id, normId)));
      const resolvedItem = matched
        ? normalizeItem<ViewportItem>(matched)
        : null;
      setActiveMapItem(resolvedItem);
      if (resolvedItem) {
        if (kind === "estimates") {
          setPlaces((old) =>
            old.some((p) => isSameId(p.id, normId))
              ? old.map((p) =>
                  isSameId(p.id, normId) ? { ...p, ...resolvedItem } : p,
                )
              : [...old, resolvedItem as unknown as NationalPlace],
          );
        }
        if (kind === "monitors") {
          setMonitors((old) =>
            old.some((p) => isSameId(p.id, normId))
              ? old.map((p) =>
                  isSameId(p.id, normId) ? { ...p, ...resolvedItem } : p,
                )
              : [...old, resolvedItem],
          );
        }
        if (kind === "sources") {
          setSources((old) =>
            old.some((p) => isSameId(p.id, normId))
              ? old.map((p) =>
                  isSameId(p.id, normId) ? { ...p, ...resolvedItem } : p,
                )
              : [...old, resolvedItem],
          );
        }
      }
      if (coords) {
        setSelectedPoint(coords);
      } else if (resolvedItem) {
        const pt: [number, number] | null =
          resolvedItem.render_longitude != null &&
          resolvedItem.render_latitude != null
            ? [resolvedItem.render_longitude, resolvedItem.render_latitude]
            : resolvedItem.longitude != null && resolvedItem.latitude != null
              ? [resolvedItem.longitude, resolvedItem.latitude]
              : null;
        if (pt) setSelectedPoint(pt);
      } else if (kind === "estimates") {
        const match =
          visiblePlaces.find((p) => isSameId(p.id, normId)) ||
          places.find((p) => isSameId(p.id, normId));
        if (match)
          setSelectedPoint([
            (match as any).render_longitude ?? match.longitude,
            (match as any).render_latitude ?? match.latitude,
          ]);
      } else if (kind === "monitors") {
        const match = monitors.find((m) => isSameId(m.id, normId));
        if (match)
          setSelectedPoint([
            (match as any).render_longitude ?? match.longitude,
            (match as any).render_latitude ?? match.latitude,
          ]);
      } else if (kind === "sources") {
        const match = sources.find((s) => isSameId(s.id, normId));
        if (match)
          setSelectedPoint([
            (match as any).render_longitude ?? match.longitude,
            (match as any).render_latitude ?? match.latitude,
          ]);
      }
      if (kind === "estimates") {
        fetch(`${API}/places?geoid=${encodeURIComponent(normId)}&year=${year}`)
          .then((response) => (response.ok ? response.json() : null))
          .then((body) => {
            const detail = body?.items?.[0] as NationalPlace | undefined;
            if (!detail) return;
            const normDetail = normalizeItem<NationalPlace>(detail);
            setPlaces((old) => {
              const merged = new Map(
                old.map((place) => [String(place.id), place]),
              );
              merged.set(String(normDetail.id), {
                ...merged.get(String(normDetail.id)),
                ...normDetail,
              });
              return [...merged.values()];
            });
          })
          .catch(() => undefined);
      }
    },
    [visiblePlaces, places, monitors, sources, year, pulseSelection],
  );
  const onCluster = useCallback(
    (kind: Layer, id: string, count: number, coordinates: [number, number]) => {
      pulseSelection();
      setSidebarOpen(true);
      setTab("place");
      setActive(null);
      setActiveMapItem(null);
      setSelectedId(null);
      setSelectedPoint(coordinates);
      const bounds = boundsRef.current;
      const selection: ClusterSelection = {
        kind,
        id,
        count,
        members: [],
        nextOffset: 0,
        loading: true,
      };
      setSelectedCluster(selection);
      if (!bounds) return;
      const [west, south, east, north] = bounds;
      const params = new URLSearchParams({
        layer: kind,
        cluster_id: id,
        west: String(west),
        south: String(south),
        east: String(east),
        north: String(north),
        year: String(year),
        offset: "0",
        limit: "50",
      });
      fetch(`${API}/viewport-members?${params}`)
        .then((r) => {
          if (!r.ok) throw new Error();
          return r.json();
        })
        .then((d) =>
          setSelectedCluster((old) =>
            old?.id === id
              ? {
                  ...old,
                  members: d.items,
                  nextOffset: d.next_offset,
                  count: d.total,
                  loading: false,
                }
              : old,
          ),
        )
        .catch(() =>
          setSelectedCluster((old) =>
            old?.id === id ? { ...old, loading: false, nextOffset: null } : old,
          ),
        );
    },
    [year, pulseSelection],
  );
  const loadMoreClusterMembers = () => {
    if (
      !selectedCluster ||
      selectedCluster.nextOffset == null ||
      !boundsRef.current
    )
      return;
    const [west, south, east, north] = boundsRef.current;
    const offset = selectedCluster.nextOffset;
    const params = new URLSearchParams({
      layer: selectedCluster.kind,
      cluster_id: selectedCluster.id,
      west: String(west),
      south: String(south),
      east: String(east),
      north: String(north),
      year: String(year),
      offset: String(offset),
      limit: "50",
    });
    setSelectedCluster({ ...selectedCluster, loading: true });
    fetch(`${API}/viewport-members?${params}`)
      .then((r) => {
        if (!r.ok) throw new Error();
        return r.json();
      })
      .then((d) =>
        setSelectedCluster((old) =>
          old?.id === selectedCluster.id
            ? {
                ...old,
                members: [...old.members, ...d.items],
                nextOffset: d.next_offset,
                loading: false,
              }
            : old,
        ),
      )
      .catch(() =>
        setSelectedCluster((old) =>
          old?.id === selectedCluster.id ? { ...old, loading: false } : old,
        ),
      );
  };
  useEffect(() => {
    if (!manifest) return;
    const search = new URLSearchParams();
    search.set("year", String(year));
    search.set("layer", layer);
    if (showSources) search.set("sources", "1");
    if (selectedId) search.set("place", selectedId);
    if (active && active.kind !== "estimates")
      search.set("feature", `${active.kind}:${active.id}`);
    if (comparisonIds.length) search.set("compare", comparisonIds.join(","));
    search.set("radius", String(contextRadius));
    if (cameraRef.current) {
      search.set("v", "1");
      search.set(
        "camera",
        [
          cameraRef.current.longitude.toFixed(4),
          cameraRef.current.latitude.toFixed(4),
          cameraRef.current.zoom.toFixed(2),
          cameraRef.current.bearing.toFixed(1),
          cameraRef.current.pitch.toFixed(1),
        ].join(","),
      );
    }
    const next = `${location.pathname}?${search.toString()}`;
    if (`${location.pathname}${location.search}` !== next)
      history.replaceState(null, "", next);
  }, [
    manifest,
    year,
    layer,
    showSources,
    selectedId,
    active?.kind,
    active?.id,
    comparisonIds,
    contextRadius,
  ]);
  const selectedMonitor = useMemo(() => {
    if (active?.kind !== "monitors") return null;
    const found = monitors.find((m) => isSameId(m.id, active.id));
    if (found) return normalizeItem<Monitor>(found);
    if (activeMapItem && isSameId(activeMapItem.id, active.id))
      return normalizeItem<Monitor>(activeMapItem);
    return null;
  }, [active, monitors, activeMapItem]);

  const selectedFacility = useMemo(() => {
    if (active?.kind !== "sources") return null;
    const found = sources.find((s) => isSameId(s.id, active.id));
    if (found) return normalizeItem<Facility>(found);
    if (activeMapItem && isSameId(activeMapItem.id, active.id))
      return normalizeItem<Facility>(activeMapItem);
    return null;
  }, [active, sources, activeMapItem]);

  const nearbyMonitors = useMemo(
    () =>
      activePlace?.nearby_monitor
        ? monitors
            .filter((m) =>
              isSameId(m.id, activePlace.nearby_monitor?.monitor_id),
            )
            .sort((a, b) => a.year - b.year)
        : [],
    [activePlace, monitors],
  );
  const nearbyYearMonitor = useMemo(
    () => nearbyMonitors.find((m) => m.year === year),
    [nearbyMonitors, year],
  );
  const chartData = nearbyMonitors.map((m) => ({
    year: m.year,
    measured: m.pm25_ug_m3,
  }));
  const comparisons = comparisonIds
    .map((id) => places.find((p) => isSameId(p.id, id)))
    .filter((p): p is NationalPlace => !!p);
  const comparisonPlaces =
    activePlace && !comparisons.some((p) => isSameId(p.id, activePlace.id))
      ? [activePlace, ...comparisons]
      : comparisons;
  const selectPlace = (place: NationalPlace) => {
    pulseSelection();
    setSidebarOpen(true);
    setActiveMapItem(null);
    history.pushState(
      null,
      "",
      `${location.pathname}?${new URLSearchParams({ year: String(year), layer, place: String(place.id), ...(comparisonIds.length ? { compare: comparisonIds.join(",") } : {}) }).toString()}`,
    );
    setPlaces((old) =>
      old.some((p) => isSameId(p.id, place.id)) ? old : [...old, place],
    );
    setSelectedId(String(place.id));
    setActive({ kind: "estimates", id: String(place.id) });
    setSelectedPoint([
      (place as any).render_longitude ?? place.longitude,
      (place as any).render_latitude ?? place.latitude,
    ]);
    setQuery("");
    setSearchResults([]);
    setTab("place");
  };
  const closeDetail = () => {
    pulseSelection();
    setActive(null);
    setActiveMapItem(null);
    setSelectedId(null);
    setSelectedPoint(null);
    setSelectedCluster(null);
  };
  const toggleCompare = (id: string) => {
    const next = comparisonIds.some((cid) => isSameId(cid, id))
      ? comparisonIds.filter((x) => !isSameId(x, id))
      : comparisonIds.length < 4
        ? [...comparisonIds, id]
        : [...comparisonIds.slice(1), id];
    history.pushState(
      null,
      "",
      `${location.pathname}?${new URLSearchParams({ year: String(year), layer, ...(selectedId ? { place: selectedId } : {}), ...(next.length ? { compare: next.join(",") } : {}) }).toString()}`,
    );
    localStorage.setItem("upwind-national-compare", JSON.stringify(next));
    setComparisonIds(next);
  };
  const snapshotIds = [
    ...new Set(
      [selectedId, ...comparisonIds].filter((id): id is string => !!id),
    ),
  ].slice(0, 5);
  const snapshotUrl = (format: "json" | "csv" | "geojson") =>
    `${API}/snapshot${format === "json" ? "" : `.${format}`}?geoids=${snapshotIds.join(",")}&year=${year}`;
  const exportSnapshot = async (format: "csv" | "geojson") => {
    if (!snapshotIds.length) return;
    setExportError("");
    try {
      const response = await fetch(snapshotUrl(format));
      if (!response.ok)
        throw new Error("The selected place snapshot could not be exported.");
      const filename = response.headers
        .get("content-disposition")
        ?.match(/filename\*?=(?:UTF-8''|\")?([^\";]+)/i)?.[1];
      const link = document.createElement("a");
      const href = URL.createObjectURL(await response.blob());
      link.href = href;
      link.download = filename
        ? decodeURIComponent(filename.replaceAll('"', ""))
        : `upwind-national-${year}-snapshot.${format}`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.setTimeout(() => URL.revokeObjectURL(href), 1000);
    } catch {
      setExportError(
        "Export could not be loaded. Check the connection and try again.",
      );
    }
  };
  const exportInvestigation = () => {
    if (!activePlace) return;
    const payload = {
      title: `UPWIND Local Pollution Investigation — ${activePlace.name}, ${activePlace.state}`,
      generated_utc: new Date().toISOString(),
      location: {
        geoid: activePlace.id,
        latitude: activePlace.latitude,
        longitude: activePlace.longitude,
        coordinate_meaning: "Census Gazetteer internal point",
      },
      year,
      place_evidence: contextData?.place_evidence ?? {
        estimate: activePlace.model_estimates?.[String(year)] ?? null,
      },
      nearby_monitor_summaries: contextData?.nearest_monitors ?? [],
      nearby_nei_inventory_records: contextData?.closest_facilities ?? [],
      road_context: contextData?.road_context ?? { available: false },
      provenance: contextData?.provenance ?? null,
      limitations: contextData?.limitations ?? [],
      notes:
        "Proximity provides geographic context; it does not indicate specific facility contribution or causation.",
    };
    const blob = new Blob([JSON.stringify(payload, null, 2)], {
      type: "application/json",
    });
    const href = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = href;
    link.download = `upwind-investigation-${activePlace.id}-${year}.json`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.setTimeout(() => URL.revokeObjectURL(href), 1000);
  };
  const printBrief = async () => {
    setPrintError("");
    if (!snapshotIds.length) {
      window.print();
      return;
    }
    try {
      const response = await fetch(snapshotUrl("json"));
      if (!response.ok)
        throw new Error("The print snapshot could not be prepared.");
      setPrintSnapshot((await response.json()) as NationalSnapshot);
      window.setTimeout(() => window.print(), 50);
    } catch {
      setPrintError(
        "The print snapshot could not be loaded. Check the connection and try again.",
      );
    }
  };
  const share = async () => {
    const url = new URL(location.href);
    if (cameraRef.current) {
      url.searchParams.set("v", "1");
      url.searchParams.set(
        "camera",
        [
          cameraRef.current.longitude.toFixed(4),
          cameraRef.current.latitude.toFixed(4),
          cameraRef.current.zoom.toFixed(2),
          cameraRef.current.bearing.toFixed(1),
          cameraRef.current.pitch.toFixed(1),
        ].join(","),
      );
    }
    try {
      await navigator.clipboard.writeText(url.toString());
      setShareCopied(true);
      window.setTimeout(() => setShareCopied(false), 2200);
    } catch {
      // Fallback for browsers with strict clipboard permissions
      const ta = document.createElement("textarea");
      ta.value = url.toString();
      ta.style.position = "fixed";
      ta.style.opacity = "0";
      document.body.appendChild(ta);
      ta.select();
      try {
        document.execCommand("copy");
        setShareCopied(true);
        window.setTimeout(() => setShareCopied(false), 2200);
      } catch {
        // Keep quiet if execCommand also fails
      } finally {
        ta.remove();
      }
    }
  };
  const onSearchKey = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key === "ArrowDown" && searchResults.length) {
      event.preventDefault();
      setSearchIndex((i) => (i + 1) % searchResults.length);
    } else if (event.key === "ArrowUp" && searchResults.length) {
      event.preventDefault();
      setSearchIndex(
        (i) => (i + searchResults.length - 1) % searchResults.length,
      );
    } else if (event.key === "Enter" && searchResults[searchIndex])
      selectPlace(searchResults[searchIndex]);
    if (event.key === "Escape") {
      setQuery("");
      setSearchResults([]);
    }
  };

  return (
    <main
      className={`national-shell${sidebarOpen ? "" : " sidebar-collapsed"}${comparisons.length > 0 ? " has-comparison" : ""}`}
    >
      {printSnapshot && (
        <section
          className="print-snapshot"
          aria-label="Printable evidence snapshot"
        >
          <header>
            <strong>UPWIND · Historical air quality evidence</strong>
            <span>
              Release {printSnapshot.release} · built{" "}
              {printSnapshot.built_utc || "not recorded"} · generated{" "}
              {printSnapshot.generated_utc || "not recorded"}
            </span>
          </header>
          <h1>Place evidence · {printSnapshot.year}</h1>
          <p>
            PM2.5 annual mean at Census Gazetteer internal points. These are
            point estimates, not place averages, current conditions, exposure,
            forecasts, or source attribution. The empirical spatial out-of-fold
            interval does not guarantee local coverage.
          </p>
          <div className="print-snapshot-grid">
            {printSnapshot.items.map((item) => (
              <article key={item.id}>
                <h2>
                  {item.name}, {item.state}
                </h2>
                <p>
                  GEOID {item.id} · {item.place_type}
                </p>
                <strong>
                  {item.estimate
                    ? `${fmt(item.estimate.value_ug_m3, 2)} µg/m³`
                    : "Estimate withheld"}
                </strong>
                <p>
                  {item.estimate
                    ? `${fmt(item.estimate.interval90_low_ug_m3, 2)}–${fmt(item.estimate.interval90_high_ug_m3, 2)} µg/m³ · ${item.estimate.interval_interpretation}`
                    : item.unsupported_reason ||
                      "No supported estimate for this place and year."}
                </p>
                <p>
                  WGS84 internal point: {item.coordinates[1].toFixed(5)},{" "}
                  {item.coordinates[0].toFixed(5)} · {item.coordinate_meaning}
                </p>
                <p>
                  Supporting AQS monitor:{" "}
                  {item.estimate?.reference_monitor_id || "not identified"} ·{" "}
                  {fmt(item.estimate?.nearest_monitor_km)} km
                </p>
                <p>
                  {item.evidence_explanation?.why_this_appears ||
                    `Annual ${item.year} model evidence at this point.`}
                </p>
                {!!item.nearby_inventory_records?.length && (
                  <>
                    <h3>
                      Nearby EPA NEI inventory records · not ambient
                      measurements
                    </h3>
                    {item.nearby_inventory_records
                      .slice(0, 3)
                      .map((record, index) => (
                        <p
                          key={`${record.facility_id || record.summary_row_id}:${index}`}
                        >
                          {String(
                            record.name ||
                              record.facility_id ||
                              "EPA inventory record",
                          )}{" "}
                          ·{" "}
                          {String(
                            record.pollutant_code || "pollutant not specified",
                          )}{" "}
                          · {fmt(Number(record.emissions), 2)}{" "}
                          {String(record.units || "")} · inventory{" "}
                          {String(record.inventory_year || "year unavailable")}{" "}
                          · {fmt(Number(record.distance_km), 1)} km from
                          internal point
                        </p>
                      ))}
                  </>
                )}
                <p>
                  Population 2024:{" "}
                  {item.population_2024 == null
                    ? "not reported"
                    : fmt(item.population_2024)}{" "}
                  · vintage {item.population_vintage || "not recorded"}
                </p>
              </article>
            ))}
          </div>
          <p>
            Sources and provenance are available from the versioned dataset
            release. EPA NEI facility rows describe inventory estimates and do
            not show contribution to ambient concentration.
          </p>
          <h2>Questions for further investigation</h2>
          <ul>
            <li>
              Are the annual observation period and nearby AQS monitor suitable
              for the local question being asked?
            </li>
            <li>
              Which local, tribal, or community monitoring records could fill
              gaps in this release?
            </li>
            <li>
              Can listed inventory facilities be verified against current
              records, permits, or mapped facility boundaries?
            </li>
            <li>
              What timestamped weather and independent measurements would be
              needed before testing a non-causal association?
            </li>
          </ul>
        </section>
      )}
      <Navbar active="map" onShare={share} shareCopied={shareCopied}>
        <section className="national-toolbar" aria-label="Explorer controls">
          <div className="national-search">
            <Search size={15} />
            <input
              ref={searchInputRef}
              aria-label="Search Census places"
              aria-expanded={!!searchResults.length}
              aria-controls="national-place-results"
              aria-activedescendant={
                searchResults[searchIndex]
                  ? `national-place-${searchResults[searchIndex].id}`
                  : undefined
              }
              placeholder="Search Census places…"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={onSearchKey}
            />
            {query && (
              <button
                aria-label="Clear search"
                onClick={() => {
                  setQuery("");
                  setSearchResults([]);
                  setSearchError("");
                  searchInputRef.current?.focus();
                }}
              >
                <X size={14} />
              </button>
            )}
            {!!searchResults.length && (
              <div
                id="national-place-results"
                className="search-results"
                role="listbox"
              >
                {searchResults.map((p, i) => (
                  <button
                    id={`national-place-${p.id}`}
                    role="option"
                    aria-selected={i === searchIndex}
                    key={p.id}
                    onMouseEnter={() => setSearchIndex(i)}
                    onClick={() => selectPlace(p)}
                  >
                    <span>{p.name}</span>
                    <small>
                      {p.state} · {p.place_type}
                    </small>
                  </button>
                ))}
              </div>
            )}
            {!!query.trim() && searchLoading && (
              <div className="search-results" role="status">
                Searching Census places…
              </div>
            )}
            {!!query.trim() && !searchLoading && !searchResults.length && (
              <div className="search-results" role="status">
                {searchError ||
                  `No Census places match “${query}”. Include the state name to distinguish places.`}
              </div>
            )}
          </div>
          <label className="national-select">
            <span>Historical year</span>
            <select
              aria-label="Historical year"
              value={year}
              onChange={(e) => {
                const next = Number(e.target.value);
                const modelingYear = manifest?.selected_modeling_year ?? 2024;
                let nextLayer = layer;
                if (layer === "estimates" && next !== modelingYear) {
                  nextLayer = "monitors";
                }
                setYear(next);
                if (nextLayer !== layer) setLayer(nextLayer);
                history.pushState(
                  null,
                  "",
                  `${location.pathname}?${new URLSearchParams({ year: String(next), layer: nextLayer, ...(selectedId ? { place: selectedId } : {}), ...(comparisonIds.length ? { compare: comparisonIds.join(",") } : {}) }).toString()}`,
                );
              }}
            >
              {availableYears.map((y) => (
                <option key={y} value={y}>
                  {y}
                  {y === manifest?.selected_modeling_year
                    ? " · modeled + monitors"
                    : y === 2025
                      ? " · preliminary monitors"
                      : " · measured monitors"}
                </option>
              ))}
            </select>
            <ChevronDown size={14} />
          </label>
          <div className="national-layer-controls">
            <div
              className="national-layers"
              role="group"
              aria-label="Map evidence layer"
            >
              <button
                type="button"
                aria-pressed={layer === "estimates"}
                className={layer === "estimates" ? "selected" : ""}
                title={
                  year !== (manifest?.selected_modeling_year ?? 2024)
                    ? `Modeled place estimates (${manifest?.selected_modeling_year ?? 2024})`
                    : "Model estimates"
                }
                onClick={() => {
                  const modelingYear = manifest?.selected_modeling_year ?? 2024;
                  const targetYear =
                    year !== modelingYear ? modelingYear : year;
                  if (targetYear !== year) setYear(targetYear);
                  setLayer("estimates");
                  history.pushState(
                    null,
                    "",
                    `${location.pathname}?${new URLSearchParams({ year: String(targetYear), layer: "estimates", ...(selectedId ? { place: selectedId } : {}), ...(comparisonIds.length ? { compare: comparisonIds.join(",") } : {}) }).toString()}`,
                  );
                }}
              >
                <Activity size={14} /> Estimates
              </button>
              <button
                type="button"
                aria-pressed={layer === "monitors"}
                className={layer === "monitors" ? "selected" : ""}
                onClick={() => {
                  history.pushState(
                    null,
                    "",
                    `${location.pathname}?${new URLSearchParams({ year: String(year), layer: "monitors", ...(selectedId ? { place: selectedId } : {}), ...(comparisonIds.length ? { compare: comparisonIds.join(",") } : {}) }).toString()}`,
                  );
                  setLayer("monitors");
                }}
              >
                <MapPin size={14} /> Monitors
              </button>
              <button
                type="button"
                aria-pressed={layer === "sources"}
                className={layer === "sources" ? "selected" : ""}
                onClick={() => {
                  history.pushState(
                    null,
                    "",
                    `${location.pathname}?${new URLSearchParams({ year: String(year), layer: "sources", ...(selectedId ? { place: selectedId } : {}), ...(comparisonIds.length ? { compare: comparisonIds.join(",") } : {}) }).toString()}`,
                  );
                  setLayer("sources");
                }}
              >
                <Layers3 size={14} /> EPA facilities
              </button>
            </div>
            <div
              className="national-overlay-control"
              role="group"
              aria-label="Evidence overlays"
            >
              <button
                type="button"
                aria-pressed={showSources}
                className={`source-overlay-toggle${showSources ? " is-active" : ""}`}
                title="Overlay EPA NEI facility records on the selected map layer"
                onClick={() => {
                  const next = !showSources;
                  setShowSources(next);
                  const nextParams = new URLSearchParams(location.search);
                  next
                    ? nextParams.set("sources", "1")
                    : nextParams.delete("sources");
                  history.replaceState(
                    null,
                    "",
                    `${location.pathname}?${nextParams.toString()}`,
                  );
                }}
              >
                <span className="source-toggle-indicator" aria-hidden="true" />
                <Layers3 size={14} />
                <span>{showSources ? "Overlay on" : "Overlay facilities"}</span>
              </button>
            </div>
          </div>
        </section>
      </Navbar>
      {error && (
        <div className="national-alert" role="alert">
          <div className="alert-content">
            <AlertCircle size={15} />
            <div>
              <strong>National release unavailable</strong>
              <span>
                {error} Run the data acquisition and model build commands in
                scripts/build_national_dataset.py.
              </span>
            </div>
          </div>
          <button
            type="button"
            className="alert-dismiss"
            aria-label="Dismiss notice"
            onClick={() => setError("")}
          >
            <X size={14} />
          </button>
        </div>
      )}
      {mapDataError && !loading && (
        <div className="national-alert" role="alert">
          <div className="alert-content">
            <AlertCircle size={15} />
            <div>
              <strong>Some map evidence is unavailable</strong>
              <span>{mapDataError}</span>
            </div>
          </div>
          <button
            type="button"
            className="alert-dismiss"
            aria-label="Dismiss notice"
            onClick={() => setMapDataError("")}
          >
            <X size={14} />
          </button>
        </div>
      )}
      {loading ? (
        <LoadingScreen
          fullScreen={true}
          message="Loading map data…"
          submessage="Preparing places, monitors, and historical estimates"
        />
      ) : (
        <>
          <div
            className={`national-main-grid${activePlace || active || selectedCluster ? " has-selection" : ""}`}
          >
            <section
              className="national-map-panel"
              aria-label="National evidence map"
            >
              <div className="national-map-heading">
                <div className="national-map-title-card">
                  <span className="national-kicker">
                    United States ·{" "}
                    {layer === "estimates"
                      ? "Annual PM2.5"
                      : layer === "monitors"
                        ? "EPA monitor sites"
                        : "Emissions inventory"}
                  </span>
                  <h2>
                    {activePlace?.name
                      ? `${activePlace.name}, ${activePlace.state}`
                      : "National evidence map"}
                  </h2>
                  <span
                    className="map-place-count-tag"
                    style={{
                      display: "block",
                      fontSize: "11px",
                      color: "#64748B",
                      marginTop: "2px",
                    }}
                  >
                    {fmt(manifest?.counts.searchable_census_places)} searchable
                    Census places
                  </span>
                  {manifest?.release?.startsWith("upwind-test-fixture-") && (
                    <span
                      role="status"
                      aria-label="Test data notice"
                      className="map-place-count-tag"
                    >
                      Synthetic test data · not release data
                    </span>
                  )}
                </div>
                <span className="map-data-pill">
                  {layer === "estimates"
                    ? `${fmt(manifest?.counts.supported_model_places)} supported places`
                    : layer === "monitors"
                      ? `${fmt(manifest?.annual_monitor_audit?.[String(year)]?.unique_spatial_site_years)} monitor site-years in ${year}`
                      : `EPA inventory · 2023`}
                </span>
              </div>
              <EvidenceMap
                year={year}
                layer={layer}
                showSources={showSources}
                initialCamera={readCamera(params)}
                selected={activePlace}
                selectedPoint={selectedPoint}
                onSelect={onMapSelect}
                onCluster={onCluster}
                onBounds={onBounds}
                onCamera={onCamera}
                places={visiblePlaces}
                monitors={monitors.filter((m) => m.year === year)}
                sources={sources}
              />
              <div
                className="map-hud-stack"
                role="region"
                aria-label="Map status and legend"
              >
                {layer === "estimates" &&
                  !visiblePlaces.some(
                    (p) => p.model_estimates?.[String(year)],
                  ) &&
                  (year !== (manifest?.selected_modeling_year ?? 2024) ? (
                    <div className="map-empty map-year-notice" role="status">
                      <div className="map-notice-header">
                        <AlertCircle size={15} />
                        <strong>
                          Model estimates are published for{" "}
                          {manifest?.selected_modeling_year ?? 2024}
                        </strong>
                      </div>
                      <p>
                        EPA measured monitor observations are available for{" "}
                        {year}.
                      </p>
                      <div className="map-notice-actions">
                        <button
                          type="button"
                          className="notice-btn primary"
                          onClick={() => {
                            setLayer("monitors");
                            history.pushState(
                              null,
                              "",
                              `${location.pathname}?${new URLSearchParams({ year: String(year), layer: "monitors", ...(selectedId ? { place: selectedId } : {}), ...(comparisonIds.length ? { compare: comparisonIds.join(",") } : {}) }).toString()}`,
                            );
                          }}
                        >
                          <MapPin size={13} /> View {year} EPA monitors
                        </button>
                        <button
                          type="button"
                          className="notice-btn secondary"
                          onClick={() => {
                            const mYear =
                              manifest?.selected_modeling_year ?? 2024;
                            setYear(mYear);
                            history.pushState(
                              null,
                              "",
                              `${location.pathname}?${new URLSearchParams({ year: String(mYear), layer: "estimates", ...(selectedId ? { place: selectedId } : {}), ...(comparisonIds.length ? { compare: comparisonIds.join(",") } : {}) }).toString()}`,
                            );
                          }}
                        >
                          Switch to {manifest?.selected_modeling_year ?? 2024}{" "}
                          estimates
                        </button>
                      </div>
                    </div>
                  ) : (
                    <p className="map-empty" role="status">
                      No supported place estimates are loaded in this map view
                      for {year}. Search a place or pan the map.
                    </p>
                  ))}
                {layer === "monitors" &&
                  !monitors.some((m) => m.year === year) && (
                    <p className="map-empty" role="status">
                      No measured EPA AQS monitor records are loaded in this map
                      view for {year}.
                    </p>
                  )}
                {(layer === "sources" || showSources) && !sources.length && (
                  <p className="map-empty" role="status">
                    No EPA NEI facility records are loaded in this map view.
                  </p>
                )}
                <div
                  className={`map-legend ${layer === "monitors" ? "legend-monitors" : layer === "sources" ? "legend-sources" : "legend-estimates"}`}
                  aria-label={`Legend: ${layer === "monitors" ? "measured monitor values" : "modeled point estimates"}${showSources || layer === "sources" ? " and facility inventory" : ""}`}
                >
                  {layer === "sources" ? (
                    <>
                      <span>
                        <i className="legend-dot facility" />
                        EPA inventory facility
                      </span>
                      <span className="legend-note">
                        Primary PM2.5 · reported source units · NEI 2023
                      </span>
                    </>
                  ) : (
                    <>
                      {layer === "monitors" ? (
                        <>
                          <span>
                            <i className="legend-dot measured" />
                            Measured AQS site
                          </span>
                          <span className="legend-note">
                            {year} annual mean · µg/m³
                          </span>
                        </>
                      ) : (
                        <>
                          <span>
                            <i className="legend-dot low" />
                            &lt;6 µg/m³
                          </span>
                          <span>
                            <i className="legend-dot mid" />
                            6–10 µg/m³
                          </span>
                          <span>
                            <i className="legend-dot high" />
                            &gt;10 µg/m³
                          </span>
                          <span className="legend-note">
                            Model estimate · {year} annual mean
                          </span>
                        </>
                      )}
                      {showSources && (
                        <span>
                          <i className="legend-dot facility" />
                          EPA NEI facility · reported annual emissions
                        </span>
                      )}
                    </>
                  )}
                </div>
                <div className="map-caveat">
                  <CircleHelp size={14} />
                  <span>
                    {layer === "estimates"
                      ? "Point estimates at Census Gazetteer locations (U.S. release) · historical, not live or citywide."
                      : layer === "monitors"
                        ? "Measured annual summaries at EPA monitoring sites (U.S. release) · historical, not live."
                        : "Annual EPA inventory records (U.S. release) · proximity does not establish contribution."}
                    {(showSources || layer === "sources") &&
                      " Inventory locations are separate records, not proven contributors."}
                  </span>
                  <button
                    type="button"
                    className="map-method-link"
                    onClick={() => setTab("methodology")}
                  >
                    Read limits
                  </button>
                </div>
              </div>
            </section>
            {!sidebarOpen && (
              <button
                type="button"
                className="floating-sidebar-toggle"
                aria-label="Show sidebar details"
                title="Show sidebar details (Press [)"
                onClick={(e) => {
                  e.stopPropagation();
                  setSidebarOpen(true);
                }}
              >
                <PanelRightOpen size={16} />
                <span>
                  {activePlace ? activePlace.name : "Places & Details"}
                </span>
              </button>
            )}
            <aside
              className={`national-detail-panel${sidebarOpen ? "" : " is-hidden"}`}
              aria-label="Place details and evidence sidebar"
            >
              <div
                className={`detail-panel-content${selectionChanging ? " is-selection-changing" : ""}`}
              >
                {tab === "methodology" ? (
                  <Methodology
                    manifest={manifest}
                    onBack={() => setTab("place")}
                    onToggleSidebar={() => setSidebarOpen(false)}
                  />
                ) : activePlace ? (
                  <>
                    <div className="detail-title-row">
                      <div>
                        <span className="national-kicker">
                          CENSUS{" "}
                          {(activePlace.place_type || "PLACE").toUpperCase()}
                        </span>
                        <h2>{activePlace.name || "Selected Census place"}</h2>
                        <p className="detail-place-meta">
                          <span>
                            {activePlace.state || "State unavailable"} · GEOID{" "}
                            {activePlace.id}
                          </span>
                          <button
                            type="button"
                            className="copy-pill-btn"
                            onClick={() => copyToClipboard(activePlace.id, "geoid")}
                            title="Copy GEOID to clipboard"
                            aria-label={`Copy GEOID ${activePlace.id}`}
                          >
                            {copiedField === "geoid" ? (
                              <>
                                <Check size={11} /> Copied
                              </>
                            ) : (
                              <>
                                <Copy size={11} /> Copy ID
                              </>
                            )}
                          </button>
                        </p>
                      </div>
                      <div className="detail-header-actions">
                        <button
                          type="button"
                          className="sidebar-toggle-btn"
                          aria-label="Hide sidebar"
                          title="Hide sidebar (Press [)"
                          onClick={(e) => {
                            e.stopPropagation();
                            setSidebarOpen(false);
                          }}
                        >
                          <PanelRightClose size={14} />
                          <span>Hide</span>
                        </button>
                        <button
                          className="icon-action"
                          aria-label="Close selected place"
                          onClick={closeDetail}
                        >
                          <X size={17} />
                        </button>
                      </div>
                    </div>
                    <div className="investigate-action">
                      <button
                        type="button"
                        className="primary-investigate"
                        aria-expanded={investigationOpen}
                        onClick={() => setInvestigationOpen((value) => !value)}
                      >
                        <Compass size={16} />
                        {investigationOpen
                          ? "Close investigation"
                          : "Investigate Location"}
                      </button>
                      <span>
                        Nearby measurements, inventory records, and road
                        context.
                      </span>
                    </div>
                    {investigationOpen && (
                      <InvestigationPanel
                        place={activePlace}
                        year={year}
                        data={contextData}
                        onExport={exportInvestigation}
                      />
                    )}
                    <div className="detail-metric">
                      <div>
                        <span>
                          {activePlace.model_estimates?.[String(year)]
                            ? `MODEL ESTIMATE · ${year}`
                            : nearbyYearMonitor
                              ? `NEARBY AQS MONITOR · ${year}`
                              : `MODEL ESTIMATE · ${year}`}
                        </span>
                        <strong>
                          {activePlace.model_estimates?.[String(year)]
                            ? fmt(
                                activePlace.model_estimates[String(year)]
                                  .value_ug_m3,
                                2,
                              )
                            : nearbyYearMonitor
                              ? fmt(nearbyYearMonitor.pm25_ug_m3, 2)
                              : fmt(undefined, 2)}{" "}
                          <small>µg/m³</small>
                        </strong>
                      </div>
                      <div className="metric-chip">
                        {activePlace.model_estimates?.[String(year)]
                          ?.evidence_status === "low_evidence_estimate"
                          ? "Low evidence"
                          : activePlace.model_estimates?.[String(year)]
                            ? "Estimated"
                            : nearbyYearMonitor
                              ? `AQS measured (${year})`
                              : "Insufficient evidence"}
                      </div>
                    </div>
                    {activePlace.model_estimates?.[String(year)] ? (
                      <>
                        <div className="uncertainty-block">
                          <span>
                            {activePlace.model_estimates[String(year)]
                              .evidence_status === "low_evidence_estimate"
                              ? "Low-evidence estimate · spatial OOF 90% error band"
                              : "Estimated point · spatial OOF 90% error band"}
                          </span>
                          <strong>
                            {fmt(
                              activePlace.model_estimates[String(year)]
                                .interval90_low_ug_m3,
                              2,
                            )}{" "}
                            –{" "}
                            {fmt(
                              activePlace.model_estimates[String(year)]
                                .interval90_high_ug_m3,
                              2,
                            )}{" "}
                            µg/m³
                          </strong>
                          <small>
                            Band from geographic out-of-fold monitor-site
                            errors. It is broad, describes this model
                            evaluation, and does not guarantee local coverage or
                            an area-average bound.
                          </small>
                        </div>
                        <div className="fact-grid">
                          <div>
                            <span>Nearest training monitor</span>
                            <b>
                              {fmt(
                                activePlace.model_estimates[String(year)]
                                  .nearest_monitor_km,
                              )}{" "}
                              km · AQS{" "}
                              {activePlace.model_estimates[String(year)]
                                .reference_monitor_id || "ID unavailable"}
                            </b>
                          </div>
                          <div>
                            <span>Population · 2024</span>
                            <b>
                              {activePlace.estimates?.["2024"]
                                ? fmt(activePlace.estimates["2024"])
                                : "Not reported"}
                            </b>
                          </div>
                        </div>
                      </>
                    ) : (
                      <div className="no-estimate">
                        <strong>Estimate withheld for {year}</strong>
                        <p>
                          {activePlace.withheld_reason ||
                            `No supported model estimate is published for this place in ${year}. The release supports ${manifest?.selected_modeling_year} only and withholds locations outside its geographic or monitor-distance support.`}
                        </p>
                        {nearbyYearMonitor && (
                          <div className="nearby-monitor-callout">
                            <span>Nearest measured EPA monitor in {year}</span>
                            <b>
                              {fmt(nearbyYearMonitor.pm25_ug_m3, 2)}{" "}
                              <small>µg/m³</small>
                            </b>
                            <small>
                              AQS Site {nearbyYearMonitor.id} ·{" "}
                              {fmt(activePlace.nearby_monitor?.distance_km, 1)}{" "}
                              km from Census internal point
                            </small>
                          </div>
                        )}
                        <button
                          onClick={() => {
                            history.pushState(
                              null,
                              "",
                              `${location.pathname}?${new URLSearchParams({ year: String(year), layer: "monitors", ...(selectedId ? { place: selectedId } : {}), ...(comparisonIds.length ? { compare: comparisonIds.join(",") } : {}) }).toString()}`,
                            );
                            setLayer("monitors");
                          }}
                        >
                          View {year} measured monitors
                        </button>
                      </div>
                    )}
                    <div className="detail-actions">
                      <button
                        className="soft-button"
                        onClick={() => toggleCompare(activePlace.id)}
                      >
                        <Bookmark size={15} />
                        {comparisonIds.includes(activePlace.id)
                          ? "Remove comparison"
                          : "Compare place"}
                      </button>
                      <button className="soft-button" onClick={share}>
                        <Share2 size={15} />
                        {shareCopied ? "Link copied" : "Share"}
                      </button>
                      <button
                        className="soft-button"
                        onClick={() => exportSnapshot("csv")}
                      >
                        <Download size={15} /> Export place
                      </button>
                    </div>
                    <section className="detail-section">
                      <div className="section-title-line">
                        <h3>Nearby measured history</h3>
                        <span>EPA AQS annual summaries</span>
                      </div>
                      {chartData.length > 1 ? (
                        <div className="history-chart">
                          <ResponsiveContainer width="100%" height={160}>
                            <LineChart
                              data={chartData}
                              margin={{
                                left: -25,
                                right: 8,
                                top: 8,
                                bottom: 2,
                              }}
                            >
                              <CartesianGrid
                                stroke="#e6e8e3"
                                vertical={false}
                              />
                              <XAxis
                                dataKey="year"
                                tick={{ fontSize: 10, fill: "#637079" }}
                                axisLine={false}
                                tickLine={false}
                              />
                              <YAxis
                                tick={{ fontSize: 10, fill: "#637079" }}
                                axisLine={false}
                                tickLine={false}
                              />
                              <Tooltip
                                formatter={(v) => [
                                  `${fmt(Number(v), 2)} µg/m³`,
                                  "Measured annual PM2.5",
                                ]}
                              />
                              <Line
                                type="monotone"
                                dataKey="measured"
                                stroke="#247b70"
                                strokeWidth={2.5}
                                dot={{ r: 3, fill: "#247b70" }}
                              />
                            </LineChart>
                          </ResponsiveContainer>
                        </div>
                      ) : (
                        <p className="muted-note">
                          No consistent nearby monitor history under the 5 km
                          Gazetteer-point rule. Monitor-site history remains
                          separately searchable.
                        </p>
                      )}
                    </section>
                    <EvidenceExplanation place={activePlace} year={year} />
                    <SourceContext
                      data={contextData}
                      loading={contextLoading}
                      error={contextError}
                      radius={contextRadius}
                      onRadiusChange={(next) => {
                        setContextRadius(next);
                        const nextParams = new URLSearchParams(location.search);
                        nextParams.set("radius", String(next));
                        history.pushState(
                          null,
                          "",
                          `${location.pathname}?${nextParams.toString()}`,
                        );
                      }}
                    />
                  </>
                ) : selectedCluster ? (
                  <>
                    <div className="detail-title-row">
                      <div>
                        <span className="national-kicker">
                          {selectedCluster.kind === "estimates"
                            ? "PLACE ESTIMATES"
                            : selectedCluster.kind === "monitors"
                              ? "EPA MONITORS"
                              : "EPA INVENTORY SOURCES"}
                        </span>
                        <h2>{fmt(selectedCluster.count)} records nearby</h2>
                        <p>Select a record to see its details.</p>
                      </div>
                      <div className="detail-header-actions">
                        <button
                          type="button"
                          className="sidebar-toggle-btn"
                          aria-label="Hide sidebar"
                          title="Hide sidebar (Press [)"
                          onClick={(e) => {
                            e.stopPropagation();
                            setSidebarOpen(false);
                          }}
                        >
                          <PanelRightClose size={14} />
                          <span>Hide</span>
                        </button>
                        <button
                          className="icon-action"
                          aria-label="Close record details"
                          onClick={closeDetail}
                        >
                          <X size={17} />
                        </button>
                      </div>
                    </div>
                    <div className="detail-section">
                      <h3>Records</h3>
                      {selectedCluster.loading &&
                        !selectedCluster.members.length && (
                          <p role="status">Loading records…</p>
                        )}
                      {selectedCluster.members.map((member, index) => (
                        <div
                          className="source-row"
                          key={`${member.id}:${index}`}
                          style={{ cursor: "pointer" }}
                          onClick={() => {
                            const coords: [number, number] | undefined =
                              member.render_longitude != null &&
                              member.render_latitude != null
                                ? [
                                    member.render_longitude,
                                    member.render_latitude,
                                  ]
                                : member.longitude != null &&
                                    member.latitude != null
                                  ? [member.longitude, member.latitude]
                                  : undefined;
                            onMapSelect(
                              selectedCluster.kind,
                              String(member.id),
                              coords,
                              member,
                            );
                          }}
                        >
                          <span>
                            <b>{member.name || member.id}</b>
                            <small>
                              {member.state ||
                                member.category ||
                                (member.year
                                  ? `EPA AQS · ${member.year}`
                                  : selectedCluster.kind === "estimates"
                                    ? "Census place estimate"
                                    : "EPA inventory record")}
                            </small>
                          </span>
                          <span>
                            {selectedCluster.kind === "estimates"
                              ? `${fmt(member.model_estimates?.[String(year)]?.value_ug_m3, 2)} µg/m³`
                              : selectedCluster.kind === "monitors"
                                ? `${fmt(member.pm25_ug_m3, 2)} µg/m³`
                                : `${fmt(member.emissions, 2)} ${member.units || ""}`}
                          </span>
                        </div>
                      ))}
                      {selectedCluster.nextOffset != null && (
                        <button
                          className="soft-button"
                          onClick={loadMoreClusterMembers}
                          disabled={selectedCluster.loading}
                        >
                          {selectedCluster.loading
                            ? "Loading…"
                            : "Load more records"}
                        </button>
                      )}
                    </div>
                  </>
                ) : selectedMonitor ? (
                  <>
                    <div className="detail-title-row">
                      <div>
                        <span className="national-kicker">
                          MEASURED · EPA AQS
                        </span>
                        <h2>Monitor {selectedMonitor.id}</h2>
                        <p>{selectedMonitor.year} annual PM2.5 summary</p>
                      </div>
                      <div className="detail-header-actions">
                        <button
                          type="button"
                          className="sidebar-toggle-btn"
                          aria-label="Hide sidebar"
                          title="Hide sidebar (Press [)"
                          onClick={(e) => {
                            e.stopPropagation();
                            setSidebarOpen(false);
                          }}
                        >
                          <PanelRightClose size={14} />
                          <span>Hide</span>
                        </button>
                        <button
                          className="icon-action"
                          aria-label="Close monitor details"
                          onClick={closeDetail}
                        >
                          <X size={17} />
                        </button>
                      </div>
                    </div>
                    <div className="detail-metric">
                      <div>
                        <span>MEASURED ANNUAL MEAN</span>
                        <strong>
                          {fmt(selectedMonitor.pm25_ug_m3, 2)}{" "}
                          <small>µg/m³</small>
                        </strong>
                      </div>
                    </div>
                    <div className="detail-facts">
                      <p>
                        Completeness indicator:{" "}
                        <b>{selectedMonitor.sample_completeness}</b>
                      </p>
                      <p>
                        Event treatment:{" "}
                        <b>{selectedMonitor.event_treatment}</b>
                      </p>
                      <p>
                        Pollutant standard:{" "}
                        <b>{selectedMonitor.pollutant_standard}</b>
                      </p>
                      <p>
                        Metric: <b>{selectedMonitor.metric}</b>
                      </p>
                      <p>
                        Coordinates: {selectedMonitor.latitude.toFixed(4)},{" "}
                        {selectedMonitor.longitude.toFixed(4)}
                      </p>
                    </div>
                  </>
                ) : selectedFacility ? (
                  <>
                    <div className="detail-title-row">
                      <div>
                        <span className="national-kicker">
                          INVENTORY ESTIMATE · EPA NEI{" "}
                          {selectedFacility.inventory_year}
                        </span>
                        <h2>{selectedFacility.name}</h2>
                        <p>
                          EIS facility ID{" "}
                          {selectedFacility.facility_id || selectedFacility.id}{" "}
                          · {selectedFacility.pollutant_code} ·{" "}
                          {selectedFacility.category}
                        </p>
                      </div>
                      <div className="detail-header-actions">
                        <button
                          type="button"
                          className="sidebar-toggle-btn"
                          aria-label="Hide sidebar"
                          title="Hide sidebar (Press [)"
                          onClick={(e) => {
                            e.stopPropagation();
                            setSidebarOpen(false);
                          }}
                        >
                          <PanelRightClose size={14} />
                          <span>Hide</span>
                        </button>
                        <button
                          className="icon-action"
                          aria-label="Close source details"
                          onClick={closeDetail}
                        >
                          <X size={17} />
                        </button>
                      </div>
                    </div>
                    <div className="detail-metric">
                      <div>
                        <span>
                          {selectedFacility.pollutant_code} · REPORTED EMISSIONS
                        </span>
                        <strong>
                          {fmt(selectedFacility.emissions, 2)}{" "}
                          <small>{selectedFacility.units}</small>
                        </strong>
                      </div>
                    </div>
                    <div className="detail-facts">
                      <p>
                        Location:{" "}
                        <b>Approximate inventory facility coordinate</b>
                      </p>
                      <p>
                        Coordinate role:{" "}
                        {selectedFacility.coordinate_role ||
                          "Reported facility coordinate; not a release point."}
                      </p>
                      <p>
                        WGS84:{" "}
                        {(
                          selectedFacility.original_coordinates || [
                            selectedFacility.longitude,
                            selectedFacility.latitude,
                          ]
                        )
                          .map((value: number) => value.toFixed(5))
                          .join(", ")}
                      </p>
                      <p>
                        Identity:{" "}
                        <b>
                          {selectedFacility.match_method ||
                            "Exact EPA EIS facility identifier"}
                        </b>{" "}
                        · canonical{" "}
                        {selectedFacility.canonical_facility_id ||
                          `epa-eis:${selectedFacility.id}`}
                      </p>
                      <p>
                        Verified address or footprint:{" "}
                        <b>
                          {selectedFacility.address ||
                            "not available in this release"}
                        </b>
                      </p>
                    </div>
                    <p className="source-disclaimer">
                      This is a facility-level annual inventory estimate for{" "}
                      {selectedFacility.inventory_year}, not ambient
                      concentration. It does not show the facility's
                      contribution to a nearby monitor. The map retains the
                      original NEI coordinate; it is not snapped to a building
                      or treated as a release point.
                    </p>
                    <a
                      className="external-link"
                      href={selectedFacility.url}
                      target="_blank"
                      rel="noreferrer"
                    >
                      Open EPA inventory source data <ExternalLink size={14} />
                    </a>
                  </>
                ) : active ? (
                  <div className="detail-loading-state" role="status">
                    <div className="detail-title-row">
                      <div>
                        <span className="national-kicker">LOADING RECORD</span>
                        <h2>
                          Loading the selected{" "}
                          {active.kind === "estimates"
                            ? "place estimate"
                            : active.kind === "monitors"
                              ? "monitor site"
                              : "inventory source"}
                          …
                        </h2>
                        <p>Loading the documented record {active.id}.</p>
                      </div>
                      <div className="detail-header-actions">
                        <button
                          type="button"
                          className="sidebar-toggle-btn"
                          aria-label="Hide sidebar"
                          title="Hide sidebar (Press [)"
                          onClick={(e) => {
                            e.stopPropagation();
                            setSidebarOpen(false);
                          }}
                        >
                          <PanelRightClose size={14} />
                          <span>Hide</span>
                        </button>
                        <button
                          className="icon-action"
                          aria-label="Close"
                          onClick={closeDetail}
                        >
                          <X size={17} />
                        </button>
                      </div>
                    </div>
                  </div>
                ) : (
                  <>
                    <div className="detail-title-row">
                      <div>
                        <span className="national-kicker">FIND A PLACE</span>
                        <h2>Find a place</h2>
                        <p>Search for a place or select a point on the map.</p>
                      </div>
                      <div className="detail-header-actions">
                        <button
                          type="button"
                          className="sidebar-toggle-btn"
                          aria-label="Hide sidebar"
                          title="Hide sidebar (Press [)"
                          onClick={(e) => {
                            e.stopPropagation();
                            setSidebarOpen(false);
                          }}
                        >
                          <PanelRightClose size={14} />
                          <span>Hide</span>
                        </button>
                      </div>
                    </div>
                    <div className="quick-places">
                      <span>Try Charlotte, Durham, Raleigh, or Denver</span>
                      {[
                        { name: "Charlotte", state: "North Carolina" },
                        { name: "Durham", state: "North Carolina" },
                        { name: "Raleigh", state: "North Carolina" },
                        { name: "Denver", state: "Colorado" },
                      ].map(({ name, state }) => (
                        <button
                          key={name}
                          onClick={() => {
                            setQuery(`${name}, ${state}`);
                            fetch(
                              `${API}/places?q=${encodeURIComponent(name)}&state=${encodeURIComponent(state)}&limit=10&year=${year}`,
                            )
                              .then((r) => {
                                if (!r.ok) throw new Error();
                                return r.json();
                              })
                              .then(
                                (d) => d.items?.[0] && selectPlace(d.items[0]),
                              )
                              .catch(() =>
                                setSearchError(
                                  "Place search is temporarily unavailable.",
                                ),
                              );
                          }}
                        >
                          {name}
                          <ArrowRight size={13} />
                        </button>
                      ))}
                    </div>
                  </>
                )}
              </div>
            </aside>
          </div>
          {(comparisons.length > 0 || !!activePlace) && (
            <section className="comparison-panel">
              <div className="comparison-heading">
                <div>
                  <span className="national-kicker">
                    SIDE BY SIDE · SAME YEAR
                  </span>
                  <h2>
                    Place comparison <small>{year}</small>
                  </h2>
                </div>
                <div className="export-actions">
                  <button onClick={() => exportSnapshot("csv")}>
                    <Download size={15} /> CSV
                  </button>
                  <button onClick={() => exportSnapshot("geojson")}>
                    GeoJSON
                  </button>
                  <button aria-label="Print brief" onClick={printBrief}>
                    <FileText size={15} /> Create community report
                  </button>
                  <button
                    aria-label="Clear comparisons"
                    onClick={() => {
                      setComparisonIds([]);
                      localStorage.removeItem("upwind-national-compare");
                      history.pushState(
                        null,
                        "",
                        `${location.pathname}?${new URLSearchParams({ year: String(year), layer, ...(selectedId ? { place: selectedId } : {}) }).toString()}`,
                      );
                    }}
                  >
                    <X size={16} />
                  </button>
                </div>
              </div>
              {printError && (
                <p className="national-alert" role="alert">
                  {printError}
                </p>
              )}
              {exportError && (
                <p className="national-alert" role="alert">
                  {exportError}
                </p>
              )}
              <p className="source-disclaimer">
                Estimates that share a reference monitor are not independent.
                Overlapping broad error bands mean their ordering is uncertain;
                differences are descriptive and may not be distinguishable
                within the empirical spatial error band.
              </p>
              <div className="comparison-list" role="list">
                {comparisonPlaces.map((p) => (
                  <article key={p.id} role="listitem">
                    <button
                      className="comparison-remove"
                      onClick={() => toggleCompare(p.id)}
                      aria-label={`Remove ${p.name}`}
                    >
                      <X size={13} />
                    </button>
                    <span>
                      {p.state} · {p.place_type}
                    </span>
                    <h3>{p.name}</h3>
                    <strong>
                      {fmt(p.model_estimates?.[String(year)]?.value_ug_m3, 2)}{" "}
                      <small>µg/m³</small>
                    </strong>
                    <p>
                      {p.model_estimates?.[String(year)]
                        ? `90% band ${fmt(p.model_estimates[String(year)].interval90_low_ug_m3, 2)}–${fmt(p.model_estimates[String(year)].interval90_high_ug_m3, 2)}`
                        : "Estimate withheld for selected period"}
                    </p>
                    {comparisonPlaces.some(
                      (other) =>
                        other.id !== p.id &&
                        other.model_estimates?.[String(year)]
                          ?.reference_monitor_id ===
                          p.model_estimates?.[String(year)]
                            ?.reference_monitor_id,
                    ) && (
                      <small>
                        Shares the same reference monitor as another selected
                        place; comparison is correlated.
                      </small>
                    )}
                  </article>
                ))}
              </div>
            </section>
          )}
          <footer
            className="national-method-note"
            aria-label="Methodology disclaimer"
          >
            <p>
              Historical estimates are place-point estimates at Census Gazetteer
              locations, not live conditions, exposure, or source attribution.
            </p>
            <a href="/methodology">
              Read the methodology and limitations <ArrowRight size={14} />
            </a>
          </footer>
        </>
      )}
    </main>
  );
}
