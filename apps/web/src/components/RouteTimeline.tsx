import { Link } from "react-router-dom";
import { buildRoutePointLink, type RoutePointLinkTarget } from "../lib/routeNavigation";
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
  pointHref?: (point: RoutePointView) => RoutePointLinkTarget;
}) {
  return (
    <div className="route-linear-panel">
      <div className="route-linear-endpoints" aria-hidden="true">
        <span>مبدا · {origin}</span>
        <span>مقصد · {destination}</span>
      </div>
      <div className="route-linear-track" aria-label={`نقاط مسیر ${title}`}>
        {points.map((point, index) => {
          const target = pointHref ? pointHref(point) : buildRoutePointLink(point.href, undefined);
          return (
            <Link
              key={point.slug}
              className={`route-linear-point ${point.state}`}
              to={target.pathname}
              state={target.state}
              aria-label={`مشاهدهٔ جزئیات ${point.name}`}
            >
              <span className="route-linear-node">
                <span className="marker-weather">{point.icon}</span>
              </span>
              <span className="route-linear-point-name">{point.name}</span>
              <span className="route-linear-order"><bdi>{index + 1}</bdi></span>
            </Link>
          );
        })}
      </div>
    </div>
  );
}
