import { useEffect, useRef, useState } from "react";
import { Link, Navigate, useParams, useSearchParams } from "react-router-dom";
import { api, ApiError } from "../../api/client";
import { LoadingState } from "../../components/LoadingState";
import { EmptyState } from "../../components/EmptyState";
import { Header } from "../../components/Header";
import { buildForecastParams } from "../../lib/periods";
import type { RouteFromState } from "../../types";

/** Resolve legacy route-scoped point URLs to the canonical /points/{slug} page. */
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
          search: nextParams.toString() ? `?${nextParams}` : "",
          state: {
            fromRoute: {
              slug: routeSlug,
              title: payload.point.route_title,
              href: payload.point.route_href,
            },
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
      <main className="point-page">
        <Header />
        <EmptyState title="نقطهٔ مسیر پیدا نشد" detail="به مسیر برگرد و نقطهٔ دیگری را انتخاب کن." />
      </main>
    );
  }

  if (target) {
    return <Navigate to={`${target.pathname}${target.search}`} replace state={target.state} />;
  }

  return (
    <main className="point-page">
      <div className="point-shell">
        <Header />
        <LoadingState />
      </div>
    </main>
  );
}

export function PointRouteBackLink({ fromRoute }: { fromRoute: RouteFromState }) {
  return (
    <Link className="point-route-back card-surface" to={fromRoute.href} aria-label={`بازگشت به مسیر ${fromRoute.title}`}>
      بازگشت به مسیر {fromRoute.title}
    </Link>
  );
}
