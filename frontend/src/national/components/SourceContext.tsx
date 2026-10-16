import type { ContextResponse } from "../types";
import ContextRecord from "./ContextRecord";

export default function SourceContext({
  data,
  loading,
  error,
  radius,
  onRadiusChange,
}: {
  data: ContextResponse | null;
  loading: boolean;
  error: string;
  radius: number;
  onRadiusChange: (radius: number) => void;
}) {
  return (
    <section className="detail-section source-context">
      <div className="section-title-line">
        <div>
          <h3>Nearby documented evidence</h3>
          <span>
            {data
              ? `${data.counts.measured_monitor_summaries} monitor summaries · ${data.counts.distinct_facilities} facilities`
              : "AQS + EPA inventory"}
          </span>
        </div>
        <label className="context-radius">
          <span>Radius</span>
          <select
            aria-label="Context search radius"
            value={radius}
            onChange={(event) => onRadiusChange(Number(event.target.value))}
          >
            <option value={25}>25 km</option>
            <option value={50}>50 km</option>
            <option value={100}>100 km</option>
            <option value={250}>250 km</option>
          </select>
        </label>
      </div>
      {loading && (
        <p className="muted-note" role="status">
          Updating evidence for the selected radius and year…
        </p>
      )}
      {error && (
        <p className="muted-note" role="status">
          {error}
        </p>
      )}
      {!loading && !error && data && (
        <>
          <div className="monitoring-gap" role="status">
            <strong>
              {data.monitoring_gap.monitor_summary_count
                ? `${data.monitoring_gap.monitor_summary_count} AQS annual site summaries in ${data.provenance.monitor_year}`
                : `No AQS annual site summary within ${radius} km for ${data.provenance.monitor_year}`}
            </strong>
            <span>{data.monitoring_gap.meaning}</span>
          </div>
          {data.nearest_monitors.length > 0 && (
            <div className="context-group">
              <h4>Closest monitor summaries</h4>
              {data.nearest_monitors.slice(0, 4).map((item, index) => (
                <ContextRecord
                  key={`m:${item.id}:${index}`}
                  item={item}
                  monitor
                />
              ))}
            </div>
          )}
          {data.closest_facilities.length > 0 && (
            <div className="context-group">
              <h4>Closest inventoried facilities</h4>
              {data.closest_facilities.slice(0, 4).map((item, index) => (
                <ContextRecord key={`c:${item.id}:${index}`} item={item} />
              ))}
            </div>
          )}
          {data.largest_compatible_inventory_groups.map((group) => (
            <div
              className="context-group"
              key={`${group.pollutant_code}:${group.units}`}
            >
              <h4>
                Largest compatible inventory rows{" "}
                <span>
                  {group.pollutant_code} · {group.units} ·{" "}
                  {group.compatible_record_count} rows
                </span>
              </h4>
              {group.records.slice(0, 4).map((item, index) => (
                <ContextRecord key={`l:${item.id}:${index}`} item={item} />
              ))}
            </div>
          ))}
          {!data.nearest_monitors.length && !data.closest_facilities.length && (
            <p className="muted-note">
              No qualifying summaries or inventory rows were found within{" "}
              {radius} km.
            </p>
          )}
          <p className="source-disclaimer">
            EPA AQS values are annual concentrations at reference stations.
            EPA NEI rows report total facility emissions. Facility proximity
            does not imply that a specific site contributed to local monitor
            readings.
          </p>
        </>
      )}
    </section>
  );
}

