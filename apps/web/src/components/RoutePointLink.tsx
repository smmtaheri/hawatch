import { Link } from "react-router-dom";
import { buildRoutePointLink } from "../lib/routeNavigation";
import type { RouteFromState } from "../types";

export function RoutePointLink({
  pointHref,
  fromRoute,
  className,
  ariaLabel,
  children,
}: {
  pointHref: string;
  fromRoute?: RouteFromState;
  className?: string;
  ariaLabel: string;
  children: React.ReactNode;
}) {
  const target = buildRoutePointLink(pointHref, fromRoute);
  return (
    <Link to={target.pathname} state={target.state} className={className} aria-label={ariaLabel}>
      {children}
    </Link>
  );
}
