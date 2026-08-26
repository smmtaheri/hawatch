import { Link } from "react-router-dom";
import type { RouteSummary } from "../types";

export function DestinationCard({ route }: { route: RouteSummary }) {
  return (
    <Link to={route.href} className={`route-card ${route.featured ? "recommended" : ""}`}>
      {route.featured ? <span className="recommend-label">پیشنهاد هواچ</span> : null}
      <span className="route-icon">⌁</span>
      <span className="route-copy">
        <h3>{route.title}</h3>
        <p>
          {route.trail_label} · {route.origin}
        </p>
        <small>
          {route.distance_label} · {route.ascent_label} صعود
        </small>
      </span>
      <span className="compact-route-arrow">←</span>
    </Link>
  );
}
