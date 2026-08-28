import { useEffect, useMemo, useRef, useState } from "react";
import { useParams, useSearchParams } from "react-router-dom";
import { api, ApiError } from "../../api/client";
import { BackNavigation } from "../../components/BackNavigation";
import { Breadcrumbs } from "../../components/Breadcrumbs";
import { DayPickerHeading, DaySelector, PeriodControlRow } from "../../components/DaySelector";
import { EmptyState } from "../../components/EmptyState";
import { ErrorState } from "../../components/ErrorState";
import { Header } from "../../components/Header";
import { LoadingState } from "../../components/LoadingState";
import { RouteSiblingNavigation } from "../../components/RouteSiblingNavigation";
import { RouteTimeline } from "../../components/RouteTimeline";
import { RoutePointLink } from "../../components/RoutePointLink";
import { ShareCard } from "../../components/ShareCard";
import { SpeedControl } from "../../components/SpeedControl";
import { StartTimeControl } from "../../components/StartTimeControl";
import { StatsGrid } from "../../components/StatsGrid";
import { StaleDataNotice } from "../../components/StaleDataNotice";
import {
  asPeriodId,
  buildForecastParams,
  formatClockDisplay,
  isValidStartTimeInput,
  PERIOD_RANGES,
  periodTicks,
  toClock,
} from "../../lib/periods";
import { classifyAllPeriods, gaugeCurrentMinutes, resolveRouteStartMinutes } from "../../lib/periodState";
import { buildRouteBackState, buildRoutePointLink } from "../../lib/routeNavigation";
import type { PeriodId, RouteForecast, RoutePointView } from "../../types";

type RouteRequestInputs = {
  slug: string;
  date?: string;
  period?: PeriodId;
  speed?: string;
  start?: string;
};

function requestKey({ slug, date, period, speed, start }: RouteRequestInputs) {
  return JSON.stringify([slug, date ?? "", period ?? "", speed ?? "", start ?? ""]);
}

function isPlannerOnlyChange(previous: RouteRequestInputs, next: RouteRequestInputs) {
  return (
    previous.slug === next.slug &&
    previous.date === next.date &&
    previous.period === next.period &&
    (previous.speed !== next.speed || previous.start !== next.start)
  );
}

function pointWeatherLabel(point: RoutePointView, periodLabel: string, timingPending: boolean) {
  if (timingPending) return `وضعیت ${periodLabel}`;
  if (point.time && point.time !== "—") return `حوالی ${point.time}`;
  return periodLabel;
}

