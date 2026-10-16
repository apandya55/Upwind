import { ExternalLink, PanelRightClose, X } from "lucide-react";
import type { NationalManifest } from "../types";
import { fmt } from "../utils";

export default function MethodologyView({
  manifest,
  onBack,
  onToggleSidebar,
}: {
  manifest: NationalManifest | null;
  onBack: () => void;
  onToggleSidebar?: () => void;
}) {
  const v2 = manifest?.model_evaluation_v2;
  const cv = manifest?.counts;
  const r24 = v2?.years["2024"];
  const r25 = v2?.years["2025"];

  return (
    <>
      <div className="detail-title-row">
        <div>
          <span className="national-kicker">
            METHODOLOGY & DATA MODEL
          </span>
          <h2>How to read this map</h2>
          <p>
            Annual PM2.5 at a Census place point, separate from nearby source
            records.
          </p>
        </div>
        <div className="detail-header-actions">
          {onToggleSidebar && (
            <button
              type="button"
              className="sidebar-toggle-btn"
              aria-label="Hide sidebar"
              title="Hide sidebar (Press [)"
              onClick={(e) => {
                e.stopPropagation();
                onToggleSidebar();
              }}
            >
              <PanelRightClose size={14} />
              <span>Hide</span>
            </button>
          )}
          <button
            className="icon-action"
            onClick={onBack}
            aria-label="Back to explorer"
          >
            <X size={17} />
          </button>
        </div>
      </div>
      <div className="methodology-copy">
        <h3>Target and deployed model</h3>
        <p>
          Target: EPA AQS annual PM2.5 summary (parameter 88101; annual
          standard; quarterly means of daily means; completeness flag Y), in
          µg/m³. The deployed model is {manifest?.model?.method}. It predicts at
          the Census Gazetteer internal point. Gazetteer points are not place
          polygons; results are not citywide or neighborhood averages.
        </p>
        <p>
          The deployed model transfers the nearest eligible monitor value. A
          fixed 150 km Gaussian kernel and a Gaussian-plus-PRISM-temperature
          candidate were evaluated using spatial block cross-validation. Because
          nearest-monitor assignment provided more consistent performance across
          sparse regions, it remains the primary deployed interpolation method.
        </p>
        <h3>Geographic development comparison</h3>
        <p>
          Spatial out-of-fold scores use the training-fold mean as the R²
          reference. On all corrected eligible monitor sites: 2024 (n=
          {fmt(r24?.nearest_monitor?.n)}) nearest-monitor MAE{" "}
          {fmt(r24?.nearest_monitor?.mae_ug_m3, 2)}, RMSE{" "}
          {fmt(r24?.nearest_monitor?.rmse_ug_m3, 2)}, bias{" "}
          {fmt(r24?.nearest_monitor?.bias_ug_m3, 2)}; Gaussian MAE{" "}
          {fmt(r24?.gaussian_kernel_ridge_150km?.mae_ug_m3, 2)}, RMSE{" "}
          {fmt(r24?.gaussian_kernel_ridge_150km?.rmse_ug_m3, 2)}. Provisional
          2025 (n={fmt(r25?.nearest_monitor?.n)}) nearest-monitor MAE{" "}
          {fmt(r25?.nearest_monitor?.mae_ug_m3, 2)}, RMSE{" "}
          {fmt(r25?.nearest_monitor?.rmse_ug_m3, 2)}; Gaussian MAE{" "}
          {fmt(r25?.gaussian_kernel_ridge_150km?.mae_ug_m3, 2)}, RMSE{" "}
          {fmt(r25?.gaussian_kernel_ridge_150km?.rmse_ug_m3, 2)}. On the matched
          PRISM comparison rows (2024 n=872; provisional 2025 n=882), Gaussian
          plus PRISM temperature scored MAE/RMSE/bias 1.320/1.859/−0.081 and
          1.384/1.872/−0.202 µg/m³ respectively. It won 5/5 2024 folds but only
          3/5 provisional 2025 folds. The existing rule requires at least four
          wins in both years, so this candidate is not deployed. PRISM annual
          grids are retrospective, not available for a beginning-of-year
          forecast. Negative R² means squared error exceeded the training-fold
          mean reference. The 2025 archive is provisional and supplementary.
        </p>
        <p>
          The symmetric 90th-percentile absolute error band is ±
          {fmt(v2?.deployment.calibration_abs_residual_90pct_ug_m3, 2)} µg/m³,
          estimated from spatial out-of-fold monitor-site residuals. It is not a
          local guarantee. Publication withholds locations outside the
          contiguous-U.S. domain or beyond{" "}
          {fmt(v2?.deployment.oof_nearest_monitor_distance_p90_support_km)} km
          from an eligible monitor; farther places remain searchable without a
          prediction. The low-evidence label marks places beyond the 75th
          percentile of observed out-of-fold monitor distance; it is a distance
          evidence tier, not a validated local uncertainty class.
        </p>
        <h3>Coverage</h3>
        <p>
          {fmt(cv?.searchable_census_places)} Census places are searchable;{" "}
          {fmt(cv?.supported_model_places)} have a 2024 estimate;{" "}
          {fmt(v2?.deployment.withheld_places)} are withheld. Population
          coverage sums available 2024 Census estimates for unique modeled place
          GEOIDs ({fmt(cv?.population_covered)} residents); it is geographic
          coverage, not users reached or impact. EPA monitor proximity uses 5 km
          from the Gazetteer internal point, not legal-boundary containment.
        </p>
        <h3>Data and limitations</h3>
        <ul>
          {Object.entries(manifest?.dataset_sources || {}).map(
            ([name, src]) => (
              <li key={name}>
                <a href={src.url} target="_blank" rel="noreferrer">
                  {name} <ExternalLink size={12} />
                </a>
                {src.vintage ? ` · vintage ${src.vintage}` : ""}
                {src.period ? ` · ${src.period}` : ""}
              </li>
            ),
          )}
        </ul>
        <p>
          EPA AQS annual observations retain parameter, metric, units, sample
          completeness, event treatment, certification, and selected colocated
          POC provenance. The release selects one ambient summary per POC:
          Events Included when present, otherwise No Events; event-excluded
          alternatives are not substituted. EPA NEI rows are facility-level
          primary-PM2.5 annual inventory estimates in source units. Inventory
          proximity does not identify contribution or responsibility.
        </p>
        <ul>
          <li>
            2025 monitor summaries are provisional and subject to final EPA certification.
          </li>
          <li>
            Population and facility proximity are not used as direct pollution predictors.
          </li>
          <li>
            Values represent historical annual estimates, not real-time conditions or personal exposure.
          </li>
        </ul>
        <div className="method-commands">
          <code>
            python scripts/build_national_dataset.py --start-year 2018
            --end-year 2025
          </code>
          <code>
            OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python
            scripts/evaluate_national_v2.py
          </code>
          <code>python scripts/evaluate_national_v3.py</code>
        </div>
      </div>
    </>
  );
}

