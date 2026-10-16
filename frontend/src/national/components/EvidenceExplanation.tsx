import type { NationalPlace } from "../types";
import { fmt } from "../utils";

export default function EvidenceExplanation({
  place,
  year,
}: {
  place: NationalPlace;
  year: number;
}) {
  const estimate = place.model_estimates?.[String(year)];
  const explanation = place.evidence_explanation;
  return (
    <section className="detail-section evidence-explanation">
      <div className="section-title-line">
        <h3>Why this estimate?</h3>
        <span>{explanation?.period || `Annual ${year}`}</span>
      </div>
      <p>
        {explanation?.why_this_appears ||
          (estimate
            ? `A released annual PM2.5 estimate is available for ${year}.`
            : `No model estimate is published for this place in ${year}.`)}
      </p>
      {estimate && (
        <dl>
          <div>
            <dt>Method</dt>
            <dd>{explanation?.method || "Nearest eligible EPA AQS monitor"}</dd>
          </div>
          <div>
            <dt>Supporting monitor</dt>
            <dd>
              AQS {estimate.reference_monitor_id || "ID unavailable"} ·{" "}
              {fmt(estimate.nearest_monitor_km, 1)} km away
              {estimate.reference_monitor_value_ug_m3 != null
                ? ` · ${fmt(estimate.reference_monitor_value_ug_m3, 2)} µg/m³`
                : ""}
            </dd>
          </div>
          <div>
            <dt>Location</dt>
            <dd>
              {explanation?.location_meaning ||
                "Census Gazetteer internal point; not a place average."}
            </dd>
          </div>
          <div>
            <dt>Uncertainty</dt>
            <dd>
              {explanation?.uncertainty_interpretation ||
                "Spatial out-of-fold monitor-site error band; not a local guarantee."}
            </dd>
          </div>
        </dl>
      )}
      {!estimate && (
        <p>
          {place.withheld_reason ||
            `The release has no supported estimate for ${year}.`}
        </p>
      )}
      <p className="evidence-limits">
        Note: Historical annual estimate. Does not reflect real-time air quality, personal exposure, or facility attribution.
      </p>
    </section>
  );
}

