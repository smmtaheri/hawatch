import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import type { RouteSummary, SimilarDestinationSummary } from "../types";
import { appendRouteContext } from "../lib/periods";
import { CategoryIcon, DesignIcon } from "./DesignIcon";
import { Dialog } from "./Dialog";
export function RouteChooser({
  routes,
  label = "تغییر مسیر",
  title = "انتخاب مسیر",
  carryPlan = false,
}: {
  routes: RouteSummary[];
  label?: string;
  title?: string;
  carryPlan?: boolean;
}) {
  const [open, setOpen] = useState(false);
  const [params] = useSearchParams();
  if (!routes.length) return null;
  return (
    <>
      <button
        className={label === "تغییر مسیر" ? "change-route" : "all-routes"}
        type="button"
        aria-haspopup="dialog"
        aria-expanded={open}
        onClick={() => setOpen(true)}
      >
        {label}
        {label === "تغییر مسیر" ? <DesignIcon name="refresh" /> : null}
      </button>
      {open ? (
        <Dialog title={title} onClose={() => setOpen(false)}>
          {routes.map((route) => (
            <Link
              className="catalog-row dialog-route"
              key={route.slug}
              to={
                carryPlan ? appendRouteContext(route.href, params) : route.href
              }
              onClick={() => setOpen(false)}
            >
              <DesignIcon name="category-route" className="category-icon" />
              <span>
                <strong>{route.title}</strong>
                <small>
                  <bdi>{route.distance_label.replace(/km/g, "کیلومتر")}</bdi> ·{" "}
                  <bdi>{route.ascent_label.replace(/ m/g, " متر")}</bdi> صعود
                </small>
              </span>
              <DesignIcon name="chevron-left" />
            </Link>
          ))}
        </Dialog>
      ) : null}
    </>
  );
}
export function RelatedRoutes({
  routes,
  title,
}: {
  routes: RouteSummary[];
  title: string;
}) {
  if (!routes.length) return null;
  return (
    <aside className="routes">
      <h2>{title}</h2>
      {routes.slice(0, 3).map((route) => (
        <Link className="route-row" key={route.slug} to={route.href}>
          <span className="route-icon">
            <DesignIcon name="hike" />
          </span>
          <span className="route-copy">
            {route.title}
            <small>
              <bdi>{route.distance_label.replace(/km/g, "کیلومتر")}</bdi> ·{" "}
              <bdi>{route.ascent_label.replace(/ m/g, " متر")}</bdi> صعود
            </small>
          </span>
          <DesignIcon name="chevron-left" />
        </Link>
      ))}
      <RouteChooser routes={routes} title={title} label="همهٔ مسیرها" />
    </aside>
  );
}

export function RelatedDestinations({
  destinations,
  title,
}: {
  destinations: SimilarDestinationSummary[];
  title: string;
}) {
  const [open, setOpen] = useState(false);
  const card = (item: SimilarDestinationSummary) => (
    <Link
      className="route-row"
      key={item.slug}
      to={item.href}
      onClick={() => setOpen(false)}
    >
      <CategoryIcon category={item.category_key} placeType={item.place_type} />
      <span className="route-copy">
        {item.name}
        <small>
          {item.region} · {item.elevation_label}
        </small>
      </span>
      <DesignIcon name="chevron-left" />
    </Link>
  );
  return (
    <aside className="routes">
      <h2>{title}</h2>
      {destinations.slice(0, 3).map(card)}
      {destinations.length > 3 ? (
        <>
          <button
            type="button"
            className="all-routes"
            onClick={() => setOpen(true)}
          >
            همهٔ مقصدها
          </button>
          {open ? (
            <Dialog title={title} onClose={() => setOpen(false)}>
              {destinations.map(card)}
            </Dialog>
          ) : null}
        </>
      ) : null}
    </aside>
  );
}
