import { Link } from "react-router-dom";
import { routeBackTarget } from "../../lib/routeNavigation";
import type { RouteFromState } from "../../types";

/** Shared route-back CTA for Forecast Place (destination or point). */
export function RouteBackLink({ fromRoute }: { fromRoute: RouteFromState }) {
  const { pathname, search } = routeBackTarget(fromRoute);
  return (
    <Link
      className="contextual-route-back card-surface"
      to={{ pathname, search }}
      aria-label={`بازگشت به مسیر ${fromRoute.title}`}
    >
      بازگشت به مسیر {fromRoute.title}
    </Link>
  );
}
