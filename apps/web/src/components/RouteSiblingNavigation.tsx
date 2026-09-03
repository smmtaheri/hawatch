import { useEffect, useRef } from "react";
import { Link, useLocation } from "react-router-dom";
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
  const detailsRef = useRef<HTMLDetailsElement>(null);
  const location = useLocation();

  useEffect(() => {
    if (detailsRef.current) detailsRef.current.open = false;
  }, [location.pathname, location.search]);

  if (!routes.length) return null;
  return (
    <nav className="route-sibling-nav" aria-label={`مسیرهای دیگر ${parentName}`}>
      <details ref={detailsRef} className="route-sibling-details">
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
              <Link
                key={route.slug}
                className="route-sibling-link"
                to={route.href}
                aria-label={`مشاهدهٔ مسیر ${route.title}`}
                onClick={() => {
                  if (detailsRef.current) detailsRef.current.open = false;
                }}
              >
                <strong>{route.title}</strong>
                <small><bdi>{route.distance_label}</bdi></small>
                <span aria-hidden="true">›</span>
              </Link>
            ))}
          </div>
        </div>
      </details>
    </nav>
  );
}
