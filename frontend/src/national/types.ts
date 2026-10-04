export interface NationalPlace {
  id: string;
  name: string;
  state: string;
  state_fips: string;
  place_type: string;
  latitude: number;
  longitude: number;
  estimates: Record<string, number>;
  model_estimates?: Record<string, ModelEstimate>;
  nearby_monitor?: {
    distance_km: number;
    year: number;
    monitor_id: string;
  } | null;
  population_vintage?: number | string | null;
  withheld_reason?: string | null;
  evidence_explanation?: {
    evidence_class: string;
    why_this_appears: string;
    pollutant: string;
    units: string;
    period: string;
    method: string | null;
    location_meaning: string;
    supporting_monitor: {
      id?: string;
      distance_km?: number;
      measured_value_ug_m3?: number;
    } | null;
    uncertainty_interpretation: string | null;
    does_not_establish: string[];
  };
}
export interface ModelEstimate {
  value_ug_m3: number;
  interval90_low_ug_m3: number;
  interval90_high_ug_m3: number;
  nearest_monitor_km: number;
  reference_monitor_id?: string;
  reference_monitor_value_ug_m3?: number;
  model_id: string;
  support: string;
  evidence_status?: "estimated" | "low_evidence_estimate";
  estimate_latitude?: number;
  estimate_longitude?: number;
  evidence_reason?: string;
}
export interface Monitor extends NationalPlaceCoordinates {
  id: string;
  state_fips?: string;
  county_fips?: string;
  year: number;
  pm25_ug_m3: number;
  sample_completeness: string;
  event_treatment: string;
  pollutant_standard: string;
  metric: string;
  units?: string;
  evidence_type?: string;
}
export interface Facility extends NationalPlaceCoordinates {
  id: string;
  name: string;
  pollutant: string;
  emissions: number;
  units: string;
  category: string;
  company?: string;
  facility_source_type?: string;
  pollutant_code?: string;
  inventory_year: number;
  source: string;
  url: string;
  facility_id?: string;
  canonical_facility_id?: string;
  coordinate_role?: string;
  match_method?: string;
  address?: string | null;
  original_coordinates?: [number, number];
}
export interface NationalPlaceCoordinates {
  latitude: number;
  longitude: number;
}
export interface NationalManifest {
  release: string;
  selected_modeling_year: number;
  annual_monitor_audit: Record<
    string,
    { unique_spatial_site_years: number; state_count: number }
  >;
  place_audit: {
    gazetteer_places: number;
    population_joined_places: number;
    population_join_rate: number;
  };
  source_audit: Record<string, unknown>;
  dataset_sources: Record<
    string,
    {
      url: string;
      vintage?: string | number;
      period?: string;
      license?: string;
    }
  >;
  model?: {
    model_id: string;
    method: string;
    candidate_model_id?: string;
    target: string;
    features: string[];
    selected_sigma_km?: number;
    kernel_bandwidth_km?: number | null;
    ridge?: number | null;
  };
  model_evaluation?: {
    selected_method: Metric;
    rbf_candidate: Metric;
    baselines: Record<string, Metric>;
    paired_rbf_vs_nearest: {
      mae_candidate_minus_nearest_ug_m3: number;
      mae_95pct_interval: number[];
      rmse_candidate_minus_nearest_ug_m3: number;
      rmse_95pct_interval: number[];
      clusters: number;
    };
    by_region: Record<string, Metric>;
    calibration_abs_residual_90pct_ug_m3: number;
    calibration_empirical_coverage_on_final_test: number;
    calibration_interval_width_ug_m3: number;
  };
  model_evaluation_v2?: {
    protocol: string;
    status: string;
    years: Record<string, Record<string, Metric>>;
    selection: {
      selected_model: string;
      fold_wins_vs_nearest_by_year: Record<string, number>;
    };
    deployment: {
      calibration_abs_residual_90pct_ug_m3: number;
      oof_nearest_monitor_distance_p90_support_km: number;
      supported_places: number;
      withheld_places: number;
    };
  };
  counts: {
    searchable_census_places: number;
    monitor_site_years: number;
    monitor_sites_selected_year: number;
    modeled_places: number;
    supported_model_places: number;
    population_covered: number | null;
    places_with_nearby_monitor_proxy?: number;
  };
}
export interface Metric {
  n: number;
  mae_ug_m3: number;
  rmse_ug_m3: number;
  signed_bias_ug_m3?: number;
  bias_ug_m3?: number;
  r2?: number;
  r2_vs_training_mean?: number;
}
export interface NationalSnapshot {
  release: string;
  built_utc?: string;
  generated_utc?: string;
  year: number;
  requested_geoids: string[];
  unknown_geoids: string[];
  items: NationalSnapshotPlace[];
}
export interface NationalSnapshotPlace {
  id: string;
  name: string;
  state: string;
  state_fips: string;
  place_type: string;
  coordinates: [number, number];
  coordinate_reference_system: string;
  coordinate_meaning: string;
  evidence_explanation?: {
    evidence_class: string;
    why_this_appears: string;
    coordinate_meaning: string;
    does_not_establish: string[];
  };
  pollutant: string;
  units: string;
  year: number;
  estimate:
    | (ModelEstimate & { interval_interpretation: string; method: string })
    | null;
  unsupported_reason?: string | null;
  population_2024?: number | null;
  population_vintage?: number | string | null;
  dataset_sources?: Record<string, unknown>;
  generated_utc?: string;
  nearby_inventory_records?: Array<Record<string, unknown>>;
  limitations?: string[] | string;
}

