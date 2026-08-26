import { useEffect, useMemo, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
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
import { RouteSiblingNavigation } from "../../components/RouteSiblingNavigation";
import { RouteTimeline } from "../../components/RouteTimeline";
import { ShareCard } from "../../components/ShareCard";
import { SpeedControl } from "../../components/SpeedControl";
import { StartTimeControl } from "../../components/StartTimeControl";
import { StatsGrid } from "../../components/StatsGrid";
import { StaleDataNotice } from "../../components/StaleDataNotice";
import type { PeriodId, RouteForecast } from "../../types";

function toClock(minutes: number) {
  const hour = Math.floor(minutes / 60) % 24;
  const minute = minutes % 60;
  return `${String(hour).padStart(2, "0")}:${String(minute).padStart(2, "0")}`;
}

export function RoutePage() {
  const { slug = "touchal-darband" } = useParams();
  const [params, setParams] = useSearchParams();
  const [data, setData] = useState<RouteForecast | null>(null);
  const [status, setStatus] = useState<"loading" | "ready" | "error" | "missing">("loading");
  const date = params.get("date") ?? undefined;
  const period = (params.get("period") as PeriodId) || "morning";
  const speed = params.get("speed") || undefined;
  const start = params.get("start_time") || undefined;

  function update(next: Record<string, string | undefined>) {
    const copy = new URLSearchParams(params);
    for (const [key, value] of Object.entries(next)) {
      if (value) copy.set(key, value);
    }
    setParams(copy, { replace: true });
  }

  function load() {
    setStatus("loading");
    api
      .routeForecast(slug, { date, period, speed, start_time: start })
      .then((payload) => {
        setData(payload);
        if (!date) {
          const today = payload.days.find((day) => day.is_today)?.date;
          if (today) update({ date: today, period, speed: payload.speed, start_time: toClock(payload.start_minutes) });
        }
        setStatus("ready");
      })
      .catch((error) => setStatus(error instanceof ApiError && error.status === 404 ? "missing" : "error"));
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [slug, date, period, speed, start]);

  const ticks = useMemo(
    () => (period === "afternoon" ? ["۱۲:۰۰", "۱۴:۰۰", "۱۶:۰۰", "۱۸:۰۰", "۲۰:۰۰", "۲۲:۰۰"] : ["۰۰:۰۰", "۰۲:۰۰", "۰۴:۰۰", "۰۶:۰۰", "۰۸:۰۰", "۱۰:۰۰"]),
    [period],
  );

  if (status === "missing") {
    return (
      <main className="route-page">
        <Header />
        <EmptyState title="مسیر پیدا نشد" detail="از صفحهٔ مقصد، مسیر دیگری را انتخاب کن." />
      </main>
    );
  }

  const selected = date ?? data?.days.find((day) => day.is_today)?.date ?? "";
  const startMinutes = data?.start_minutes ?? 360;
  const periodRange = period === "afternoon" ? { min: 720, max: 1440, label: "۱۲ تا ۲۴" } : { min: 0, max: 720, label: "۰۰ تا ۱۲" };

  return (
    <main className="route-page">
      <div className="route-shell">
        <Header />
        {status === "error" ? <ErrorState onRetry={load} /> : null}
        {status === "loading" && !data ? <LoadingState /> : null}
        {data ? (
          <>
            {data.meta.freshness === "stale" ? <StaleDataNotice generatedAt={data.meta.generated_at} /> : null}
            <section className="route-hero">
              <BackNavigation to={data.route.parent.href} ariaLabel="بازگشت به صفحهٔ مقصد" />
              <div className="route-hero-copy">
                <Breadcrumbs
                  items={[
                    { label: "مقصدها", to: "/#search-results" },
                    { label: data.route.parent.name, to: data.route.parent.href },
                    { label: data.route.title },
                  ]}
                />
                <h1>{data.route.title}</h1>
              </div>
              <div className="hero-status-stack route-hero-status-stack" aria-label="خلاصهٔ وضعیت مسیر">
                <div className="status-pill change">{data.hero.status}</div>
              </div>
            </section>
            <RouteSiblingNavigation parentName={data.route.parent.name} routes={data.route.siblings} />
            <div className="route-overview-grid">
              <div className="route-overview-main">
                <section className="route-planner card-surface" id="planner">
                  <div className="planner-heading">
                    <span className="decision-chip">انتخاب روز</span>
                  </div>
                  <div className="planner-day">
                    <DaySelector
                      className="route-day-tabs"
                      days={data.days}
                      selected={selected}
                      onSelect={(next) => update({ date: next })}
                    />
                  </div>
                </section>
                <section className="route-weather-card card-surface" id="route-weather" aria-label="نقاط مهم و وضعیت مسیر در طول روز">
                  <div className="route-weather-heading">
                    <div>
                      <span className="decision-chip">نقاط مهم</span>
                    </div>
                    <div className="route-hourly-selector" aria-label="انتخاب بازهٔ زمانی پیش‌بینی">
                      <PeriodToggle value={period} onChange={(next) => update({ period: next, start_time: next === "afternoon" ? "12:00" : "06:00" })} />
                    </div>
                  </div>
                  <RouteTimeline
                    origin={data.route.origin}
                    destination={data.route.destination_label}
                    title={data.route.title}
                    points={data.points}
                  />
                  <div className="route-hourly-values">
                    <HourlyForecast
                      hours={data.hourly}
                      headline={period === "morning" ? "تغییرات نیمهٔ اول روز · هر دو ساعت" : "تغییرات نیمهٔ دوم روز · هر دو ساعت"}
                    />
                  </div>
                  <div className="route-point-weather-values" aria-label="آب‌وهوای متناظر با نقاط مهم مسیر">
                    <div className="route-point-weather-grid">
                      {data.points.map((point) => (
                        <Link
                          key={`${point.slug}-weather`}
                          className={`route-point-weather-card ${point.state}`}
                          to={point.href}
                          onClick={(event) => event.preventDefault()}
                          aria-label={`آب‌وهوای ${point.name} در زمان ${point.time}`}
                        >
                          <strong>{point.time}</strong>
                          <span className="route-point-weather-icon">{point.icon}</span>
                          <span className="route-point-weather-condition">{point.condition}</span>
                          <b>{point.temp != null ? `${point.temp}°` : "—"}</b>
                          <small>باد {point.wind ?? "—"}</small>
                          {point.state !== "normal" ? <em>{point.state === "critical" ? "احتیاط" : "تغییر"}</em> : null}
                        </Link>
                      ))}
                    </div>
                  </div>
                </section>
                <StatsGrid items={data.stats} />
              </div>
              <aside className="route-overview-side">
                <div className="planner-quick-box" aria-label="تنظیم سریع حرکت">
                  <div className="mobile-planner-selectors" aria-label="انتخاب سرعت حرکت">
                    <div className="mobile-planner-selector">
                      <span className="planner-label">سرعت حرکت</span>
                      <div className="segmented-control">
                        {data.speed_options.map((option) => (
                          <button
                            key={`mobile-${option}`}
                            className={data.speed === option ? "selected" : ""}
                            type="button"
                            onClick={() => update({ speed: option })}
                          >
                            {option}
                          </button>
                        ))}
                      </div>
                    </div>
                  </div>
                  <StartTimeControl
                    minutes={startMinutes}
                    min={periodRange.min}
                    max={periodRange.max}
                    ticks={ticks}
                    rangeLabel={periodRange.label}
                    display={data.start_time}
                    onChange={(value) => update({ start_time: toClock(value) })}
                  />
                  <SpeedControl value={data.speed} options={data.speed_options} onChange={(value) => update({ speed: value })} />
                </div>
                <ShareCard forecast={data} />
              </aside>
            </div>
            <footer className="site-footer">
              <span>هوای مقصد، برنامهٔ مسیر</span>
            </footer>
          </>
        ) : null}
      </div>
    </main>
  );
}
