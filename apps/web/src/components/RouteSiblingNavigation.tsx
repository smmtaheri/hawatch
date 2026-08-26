import { Link } from "react-router-dom";
import type { RouteSummary } from "../types";

export function RouteSiblingNavigation({
  parentName,
  routes,
}: {
  parentName: string;
  routes: RouteSummary[];
}) {
  if (!routes.length) return null;
  return (
    <nav className="route-sibling-nav card-surface" aria-label={`مسیرهای دیگر ${parentName}`}>
      <div className="route-sibling-heading">
        <span className="decision-chip">مسیرهای دیگر</span>
        <small>{parentName}</small>
      </div>
      <div className="route-sibling-links">
        {routes.map((route) => (
          <Link key={route.slug} className="route-sibling-link" to={route.href} aria-label={`مشاهدهٔ مسیر ${route.title}`}>
            <strong>{route.title}</strong>
            <small>{route.distance_label}</small>
            <span aria-hidden="true">←</span>
          </Link>
        ))}
      </div>
    </nav>
  );
}
