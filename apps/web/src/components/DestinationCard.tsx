import { Link } from "react-router-dom";
import type { RouteSummary } from "../types";

export function DestinationCard({ route }: { route: RouteSummary }) {
  return (
    <Link to={route.href} className="route-card">
      <span className="route-icon">⌁</span>
      <span className="route-copy">
        <h3>{route.title}</h3>
        <small className="route-details">
          <span className="route-detail">ارتفاع‌گیری: {route.ascent_label}</span>
          <span className="route-detail">مسافت: {route.distance_label}</span>
        </small>
      </span>
      <span className="compact-route-arrow">←</span>
    </Link>
  );
}
