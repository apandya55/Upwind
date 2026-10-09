import { ExternalLink } from "lucide-react";
import type { ContextItem } from "../types";
import { fmt } from "../utils";

export default function ContextRecord({
  item,
  monitor = false,
}: {
  item: ContextItem;
  monitor?: boolean;
}) {
  return (
    <article className="evidence-context-record">
      <div>
        <strong>{monitor ? `AQS monitor ${item.id}` : item.id}</strong>
        <span>
          {monitor
            ? `Measured annual PM2.5 · ${item.year}`
            : `${item.pollutant_code || "PM2.5"} · ${item.category || "EPA inventory record"} · ${item.inventory_year}`}
        </span>
        <small>
          {fmt(item.distance_km, 1)} km from selected point ·{" "}
          {monitor
            ? "instrument-site distance"
            : "reported facility-coordinate distance"}
        </small>
      </div>
      <b>
        {monitor
          ? `${fmt(item.value_ug_m3, 2)} µg/m³`
          : `${fmt(item.emissions, 2)} ${item.units || ""}`}
      </b>
      {item.source_url && (
        <a
          href={item.source_url}
          target="_blank"
          rel="noreferrer"
          aria-label={`Open provenance for ${item.id}`}
        >
          <ExternalLink size={14} />
        </a>
      )}
    </article>
  );
}

