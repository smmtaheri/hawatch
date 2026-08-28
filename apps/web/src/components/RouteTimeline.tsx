import { Link } from "react-router-dom";
import type { RoutePointView } from "../types";

export function RouteTimeline({
  origin,
  destination,
  title,
  points,
  pointHref,
}: {
  origin: string;
  destination: string;
  title: string;
  points: RoutePointView[];
  pointHref?: (point: RoutePointView) => string;
}) {
  return (
    <div className="route-linear-panel">
      <div className="route-linear-scroll">
        <div className="route-linear-endpoints" aria-hidden="true">
          <span>مبدا · {origin}</span>
          <span>مقصد · {destination}</span>
        </div>
        <div className="route-linear-track" aria-label={`نقاط مسیر ${title}`}>
          {points.map((point) => (
            <Link
              key={point.slug}
              className={`route-linear-point ${point.state}`}
              to={pointHref ? pointHref(point) : point.href}
              aria-label={`مشاهدهٔ جزئیات ${point.name}، ${point.time}`}
            >
              <span className="route-linear-node">
                <span className="marker-weather">{point.icon}</span>
              </span>
              <span className="route-linear-point-name">{point.name}</span>
              <span className="route-linear-reading">
                <b>{point.temp != null ? `${point.temp}°` : "—"}</b>
                <small>{point.time}</small>
              </span>
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}