export type Layer = "estimates" | "monitors" | "sources";

export interface CameraState {
  longitude: number;
  latitude: number;
  zoom: number;
  bearing: number;
  pitch: number;
}

export type ViewportItem = Record<string, any> & {
  id: string;
  cluster_id: string;
  member_count: number;
  is_cluster: boolean;
  render_latitude?: number;
  render_longitude?: number;
};

export interface ViewportResult {
  items: ViewportItem[];
  represented_records: number;
  symbol_count: number;
  complete: boolean;
  aggregation_zoom: number;
  dataset_version: string;
}

export interface ClusterSelection {
  kind: Layer;
  id: string;
  count: number;
  members: any[];
  nextOffset: number | null;
  loading: boolean;
}

export interface ContextItem {
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
}

export interface ContextResponse {
  query?: { radius_km: number };
  items: ContextItem[];
  nearest_monitors: ContextItem[];
  closest_facilities: ContextItem[];
  largest_compatible_inventory_groups: {
    pollutant_code: string;
    units: string;
    compatible_record_count: number;
    ranking_meaning: string;
    records: ContextItem[];
  }[];
  counts: {
    measured_monitor_summaries: number;
    facility_inventory_summary_rows: number;
    distinct_facilities: number;
  };
  monitoring_gap: {
    status: string;
    monitor_summary_count: number;
    radius_km: number;
    meaning: string;
  };
  provenance: { monitor_year: number; inventory_year: number };
  limitations: string[];
  place_evidence?: {
    evidence_class: string;
    place: { id: string; name: string; state: string };
    year: number;
    estimate: any;
    coordinate_meaning: string;
    uncertainty: string | null;
  } | null;
  road_context?: {
    available: boolean;
    coverage: string;
    reason?: string;
    city?: string;
    radius_km?: number;
    nearest_major_road?: {
      name: string;
      road_class: string;
      distance_km: number;
    } | null;
    nearby_major_roads?: {
      osm_way_id: string;
      name: string;
      road_class: string;
      distance_km: number;
      segment_count: number;
      way_ids: string[];
    }[];
    major_road_corridor_count_within_radius?: number;
    major_road_length_km_within_radius?: number;
    major_road_length_km_per_km2?: number;
    provenance?: {
      dataset: string;
      source_url: string;
      license: string;
      attribution: string;
      extract_timestamp?: string;
      extract_bounds_wgs84: Record<string, number>;
    };
    interpretation?: string;
  };
}

