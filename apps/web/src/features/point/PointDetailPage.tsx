import { useEffect, useRef, useState } from "react";
import { useLocation, useParams, useSearchParams } from "react-router-dom";
import { api, ApiError } from "../../api/client";
import { Breadcrumbs } from "../../components/Breadcrumbs";
import { DaySelector } from "../../components/DaySelector";
import { DestinationCard } from "../../components/DestinationCard";
import { EmptyState } from "../../components/EmptyState";
import { ErrorState } from "../../components/ErrorState";
import { Header } from "../../components/Header";
import { HourlyForecast } from "../../components/HourlyForecast";
import { LoadingState } from "../../components/LoadingState";
import { PeriodToggle } from "../../components/PeriodToggle";
import { StaleDataNotice } from "../../components/StaleDataNotice";
import { asPeriodId, buildForecastParams, PERIOD_RANGES } from "../../lib/periods";
import type { PeriodId, PointForecast, RouteFromState } from "../../types";
import { PointRouteBackLink } from "./PointNavigation";

type PointLocationState = {
  fromRoute?: RouteFromState;
};

export function PointDetailPage() {
  const { slug = "" } = useParams();
  const location = useLocation();
  const fromRoute = (location.state as PointLocationState | null)?.fromRoute;
  const [searchParams, setSearchParams] = useSearchParams();
  const [date, setDate] = useState<string | undefined>(() => searchParams.get("date") || undefined);
  const [period, setPeriod] = useState<PeriodId | undefined>(() => asPeriodId(searchParams.get("period")));
  const [data, setData] = useState<PointForecast | null>(null);
  const [status, setStatus] = useState<"loading" | "ready" | "error" | "missing">("loading");
  const requestId = useRef(0);
  const resolvedDefaultRequestKey = useRef<string | null>(null);
  const explicitDate = Boolean(searchParams.get("date"));
  const explicitPeriod = Boolean(searchParams.get("period"));
  const displayPeriod = period ?? (data?.meta.selected_period as PeriodId | undefined) ?? "morning";

  function requestKey(nextDate = date, nextPeriod = period) {
    return JSON.stringify([slug, nextDate ?? "", nextPeriod ?? ""]);
  }

  function writeQuery(next: Record<string, string | undefined>) {
    const copy = new URLSearchParams(searchParams);
    for (const [key, value] of Object.entries(next)) {
      if (value) copy.set(key, value);
      else copy.delete(key);
    }
    setSearchParams(copy, { replace: true });
  }

  function selectDate(next: string) {
    setDate(next);
    const nextPeriod = period ?? (data?.meta.selected_period as PeriodId | undefined);
    writeQuery({ date: next, period: nextPeriod });
  }

  function selectPeriod(next: PeriodId) {
    setPeriod(next);
    const nextDate = date ?? data?.meta.selected_date;
    writeQuery({ date: nextDate, period: next });
  }

  function load() {
    const currentRequest = ++requestId.current;
    setStatus("loading");
    api
      .pointForecast(
        slug,
        buildForecastParams({
          date,
          period,
          includeDate: explicitDate,
          includePeriod: explicitPeriod,
        }),
      )
      .then((payload) => {
        if (currentRequest !== requestId.current) return;
        setData(payload);
        if (!date || !period) {
          const resolvedDate = date ?? payload.meta.selected_date;
          const resolvedPeriod = period ?? (payload.meta.selected_period as PeriodId);
          resolvedDefaultRequestKey.current = requestKey(resolvedDate, resolvedPeriod);
          if (!date) setDate(resolvedDate);
          if (!period) setPeriod(resolvedPeriod);
        }
        setStatus("ready");
      })
      .catch((error) => {
        if (currentRequest !== requestId.current) return;
        setStatus(error instanceof ApiError && error.status === 404 ? "missing" : "error");
      });
  }

  useEffect(() => {
    if (resolvedDefaultRequestKey.current === requestKey()) {
      resolvedDefaultRequestKey.current = null;
      return;
    }
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [slug, date, period]);

  if (status === "missing") {
    return (
      <main className="point-page">
        <div className="point-shell">
          <Header />
          <EmptyState title="نقطهٔ هواشناسی پیدا نشد" detail="از جست‌وجوی خانه نام دیگری را امتحان کن." />
        </div>
      </main>
    );
  }

  const selected = date ?? data?.meta.selected_date ?? "";
  const layoutClass = fromRoute ? "point-layout point-layout--single" : "point-layout";

  return (
    <main className="point-page">
      <div className="point-shell">
        <Header />
        {status === "error" ? <ErrorState onRetry={load} /> : null}
        {status === "loading" && !data ? <LoadingState /> : null}
        {data ? (
          <>
            {data.meta.freshness === "stale" ? <StaleDataNotice generatedAt={data.meta.generated_at} /> : null}
            <section className="point-hero card-surface">
              {fromRoute ? <PointRouteBackLink fromRoute={fromRoute} /> : null}
              <Breadcrumbs items={[{ label: "مقصدها", to: "/#search-results" }, { label: data.point.name }]} />
              <h1>{data.point.name}</h1>
              <p className="muted">
                {data.point.elevation_label}
                {data.point.latitude != null && data.point.longitude != null
                  ? `　·　${data.point.latitude.toFixed(4)}، ${data.point.longitude.toFixed(4)}`
                  : ""}
                {data.point.destination ? `　·　${data.point.destination.region}` : ""}
              </p>
              <div className="hero-status-stack point-hero-status-stack" aria-label="خلاصهٔ وضعیت نقطه">
                <div className="status-pill now">{data.hero.status}</div>
              </div>
            </section>
            <div className={layoutClass}>
              <div className="point-main">
                <section className="point-weather-card card-surface">
                  <div className="section-title-row">
                    <div>
                      <h2>پیش‌بینی {data.point.name}</h2>
                      <p className="muted">روز و بازه را تغییر بده تا وضعیت این نقطه را قبل از حرکت ببینی.</p>
                    </div>
                    <span className="updated">{data.updated_label}</span>
                  </div>
                  <DaySelector days={data.days} selected={selected} onSelect={selectDate} />
                  <div className="destination-period-row">
                    <span className="planner-label">بازهٔ نمایش هوا</span>
                    <PeriodToggle value={displayPeriod} onChange={selectPeriod} />
                  </div>
                  {data.empty || data.partial ? (
                    <EmptyState
                      title={data.partial ? "پیش‌بینی ناقص" : "پیش‌بینی در دسترس نیست"}
                      detail="برای این روز و بازه داده‌ای در پایگاه داده ثبت نشده است."
                    />
                  ) : (
                    <>
                      {data.weather ? (
                        <div className="point-current-reading">
                          <span className="weather-symbol">{data.weather.icon}</span>
                          <strong>{data.weather.temperature_label}</strong>
                          <span>{data.weather.condition}</span>
                          <small>{data.weather.wind_label}</small>
                        </div>
                      ) : null}
                      <HourlyForecast hours={data.hourly} headline={data.period.headline} />
                    </>
                  )}
                </section>
              </div>
              {!fromRoute && data.related_routes.length ? (
                <aside className="point-side">
                  <section className="point-routes-card card-surface" aria-label="مسیرهای مرتبط">
                    <div className="section-title-row">
                      <h2>مسیرهای مرتبط</h2>
                    </div>
                    <div className="route-cards">
                      {data.related_routes.map((route) => (
                        <DestinationCard key={route.slug} route={route} />
                      ))}
                    </div>
                  </section>
                </aside>
              ) : null}
            </div>
            <footer className="site-footer">
              <span>هوای مقصد، برنامهٔ مسیر · بازهٔ {PERIOD_RANGES[displayPeriod].label}</span>
            </footer>
          </>
        ) : null}
      </div>
    </main>
  );
}
