import { useEffect, useState } from "react";
import { useParams, useSearchParams } from "react-router-dom";
import { api, ApiError } from "../../api/client";
import { BackNavigation } from "../../components/BackNavigation";
import { Breadcrumbs } from "../../components/Breadcrumbs";
import { DaySelector } from "../../components/DaySelector";
import { EmptyState } from "../../components/EmptyState";
import { ErrorState } from "../../components/ErrorState";
import { Header } from "../../components/Header";
import { HourlyForecast } from "../../components/HourlyForecast";
import { LoadingState } from "../../components/LoadingState";
import { PeriodToggle } from "../../components/PeriodToggle";
import { StaleDataNotice } from "../../components/StaleDataNotice";
import { PERIOD_RANGES } from "../../lib/periods";
import type { PeriodId, RoutePointForecast } from "../../types";

export function PointDetailPage() {
  const { routeSlug = "", pointSlug = "" } = useParams();
  const [params, setParams] = useSearchParams();
  const [data, setData] = useState<RoutePointForecast | null>(null);
  const [status, setStatus] = useState<"loading" | "ready" | "error" | "missing">("loading");
  const date = params.get("date") ?? undefined;
  const period = (params.get("period") as PeriodId) || "morning";

  function update(next: Record<string, string | undefined>) {
    const copy = new URLSearchParams(params);
    for (const [key, value] of Object.entries(next)) {
      if (value) copy.set(key, value);
      else copy.delete(key);
    }
    setParams(copy, { replace: true });
  }

  function load() {
    setStatus("loading");
    api
      .routePointForecast(routeSlug, pointSlug, { date, period })
      .then((payload) => {
        setData(payload);
        if (!date) {
          update({ date: payload.meta.selected_date, period: payload.meta.selected_period as PeriodId });
        }
        setStatus("ready");
      })
      .catch((error) => setStatus(error instanceof ApiError && error.status === 404 ? "missing" : "error"));
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [routeSlug, pointSlug, date, period]);

  if (status === "missing") {
    return (
      <main className="point-page">
        <Header />
        <EmptyState title="نقطهٔ مسیر پیدا نشد" detail="به مسیر برگرد و نقطهٔ دیگری را انتخاب کن." />
      </main>
    );
  }

  const selected = date ?? data?.meta.selected_date ?? "";
  const backHref = data?.back_href ?? `/routes/${routeSlug}`;
  const routeParams = new URLSearchParams();
  for (const key of ["date", "period", "start_time", "speed"]) {
    const value = params.get(key);
    if (value) routeParams.set(key, value);
  }
  const backTo = routeParams.toString() ? `${backHref.split("?")[0]}?${routeParams}` : backHref;

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
              <BackNavigation to={backTo} ariaLabel="بازگشت به مسیر" />
              <Breadcrumbs
                items={[
                  { label: "مقصدها", to: "/#search-results" },
                  { label: data.point.destination.name, to: data.point.destination.href },
                  { label: data.point.route_title, to: data.point.route_href },
                  { label: data.point.name },
                ]}
              />
              <h1>{data.point.name}</h1>
              <p className="muted">
                {data.point.route_title}　·　{data.point.elevation_label}
                {data.point.latitude != null && data.point.longitude != null
                  ? `　·　${data.point.latitude.toFixed(4)}، ${data.point.longitude.toFixed(4)}`
                  : ""}
              </p>
            </section>
            <section className="point-weather-card card-surface">
              <div className="section-title-row">
                <div>
                  <h2>پیش‌بینی نقطه</h2>
                  <p className="muted">بازه و روز را تغییر بده تا وضعیت این نقطه در مسیر را ببینی.</p>
                </div>
              </div>
              <DaySelector days={data.days} selected={selected} onSelect={(next) => update({ date: next })} />
              <div className="destination-period-row">
                <span className="planner-label">بازهٔ نمایش هوا</span>
                <PeriodToggle
                  value={period}
                  onChange={(next) =>
                    update({ period: next, start_time: undefined, date: selected || undefined })
                  }
                />
              </div>
              {!data.point.has_weather_point ? (
                <EmptyState
                  title="نقطهٔ هواشناسی متصل نیست"
                  detail="این نقطه در مسیر ثبت شده اما دادهٔ هواشناسی مستقل برای آن وجود ندارد."
                />
              ) : data.empty || data.partial ? (
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
            <footer className="site-footer">
              <span>هوای مقصد، برنامهٔ مسیر · بازهٔ {PERIOD_RANGES[period].label}</span>
            </footer>
          </>
        ) : null}
      </div>
    </main>
  );
}
