export interface Point {
  latitude: number;
  longitude: number;
}
export interface Measurement extends Point {
  sensor_id: string;
  timestamp: string;
  pm25_ug_m3: number;
  uncertainty_ug_m3: number | null;
  flags: string[];
  origin: "user_import" | "synthetic";
}
export interface Weather extends Point {
  timestamp: string;
  wind_speed_m_s: number;
  wind_from_deg: number;
  provenance: string;
  origin: "user_import" | "synthetic";
}
export interface Site extends Point {
  id: string;
  name: string;
  kind: "sensor" | "candidate";
  allowed: boolean;
  power: boolean;
  access: boolean;
  cost: number;
  windows: string[];
}
export interface Plan {
  method: string;
  site_ids: string[];
  cost: number;
  score: number;
  equipment: number;
  window: string;
  mean_score?: number;
  min_score?: number;
  max_score?: number;
  seeds?: number;
}
export interface Result {
  status: string;
  reason?: string;
  warnings: string[];
  plans: Plan[];
  sources: (Point & { id: string; weight: number })[];
  interpretation?: string;
  model_version: string;
  input_hash: string;
  runtime_ms?: number;
  entropy_nats?: number;
  fitted_rmse_ug_m3?: number | null;
  rows_used?: number;
  scenario_count?: number;
  eligible_sites?: number;
  exact_search?: boolean;
  ties?: number | null;
  source_probability?: number | null;
  evidence_status?: "source_supported" | "ambiguous" | "model_mismatch";
  source_region90?: {
    level: number;
    meaning: string;
    area_m2: number;
    domain_area_m2: number;
    resolution_m: number;
    cells: { polygon: Point[]; weight: number }[];
    support: string;
  } | null;
  rows_loaded?: number;
  rows_excluded?: number;
  rows_input?: number;
  selection?: { method: string; limit: number; seed: number };
  diagnostics?: {
    held_out_sensor: {
      sensor_id: string;
      rows: number;
      rmse_ug_m3?: number;
      coverage90?: number;
      mean_nlpd?: number;
      unavailable?: string;
      flagged: boolean;
    }[];
    predictive_warning: boolean;
    method: string;
    sensors_total?: number;
    sensors_checked?: number;
  } | null;
}
export interface ImportRecord {
  id: string;
  filename: string;
  kind: "measurements" | "weather";
  sha256: string;
  raw_csv: string;
  timezone: string;
  column_mapping: Record<string, string>;
  summary: {
    total: number;
    accepted: number;
    invalid: number;
    flagged: number;
    issues: { line: number; error: string }[];
  };
  transformations: string[];
}
export interface Settings {
  budget: number;
  equipment_limit: number;
  window: string;
  noise_ug_m3: number;
  seed: number;
  objective: "scenario_information" | "spatial_coverage";
  inference_limit?: number;
  selection_seed?: number;
}
export interface Investigation {
  id: string;
  name: string;
  concern: string;
  objective: string;
  area: number[];
  synthetic: boolean;
  measurements: Measurement[];
  weather: Weather[];
  sites: Site[];
  source_locations: Point[];
  assumptions: {
    steady: boolean;
    open_terrain: boolean;
    local_weather: boolean;
    note: string;
  };
  settings: Settings;
  imports: ImportRecord[];
  observations: (Point & {
    timestamp: string;
    note: string;
    approximate: boolean;
  })[];
  instruments: Record<string, string>;
  result: Result | null;
  plan_history: Result[];
}
export const emptyInvestigation = (): Investigation => ({
  id: "",
  name: "New investigation",
  concern: "",
  objective: "Choose practical monitoring sites for a community investigation.",
  area: [-0.012, -0.008, 0.012, 0.009],
  synthetic: false,
  measurements: [],
  weather: [],
  sites: [],
  source_locations: [],
  assumptions: {
    steady: false,
    open_terrain: false,
    local_weather: false,
    note: "",
  },
  settings: {
    budget: 350,
    equipment_limit: 2,
    window: "steady-window",
    noise_ug_m3: 2,
    seed: 42,
    objective: "spatial_coverage",
  },
  imports: [],
  observations: [],
  instruments: {},
  result: null,
  plan_history: [],
});
export async function api<T>(
  path: string,
  body?: unknown,
  signal?: AbortSignal,
): Promise<T> {
  const res = await fetch("/api" + path, {
    method: body === undefined ? "GET" : "POST",
    headers: body === undefined ? {} : { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
    signal,
  });
  if (!res.ok) {
    let msg = await res.text();
    try {
      const data = JSON.parse(msg);
      msg =
        typeof data.detail === "string"
          ? data.detail
          : JSON.stringify(data.detail);
    } catch {
      /* text response */
    }
    throw new Error(msg.slice(0, 700));
  }
  return res.json();
}
