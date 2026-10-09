import { Download, ExternalLink } from "lucide-react";
import type { ContextResponse, NationalPlace } from "../types";
import { contextRadiusLabel, fmt } from "../utils";
import ContextRecord from "./ContextRecord";

export default function InvestigationPanel({
  place,
  year,
  data,
  onExport,
}: {
  place: NationalPlace;
  year: number;
  data: ContextResponse | null;
  onExport: () => void;
}) {
  const estimate = place.model_estimates?.[String(year)];
  const roads = data?.road_context;
  return (
    <section
      className="detail-section location-investigation"
      aria-label={`Local pollution investigation for ${place.name}`}
    >
      <div className="section-title-line">
        <div>
          <h3>Local pollution investigation</h3>
          <span>
            {place.name}, {place.state} · evidence around the Census point
          </span>
        </div>
        <button className="soft-button" onClick={onExport}>
          <Download size={14} /> Export JSON
        </button>
      </div>
      <div className="investigation-evidence-row">
        <b>Modeled estimate · {year}</b>
        <strong>
          {estimate
            ? `${fmt(estimate.value_ug_m3, 2)} µg/m³`
            : "No supported estimate"}
        </strong>
        <small>
          {estimate
            ? `Spatial OOF 90% band ${fmt(estimate.interval90_low_ug_m3, 2)}–${fmt(estimate.interval90_high_ug_m3, 2)} µg/m³`
            : place.withheld_reason ||
              "No estimate is published for this year."}
        </small>
      </div>
      <div className="context-group">
        <h4>Measured monitoring</h4>
        {data?.nearest_monitors.length ? (
          data.nearest_monitors
            .slice(0, 3)
            .map((item, i) => (
              <ContextRecord
                key={`investigation-monitor-${item.id}-${i}`}
                item={item}
                monitor
              />
            ))
        ) : (
          <p className="muted-note">
            No eligible EPA AQS annual summary within {contextRadiusLabel(data)}{" "}
            km for {year}.
          </p>
        )}
      </div>
      <div className="context-group">
        <h4>EPA NEI inventory records</h4>
        {data?.closest_facilities.length ? (
          data.closest_facilities
            .slice(0, 4)
            .map((item, i) => (
              <ContextRecord
                key={`investigation-facility-${item.id}-${i}`}
                item={item}
              />
            ))
        ) : (
          <p className="muted-note">
            No matching EPA NEI PM2.5 inventory rows were found within the
            selected search radius.
          </p>
        )}
        <p className="muted-note">
          Facility values describe annual inventory emissions, not ambient
          concentrations.
        </p>
      </div>
      <div className="context-group">
        <h4>Major road network</h4>
        {roads?.available ? (
          <>
            <p>
              {roads.nearest_major_road
                ? `${roads.nearest_major_road.name} (${roads.nearest_major_road.road_class}) is ${fmt(roads.nearest_major_road.distance_km, 2)} km from the point.`
                : `No mapped major road was found within ${roads.radius_km} km.`}
            </p>
            <p>
              {fmt(roads.major_road_length_km_within_radius, 2)} km of mapped
              major-road length across{" "}
              {roads.major_road_corridor_count_within_radius} named corridors
              within {roads.radius_km} km (
              {fmt(roads.major_road_length_km_per_km2, 2)} km/km²). This is
              road-network context only.
            </p>
            <ul>
              {(roads.nearby_major_roads || []).slice(0, 4).map((road) => (
                <li key={road.osm_way_id}>
                  {road.name} · {road.road_class} · {fmt(road.distance_km, 2)}{" "}
                  km
                </li>
              ))}
            </ul>
            <a
              className="external-link"
              href={roads.provenance?.source_url}
              target="_blank"
              rel="noreferrer"
            >
              {roads.provenance?.dataset || "Road network"} ·{" "}
              {roads.provenance?.license} <ExternalLink size={13} />
            </a>
            <small className="muted-note">
              {roads.provenance?.attribution} · extract{" "}
              {roads.provenance?.extract_timestamp || "timestamp not supplied"}.{" "}
              {roads.coverage}
            </small>
          </>
        ) : (
          <p className="muted-note">
            {roads?.reason ||
              "Road coverage is not available for this location."}
          </p>
        )}
      </div>
      <div className="investigation-limits">
        <strong>Limits</strong>
        <p>
          These records show nearby measurements, an annual place-point
          estimate, inventory rows, and mapped road geography. They do not
          identify which source contributed to measured or estimated PM2.5. EPA
          ECHO/FRS records are not integrated in this release. No local
          meteorological observation is linked to this investigation.
        </p>
      </div>
    </section>
  );
}

