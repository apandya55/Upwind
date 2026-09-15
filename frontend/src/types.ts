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
  role?: "primary" | "reference";
  source_id?: string;
  upstream_id?: string;
  direction_systematic_sd_deg?: number | null;
  speed_systematic_fraction?: number | null;
  direction_random_sd_deg?: number;
  comparison_provenance?: string;
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
export interface StrengthPriorSensitivity {
  factors: number[];
  baseline_factor: number;
  alternatives: {
    factor: number;
    source_probability: number;
    posterior_mean: Point;
    density_mode: Point;
    spatial_rms_m: number;
    cell_tv_distance: number;
    posterior_mean_shift_m: number;
  }[];
  thresholds: {
    posterior_mean_shift_m: number;
    cell_tv_distance: number;
  };
  material_factors: number[];
  blocking: boolean;
  meaning: string;
}
export interface Result {
  location_estimate?: {
    posterior_mean: Point;
    density_mode: Point;
    spatial_rms_m: number;
    edge_mass: number;
    domain_limited: boolean;
    meaning: string;
  };
  quadrature_diagnostics?: {
    refined: boolean;
    parents_split: number;
    coarse_cells: number;
    final_cells?: number;
    limitation: string | null;
  };
  meteorology_evidence?: {
    common_mode_prior_probability?: number;
    common_mode_posterior_probability?: number;
    common_mode_meaning?: string;
    status: "unverified" | "comparison_supplied";
    comparison_count: number;
    comparisons_used?: {
      source_id: string;
      upstream_id: string;
      timestamp: string;
      lag_s: number;
      distance_m: number;
      provenance: string;
      origin: string;
    }[];
    independent_upstream_groups: number;
    direction_comparison_correction_deg: number;
    persistent_direction_sd_deg: number;
    speed_comparison_factor: number;
    total_direction_sd_deg: number;
    pollution_conditioned_offset_mean_deg: number;
    source_weather_location_span_m: number;
    weather_warning: boolean;
    meaning: string;
    additional_evidence: string;
    unusable_comparisons: {
      source_id: string;
      timestamp: string;
      reason: string;
    }[];
  } | null;
  status: string;
  reason?: string;
  warnings: string[];
  plans: Plan[];
  sources: (Point & { id: string; weight: number })[];
  interpretation?: string;
  model_version: string;
  protocol_version?: string;
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
  strength_prior_sensitivity?: StrengthPriorSensitivity;
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
  observability?: {
    profile_compatible_domain_fraction: number;
    far_compatible_cells: number;
    conditional_location_information_nats: number;
    meaning: string;
    externalities?: {
      flags: string[];
      blocking: boolean;
      standardized_residual_rms?: number;
      evidence?: Record<string, number | string>;
      meaning: string;
    };
    source_count?: {
      material_competing_pair: boolean;
      improvement_delta_chi2?: number;
      separation_m?: number;
      meaning: string;
    };
    strength_prior_sensitivity?: StrengthPriorSensitivity;
  } | null;
  study_window_count?: number;
  spatial_quadrature_order?: number | null;
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
    windows_checked?: number;
    held_out_window?: {
      window_id: string;
      rows: number;
      flagged: boolean;
      tail_probability?: number;
      unavailable?: string;
    }[];
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
  objective:
    | "scenario_information"
    | "spatial_coverage"
    | "prediction_variance";
  met_direction_sd_deg?: number;
  met_speed_fraction?: number;
  met_uncertainty_provenance?: string;
  source_height_m?: number;
  receptor_height_m?: number;
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
  study_windows?: { id: string; start: string; end: string }[];
  sites: Site[];
  source_locations: Point[];
  assumptions: {
    steady: boolean;
    open_terrain: boolean;
    local_weather: boolean;
    constant_release_across_windows?: boolean;
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
  archived_results?: Record<string, unknown>[];
  compatibility_notes?: string[];
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
