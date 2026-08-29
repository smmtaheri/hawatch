import type { PeriodId, RouteFromState } from "../types";
import { asPeriodId } from "./periods";

export type RoutePointLinkTarget = {
  pathname: string;
  state?: { fromRoute: RouteFromState };
};

export function buildRouteBackState(
  route: { slug: string; title: string; href: string },
  params: URLSearchParams,
): RouteFromState {
  const search = params.toString();
  return {
    slug: route.slug,
    title: route.title,
    pathname: route.href,
    search: search ? `?${search}` : "",
    href: search ? `${route.href}?${search}` : route.href,
  };
}

export function buildLegacyRouteBackState(
  routeSlug: string,
  routeTitle: string,
  routeHref: string,
  params: URLSearchParams,
): RouteFromState {
  const backParams = new URLSearchParams();
  for (const key of ["date", "period", "start_time", "speed"]) {
    const value = params.get(key);
    if (value) backParams.set(key, value);
  }
  return buildRouteBackState({ slug: routeSlug, title: routeTitle, href: routeHref }, backParams);
}

export function buildRoutePointLink(pointHref: string, fromRoute: RouteFromState | undefined): RoutePointLinkTarget {
  return {
    pathname: pointHref,
    ...(fromRoute ? { state: { fromRoute } } : {}),
  };
}

export function routeBackTarget(fromRoute: RouteFromState) {
  const pathname = fromRoute.pathname || fromRoute.href.split("?")[0];
  const search = fromRoute.search?.startsWith("?") ? fromRoute.search.slice(1) : fromRoute.search ?? "";
  return { pathname, search };
}

/** Date/period from route planner search; excludes route-only params like start_time/speed. */
export function plannerDatePeriodFromRouteSearch(search: string): { date?: string; period?: PeriodId } {
  const params = new URLSearchParams(search.startsWith("?") ? search.slice(1) : search);
  return {
    date: params.get("date") || undefined,
    period: asPeriodId(params.get("period")),
  };
}

/** Date/period from public place URL only — never seed from fromRoute (back CTA only). */
export function initialDestinationPlanner(
  urlParams: URLSearchParams,
  _fromRoute?: RouteFromState,
): { date?: string; period?: PeriodId } {
  return {
    date: urlParams.get("date") || undefined,
    period: asPeriodId(urlParams.get("period")),
  };
}
