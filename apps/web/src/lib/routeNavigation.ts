import type { RouteFromState } from "../types";

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

export function buildRoutePointLink(pointHref: string, fromRoute: RouteFromState | undefined) {
  return {
    pathname: pointHref,
    search: "",
    state: fromRoute ? { fromRoute } : undefined,
  };
}

export function routeBackTarget(fromRoute: RouteFromState) {
  const pathname = fromRoute.pathname || fromRoute.href.split("?")[0];
  const search = fromRoute.search?.startsWith("?") ? fromRoute.search.slice(1) : fromRoute.search ?? "";
  return { pathname, search };
}
