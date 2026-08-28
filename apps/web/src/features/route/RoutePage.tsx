import { useEffect, useMemo, useRef, useState } from "react";
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
import { appendRouteContext, formatClockDisplay, PERIOD_RANGES, periodTicks, toClock } from "../../lib/periods";
import type { PeriodId, RouteForecast } from "../../types";

export function RoutePage() {
  const { slug = "touchal-darband" } = useParams();
  const [params, setParams] = useSearchParams();
  const [data, setData] = useState<RouteForecast | null>(null);
  const [status, setStatus] = useState<"loading" | "ready" | "error" | "missing">("loading");
  const [draftMinutes, setDraftMinutes] = useState<number | null>(null);
  const requestId = useRef(0);
  const commitTimer = useRef<number | null>(null);
  const plannerReady = useRef(false);
  const explicitDate = params.has("date");
  const explicitPeriod = params.has("period");
  const date = params.get("date") ?? undefined;
  const period = ((params.get("period") as PeriodId) || "morning") as PeriodId;
  const speed = params.get("speed") || undefined;
  const start = params.get("start_time") || undefined;

  function update(next: Record<string, string | undefined>) {
    const copy = new URLSearchParams(params);
    for (const [key, value] of Object.entries(next)) {
      if (value) copy.set(key, value);
      else copy.delete(key);
    }
    setParams(copy, { replace: true });
  }

  function load(options?: { skipIfTimingPending?: boolean }) {
    if (options?.skipIfTimingPending && data?.timing_pending) {
      return;
    }
    const currentRequest = ++requestId.current;
    setStatus("loading");
    api
      .routeForecast(slug, { date, period, speed, start_time: start })
      .then((payload) => {
        if (currentRequest !== requestId.current) return;
        setData(payload);
        setDraftMinutes(payload.start_minutes);
        if (!explicitDate || !explicitPeriod) {
          const today = payload.days.find((day) => day.is_today)?.date ?? payload.meta.selected_date;
          update({
            date: explicitDate ? date : today,
            period: explicitPeriod ? period : (payload.meta.selected_period as PeriodId),
            speed: payload.speed,
            start_time: toClock(payload.start_minutes),
          });
        }
        setStatus("ready");
        plannerReady.current = true;
      })
      .catch((error) => {
        if (currentRequest !== requestId.current) return;
        setStatus(error instanceof ApiError && error.status === 404 ? "missing" : "error");
      });
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [slug, date, period]);

  useEffect(() => {
    if (!plannerReady.current) return;
    load({ skipIfTimingPending: true });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [speed, start]);

  const ticks = useMemo(() => periodTicks(period), [period]);
  const periodRange = PERIOD_RANGES[period];
  const pointHref = (href: string) => appendRouteContext(href, params);

  function commitStartMinutes(minutes: number) {
    setDraftMinutes(minutes);
    if (data?.timing_pending) {
      update({ start_time: toClock(minutes) });
      return;
    }
    if (commitTimer.current) window.clearTimeout(commitTimer.current);
    commitTimer.current = window.setTimeout(() => {
      update({ start_time: toClock(minutes) });
    }, 300);
  }

  function handlePeriodChange(next: PeriodId) {
    update({ period: next, start_time: PERIOD_RANGES[next].defaultStart });
  }

  if (status === "missing") {
    return (
      <main className="route-page">
        <Header />
        <EmptyState title="مسیر پیدا نشد" detail="از صفحهٔ مقصد، مسیر دیگری را انتخاب کن." />
      </main>
    );
  }

  const selected = date ?? data?.days.find((day) => day.is_today)?.date ?? "";
  const startMinutes = draftMinutes ?? data?.start_minutes ?? periodRange.min;
  const startDisplay = formatClockDisplay(startMinutes);

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
                      <PeriodToggle value={period} onChange={handlePeriodChange} />
                    </div>
                  </div>
                  <RouteTimeline
                    origin={data.route.origin}
                    destination={data.route.destination_label}
                    title={data.route.title}
                    points={data.points}
                    pointHref={(point) => pointHref(point.href)}
                  />
                  <div className="route-hourly-values">
                    <HourlyForecast hours={data.hourly} headline={data.period.headline ?? data.period.range_label} />
                  </div>
                  <div className="route-point-weather-values" aria-label="آب‌وهوای متناظر با نقاط مهم مسیر">
                    <div className="route-point-weather-grid">
                      {data.points.map((point) => (
                        <Link
                          key={`${point.slug}-weather`}
                          className={`route-point-weather-card ${point.state}`}
                          to={pointHref(point.href)}
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
                    display={startDisplay}
                    onChange={setDraftMinutes}
                    onCommit={commitStartMinutes}
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