export function RoutePage() {
  const { slug = "touchal-darband" } = useParams();
  const [params, setParams] = useSearchParams();
  const [data, setData] = useState<RouteForecast | null>(null);
  const [status, setStatus] = useState<"loading" | "ready" | "error" | "missing">("loading");
  const [draftMinutes, setDraftMinutes] = useState<number | null>(null);
  const [draftSpeed, setDraftSpeed] = useState<string | null>(null);
  const requestId = useRef(0);
  const commitTimer = useRef<number | null>(null);
  const timingPendingRef = useRef(false);
  const previousRequestInputs = useRef<RouteRequestInputs | null>(null);
  const resolvedUrlRequestKey = useRef<string | null>(null);
  const requestedDate = params.get("date") || undefined;
  const explicitDate = Boolean(requestedDate);
  const requestedPeriod = asPeriodId(params.get("period"));
  const explicitPeriod = Boolean(requestedPeriod);
  const speed = params.get("speed") || undefined;
  const start = params.get("start_time") || undefined;
  const displayPeriod = requestedPeriod ?? (data?.meta.selected_period as PeriodId | undefined) ?? "morning";
  const displaySpeed = draftSpeed ?? speed ?? data?.speed ?? "متوسط";
  const timingPending = Boolean(data?.timing_pending);

  function update(next: Record<string, string | undefined>) {
    const copy = new URLSearchParams(params);
    for (const [key, value] of Object.entries(next)) {
      if (value) copy.set(key, value);
      else copy.delete(key);
    }
    setParams(copy, { replace: true });
  }

  function load(omitInvalidStart = false) {
    const currentRequest = ++requestId.current;
    setStatus("loading");
    const effectiveStart = omitInvalidStart ? undefined : start;
    api
      .routeForecast(
        slug,
        buildForecastParams({
          date: requestedDate,
          period: requestedPeriod ?? undefined,
          start_time: effectiveStart,
          speed,
          includeDate: explicitDate,
          includePeriod: explicitPeriod,
        }),
      )
      .then((payload) => {
        if (currentRequest !== requestId.current) return;
        setData(payload);
        timingPendingRef.current = Boolean(payload.timing_pending);
        const resolvedPeriod = (requestedPeriod ?? payload.meta.selected_period) as PeriodId;
        const resolvedDate = explicitDate ? requestedDate! : payload.meta.selected_date;
        setDraftMinutes(payload.start_minutes);
        setDraftSpeed(payload.speed);
        const canonicalClock = toClock(payload.start_minutes);
        const needsUrlSync =
          !explicitDate ||
          !explicitPeriod ||
          !effectiveStart ||
          effectiveStart !== canonicalClock ||
          omitInvalidStart;
        if (needsUrlSync) {
          const resolvedParams = {
            date: resolvedDate,
            period: explicitPeriod ? requestedPeriod ?? undefined : resolvedPeriod,
            speed: payload.speed,
            start_time: canonicalClock,
          };
          resolvedUrlRequestKey.current = requestKey({
            slug,
            date: resolvedParams.date,
            period: resolvedParams.period,
            speed: resolvedParams.speed,
            start: resolvedParams.start_time,
          });
          update(resolvedParams);
        }
        setStatus("ready");
      })
      .catch((error) => {
        if (currentRequest !== requestId.current) return;
        if (error instanceof ApiError && error.status === 400 && start && !omitInvalidStart) {
          update({ start_time: undefined });
          return;
        }
        setStatus(error instanceof ApiError && error.status === 404 ? "missing" : "error");
      });
  }

  useEffect(() => {
    const nextInputs = {
      slug,
      date: requestedDate,
      period: requestedPeriod ?? undefined,
      speed,
      start,
    };
    const nextKey = requestKey(nextInputs);
    const previousInputs = previousRequestInputs.current;
    previousRequestInputs.current = nextInputs;

    if (resolvedUrlRequestKey.current === nextKey) {
      resolvedUrlRequestKey.current = null;
      return;
    }
    if (previousInputs && isPlannerOnlyChange(previousInputs, nextInputs) && timingPendingRef.current) {
      return;
    }
    if (start && !isValidStartTimeInput(start)) {
      update({ start_time: undefined });
      return;
    }
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [slug, requestedDate, requestedPeriod, speed, start]);

  useEffect(
    () => () => {
      if (commitTimer.current) window.clearTimeout(commitTimer.current);
    },
    [],
  );

  const ticks = useMemo(() => periodTicks(displayPeriod), [displayPeriod]);
  const periodRange = PERIOD_RANGES[displayPeriod];
  const fromRoute = data ? buildRouteBackState(data.route, params) : undefined;

  function pointLink(point: RoutePointView) {
    return buildRoutePointLink(point.href, fromRoute);
  }

  function scheduleCommit(minutes: number) {
    if (commitTimer.current) window.clearTimeout(commitTimer.current);
    commitTimer.current = window.setTimeout(() => {
      update({ start_time: toClock(minutes) });
    }, 300);
  }

  function handleDraftChange(minutes: number) {
    setDraftMinutes(minutes);
    scheduleCommit(minutes);
  }

  function commitStartMinutes(minutes: number) {
    if (commitTimer.current) window.clearTimeout(commitTimer.current);
    setDraftMinutes(minutes);
    update({ start_time: toClock(minutes) });
  }

  function handlePeriodChange(next: PeriodId) {
    if (commitTimer.current) window.clearTimeout(commitTimer.current);
    const selected = requestedDate ?? data?.meta.selected_date ?? "";
    const canonical = resolveRouteStartMinutes(selected, next, data?.meta.current_local_time);
    setDraftMinutes(canonical);
    update({ period: next, start_time: toClock(canonical) });
  }

  function handleDateChange(next: string) {
    if (commitTimer.current) window.clearTimeout(commitTimer.current);
    const canonical = resolveRouteStartMinutes(next, displayPeriod, data?.meta.current_local_time);
    setDraftMinutes(canonical);
    update({ date: next, start_time: toClock(canonical) });
  }

  function handleSpeedChange(nextSpeed: string) {
    setDraftSpeed(nextSpeed);
    update({ speed: nextSpeed });
  }

  if (status === "missing") {
    return (
      <main className="route-page">
        <Header />
        <EmptyState title="مسیر پیدا نشد" detail="از صفحهٔ مقصد، مسیر دیگری را انتخاب کن." />
      </main>
    );
  }

  const selected = requestedDate ?? data?.meta.selected_date ?? "";
  const startMinutes = draftMinutes ?? data?.start_minutes ?? periodRange.defaultStartMinutes;
  const startDisplay = formatClockDisplay(startMinutes);
  const periodStates =
    data?.meta.current_local_time && selected
      ? classifyAllPeriods(selected, data.meta.current_local_time)
      : undefined;
  const gaugeNow = data?.meta.current_local_time
    ? gaugeCurrentMinutes(selected, displayPeriod, data.meta.current_local_time)
    : undefined;

  return (
    <main className="route-page">
      <div className="route-shell">
        <Header />
        {status === "error" ? <ErrorState onRetry={load} /> : null}
        {status === "loading" && !data ? <LoadingState /> : null}
        {data ? (
          <>
            {data.meta.freshness === "stale" ? <StaleDataNotice /> : null}
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
                  <DayPickerHeading />
                  <div className="planner-day">
                    <DaySelector
                      className="route-day-tabs"
                      days={data.days}
                      selected={selected}
                      onSelect={handleDateChange}
                    />
                  </div>
                </section>
                <section className="route-weather-card card-surface" id="route-weather" aria-label="نقاط مهم و وضعیت مسیر در طول روز">
                  <div className="route-weather-heading">
                    <div>
                      <span className="decision-chip">نقاط مهم</span>
                    </div>
                    <div className="route-hourly-selector" aria-label="انتخاب بازهٔ زمانی پیش‌بینی">
                      <PeriodControlRow
                        period={displayPeriod}
                        onChange={handlePeriodChange}
                        periodStates={periodStates}
                        className="destination-period-row route-period-row"
                      />
                    </div>
                  </div>
                  <RouteTimeline
                    origin={data.route.origin}
                    destination={data.route.destination_label}
                    title={data.route.title}
                    points={data.points}
                    pointHref={(point) => pointLink(point)}
                  />
                  <div className="route-point-weather-values" aria-label="آب‌وهوای متناظر با نقاط مهم مسیر">
                    <div className="route-point-weather-grid">
                      {data.points.map((point) => {
                        const unavailable = point.weather_available === false;
                        const label = pointWeatherLabel(point, data.period.label, timingPending);
                        return (
                          <RoutePointLink
                            key={`${point.slug}-weather`}
                            pointHref={point.href}
                            fromRoute={fromRoute}
                            className={`route-point-weather-card ${point.state} ${unavailable ? "weather-unavailable" : ""}`}
                            ariaLabel={`آب‌وهوای ${point.name} · ${label}`}
                          >
                            <strong>{label}</strong>
                            <span className="route-point-weather-icon">{point.icon}</span>
                            <span className="route-point-weather-condition">
                              {unavailable ? "در دسترس نیست" : point.condition}
                            </span>
                            <b>{point.temp != null ? `${point.temp}°` : "—"}</b>
                            <small>باد {point.wind ?? "—"}</small>
                            {point.state !== "normal" ? <em>{point.state === "critical" ? "احتیاط" : "تغییر"}</em> : null}
                          </RoutePointLink>
                        );
                      })}
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
                            className={displaySpeed === option ? "selected" : ""}
                            type="button"
                            onClick={() => handleSpeedChange(option)}
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
                    period={displayPeriod}
                    ticks={ticks}
                    rangeLabel={periodRange.label}
                    display={startDisplay}
                    currentMinutes={gaugeNow}
                    onChange={handleDraftChange}
                    onCommit={commitStartMinutes}
                  />
                  <SpeedControl value={displaySpeed} options={data.speed_options} onChange={handleSpeedChange} />
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
