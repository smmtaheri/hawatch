import { Link } from "react-router-dom";
import type { RoutePointView } from "../types";

export function RouteTimeline({
  origin,
  destination,
  title,
  points,
}: {
  origin: string;
  destination: string;
  title: string;
  points: RoutePointView[];
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
              to={point.href}
              aria-label={`مشاهدهٔ مقصد ${point.name}، ${point.time}`}
              onClick={(event) => event.preventDefault()}
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
