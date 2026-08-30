import { useEffect, useState } from "react";
import { Navigate, useParams, useSearchParams } from "react-router-dom";
import { api, ApiError } from "../../api/client";
import { LoadingState } from "../../components/LoadingState";
import { EmptyState } from "../../components/EmptyState";
import { Header } from "../../components/Header";
import { buildForecastParams } from "../../lib/periods";
import { buildLegacyRouteBackState } from "../../lib/routeNavigation";
import type { RouteFromState } from "../../types";

/** Resolve legacy route-scoped point URLs to the canonical Forecast Place URL. */
export function LegacyRoutePointRedirect() {
  const { routeSlug = "", pointSlug = "" } = useParams();
  const [params] = useSearchParams();
  const [target, setTarget] = useState<{ pathname: string; search: string; state: { fromRoute: RouteFromState } } | null>(
    null,
  );
  const [missing, setMissing] = useState(false);

  useEffect(() => {
    let cancelled = false;
    api
      .routePointForecast(
        routeSlug,
        pointSlug,
        buildForecastParams({
          date: params.get("date") || undefined,
          period: params.get("period") || undefined,
          includeDate: Boolean(params.get("date")),
          includePeriod: Boolean(params.get("period")),
        }),
      )
      .then((payload) => {
        if (cancelled) return;
        const slug = payload.weather_point_slug;
        const canonical = payload.canonical_href ?? (slug ? `/points/${slug}` : null);
        if (!canonical) {
          setMissing(true);
          return;
        }
        const nextParams = new URLSearchParams();
        const date = params.get("date");
        const period = params.get("period");
        if (date) nextParams.set("date", date);
        if (period) nextParams.set("period", period);
        setTarget({
          pathname: canonical.split("?")[0],
          search: nextParams.toString() ? `?${nextParams.toString()}` : "",
          state: {
            fromRoute: buildLegacyRouteBackState(
              routeSlug,
              payload.point.route_title,
              payload.point.route_href,
              params,
            ),
          },
        });
      })
      .catch((error) => {
        if (cancelled) return;
        setMissing(error instanceof ApiError && error.status === 404);
      });
    return () => {
      cancelled = true;
    };
  }, [routeSlug, pointSlug, params]);

  if (missing) {
    return (
      <main className="destination-page">
        <Header />
        <EmptyState title="نقطهٔ مسیر پیدا نشد" detail="به مسیر برگرد و نقطهٔ دیگری را انتخاب کن." />
      </main>
    );
  }

  if (target) {
    return <Navigate to={`${target.pathname}${target.search}`} replace state={target.state} />;
  }

  return (
    <main className="destination-page">
      <div className="destination-shell">
        <Header />
        <LoadingState />
      </div>
    </main>
  );
}
