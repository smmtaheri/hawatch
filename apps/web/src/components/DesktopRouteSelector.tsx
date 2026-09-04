import { useEffect, useState } from "react";
import { useLocation } from "react-router-dom";
import type { RouteSummary } from "../types";
import { PointCard } from "./PointCard";

const MAX_VISIBLE_DESKTOP_ROUTES = 4;

/**
 * Desktop route discovery keeps the first four routes in the page flow and
 * puts the rest behind an explicit menu. The API order is intentional: it is
 * the database's point/route sort order and therefore the operator's
 * display ranking.
 */
export function DesktopRouteSelector({
  routes,
  title,
}: {
  routes: RouteSummary[];
  title: string;
}) {
  const [isOpen, setIsOpen] = useState(false);
  const location = useLocation();
  const visibleRoutes = routes.slice(0, MAX_VISIBLE_DESKTOP_ROUTES);
  const additionalRoutes = routes.slice(MAX_VISIBLE_DESKTOP_ROUTES);

  useEffect(() => {
    setIsOpen(false);
  }, [location.pathname, location.search]);

  useEffect(() => {
    if (!isOpen) return;

    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") setIsOpen(false);
    }

    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [isOpen]);

  if (!routes.length) return null;

  return (
    <section
      className={`desktop-route-selection top-routes-card compact-route-box card-surface ${routes.length === 1 ? "single-route" : ""}`}
      id="routes"
      aria-label={title}
    >
      <div className="compact-route-heading">
        <div>
          <span className="eyebrow teal-text">تصمیم بعدی</span>
          <h2>{title}</h2>
        </div>
      </div>

      <div className="route-cards desktop-route-cards">
        {visibleRoutes.map((route) => (
          <PointCard key={route.slug} route={route} />
        ))}
      </div>

      {additionalRoutes.length ? (
        <div className="desktop-route-overflow">
          <button
            className="desktop-route-overflow-trigger"
            type="button"
            aria-haspopup="menu"
            aria-expanded={isOpen}
            onClick={() => setIsOpen((open) => !open)}
          >
            دیدن باقی مسیرها
            <span aria-hidden="true">←</span>
          </button>
          {isOpen ? (
            <div className="desktop-route-overflow-panel" role="menu" aria-label="مسیرهای بیشتر">
              {additionalRoutes.map((route) => (
                <PointCard key={route.slug} route={route} role="menuitem" onNavigate={() => setIsOpen(false)} />
              ))}
            </div>
          ) : null}
        </div>
      ) : null}
    </section>
  );
}
