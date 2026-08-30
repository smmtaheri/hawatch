import { Link } from "react-router-dom";
import type { RouteSummary } from "../types";

export function RouteSiblingNavigation({
  parentName,
  currentRoute,
  routes,
}: {
  parentName: string;
  currentRoute: Pick<RouteSummary, "title" | "href">;
  routes: RouteSummary[];
}) {
  if (!routes.length) return null;
  return (
    <nav className="route-sibling-nav" aria-label={`مسیرهای دیگر ${parentName}`}>
      <details className="route-sibling-details">
        <summary className="route-sibling-trigger">
          <span aria-hidden="true">⌁</span>
          <strong>تغییر مسیر</strong>
          <span className="route-sibling-trigger-chevron" aria-hidden="true">⌄</span>
        </summary>
        <div className="route-sibling-panel">
          <div className="route-sibling-panel-heading">مسیرهای قلهٔ {parentName}</div>
          <div className="route-sibling-links">
            <div className="route-sibling-link route-sibling-link-current" aria-current="page">
              <strong>{currentRoute.title}</strong>
              <small>مسیر فعلی</small>
              <span aria-hidden="true">✓</span>
            </div>
            {routes.map((route) => (
              <Link key={route.slug} className="route-sibling-link" to={route.href} aria-label={`مشاهدهٔ مسیر ${route.title}`}>
                <strong>{route.title}</strong>
                <small>{route.distance_label}</small>
                <span aria-hidden="true">›</span>
              </Link>
            ))}
          </div>
        </div>
      </details>
    </nav>
  );
}
