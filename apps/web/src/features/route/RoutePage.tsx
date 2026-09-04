import { useEffect, useMemo, useRef, useState, type CSSProperties } from "react";
import { useParams, useSearchParams } from "react-router-dom";
import { api, ApiError } from "../../api/client";
import { BackNavigation } from "../../components/BackNavigation";
import { Breadcrumbs } from "../../components/Breadcrumbs";
import { DayPickerHeading, DaySelector, PeriodControlRow } from "../../components/DaySelector";
import { EmptyState } from "../../components/EmptyState";
import { ErrorState } from "../../components/ErrorState";
import { Header } from "../../components/Header";
import { LoadingState } from "../../components/LoadingState";
import { MobileRouteSelector } from "../../components/MobileRouteSelector";
import { RouteSiblingNavigation } from "../../components/RouteSiblingNavigation";
import { RouteTimeline } from "../../components/RouteTimeline";
import { RoutePointLink } from "../../components/RoutePointLink";
import { ShareCard } from "../../components/ShareCard";
import { SpeedControl } from "../../components/SpeedControl";
import { StartTimeControl } from "../../components/StartTimeControl";
import { StaleDataNotice } from "../../components/StaleDataNotice";
import {
  asPeriodId,
  buildForecastParams,
  formatClockDisplay,
  isValidStartTimeInput,
  resolvePlannerBounds,
  toClock,
} from "../../lib/periods";
import { classifyAllPeriods, gaugeCurrentMinutes, resolveRouteStartMinutes } from "../../lib/periodState";
import { usePageTitle } from "../../lib/pageTitle";
import { buildRouteBackState, buildRoutePointLink } from "../../lib/routeNavigation";
import { scrollToDetailHero } from "../../lib/detailEntryScroll";
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

function formatFaDigits(value: number | string) {
  return String(value).replace(/\d/g, (digit) => "۰۱۲۳۴۵۶۷۸۹"[Number(digit)]);
}

function pointWeatherLabel(point: RoutePointView, timingPending: boolean) {
  if (timingPending || point.timing_pending) return "زمان‌بندی در دسترس نیست";
  if (point.time && point.time !== "—") return `حدود ${point.time}`;
  return "پیش‌بینی رسیدن";
}

function timingEstimateBadgeLabel(point: RoutePointView) {
  const uncertainty = point.timing_uncertainty_minutes;
  if (uncertainty != null && uncertainty >= 0) {
    return `تخمینی · ±${formatFaDigits(uncertainty)} دقیقه`;
  }
  return "تخمینی";
}

export function RoutePage() {
  const { slug = "tochal-darband" } = useParams();
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
  usePageTitle(data?.route.title);

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

  // Only route identity triggers this. Planner changes must keep the visitor's
  // reading position intact while a fresh route opens at its identity hero.
  useEffect(() => {
    if (!data?.route.slug) return;
    const frame = window.requestAnimationFrame(() => {
      scrollToDetailHero(".route-page .route-hero");
    });
    return () => window.cancelAnimationFrame(frame);
  }, [data?.route.slug]);

  const plannerBounds = useMemo(
    () => resolvePlannerBounds(displayPeriod, data?.period ?? null),
    [displayPeriod, data?.period],
  );
  const ticks = plannerBounds.ticks;
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
    const canonical = resolveRouteStartMinutes(
      selected,
      next,
      data?.meta.current_local_time,
      undefined,
      data?.period?.id === next ? data.period : null,
    );
    setDraftMinutes(canonical);
    update({ period: next, start_time: toClock(canonical) });
  }

  function handleDateChange(next: string) {
    if (commitTimer.current) window.clearTimeout(commitTimer.current);
    const canonical = resolveRouteStartMinutes(
      next,
      displayPeriod,
      data?.meta.current_local_time,
      undefined,
      data?.period ?? null,
    );
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
        <div className="page-back-navigation">
          <BackNavigation />
        </div>
        <EmptyState title="مسیر پیدا نشد" detail="از صفحهٔ نقطه، مسیر دیگری را انتخاب کن." />
      </main>
    );
  }

  const selected = requestedDate ?? data?.meta.selected_date ?? "";
  const startMinutes = draftMinutes ?? data?.start_minutes ?? plannerBounds.defaultStartMinutes;
  const startDisplay = formatClockDisplay(startMinutes);
  const periodStates =
    data?.meta.current_local_time && selected
      ? classifyAllPeriods(selected, data.meta.current_local_time)
      : undefined;
  const gaugeNow =
    data?.meta.current_local_time && selected
      ? gaugeCurrentMinutes(selected, displayPeriod, data.meta.current_local_time, data.period)
      : undefined;

  return (
    <main className="route-page">
      <div className="route-shell">
        <Header />
        <div className="page-back-navigation">
          <BackNavigation />
        </div>
        {status === "error" ? <ErrorState onRetry={load} /> : null}
        {status === "loading" && !data ? <LoadingState /> : null}
        {data ? (
          <>
            {data.meta.freshness === "stale" ? <StaleDataNotice /> : null}
            <section className="route-hero">
              <div className="route-hero-copy">
                <Breadcrumbs
                  items={[
                    { label: "نقاط", to: "/#search-results" },
                    ...(data.route.target_point ? [{ label: data.route.target_point.name, to: data.route.target_point.href }] : []),
                    { label: data.route.title },
                  ]}
                />
                <h1>{data.route.title}</h1>
                <p className="route-hero-meta">
                  مسافت <bdi>{data.route.distance_label}</bdi>　·　صعود <bdi>{data.route.ascent_label}</bdi>
                </p>
              </div>
              <div className="hero-status-stack route-hero-status-stack" aria-label="خلاصهٔ وضعیت مسیر">
                <div className="status-pill change">{data.hero.status}</div>
              </div>
              <MobileRouteSelector
                routes={data.route.siblings}
                title={`مسیرهای دیگر ${data.route.target_point?.name ?? data.route.target_label}`}
                variant="trigger"
              />
              <RouteSiblingNavigation
                parentName={data.route.target_point?.name ?? data.route.target_label}
                currentRoute={{ title: data.route.title, href: data.route.href }}
                routes={data.route.siblings}
              />
            </section>
            <div className="route-overview-grid">
              <div className="route-overview-main">
                <section className="route-planner card-surface" id="planner">
                  <div className="route-planner-day-period">
                    <DayPickerHeading />
                    <PeriodControlRow
                      period={displayPeriod}
                      onChange={handlePeriodChange}
                      periodStates={periodStates}
                      className="point-period-row route-period-row"
                    />
                  </div>
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
                    <span className="decision-chip">نقاط مهم</span>
                  </div>
                  <div className="route-points-axis-scroll">
                    <div
                      className={`route-points-axis-content ${data.points.length > 6 ? "has-overflow" : ""}`}
                      style={{ "--route-point-count": data.points.length } as CSSProperties}
                    >
                      <RouteTimeline
                        origin={data.route.origin}
                        target={data.route.target_label}
                        title={data.route.title}
                        points={data.points}
                        pointHref={(point) => pointLink(point)}
                      />
                      <div className="route-point-weather-values" aria-label="آب‌وهوای متناظر با نقاط مهم مسیر">
                        <div className="route-point-weather-grid">
                          {data.points.map((point) => {
                            const weatherMissing = point.weather_available === false;
                            const unavailable = weatherMissing || point.timing_pending;
                            const label = pointWeatherLabel(point, timingPending);
                            return (
                              <RoutePointLink
                                key={`${point.slug}-weather`}
                                pointHref={point.href}
                                fromRoute={fromRoute}
                                className={`route-point-weather-card ${point.state} ${unavailable ? "weather-unavailable" : ""}`}
                                ariaLabel={`آب‌وهوای ${point.name} · ${label}`}
                              >
                                <strong>{point.name}</strong>
                                <span className="route-point-weather-eta"><bdi>{label}</bdi></span>
                                {point.timing_estimated && !timingPending ? (
                                  <span className="route-point-weather-badge">{timingEstimateBadgeLabel(point)}</span>
                                ) : null}
                                <span className="route-point-weather-icon">{weatherMissing || timingPending ? "—" : point.icon}</span>
                                <span className="route-point-weather-condition">
                                  {timingPending
                                    ? "زمان‌بندی در دسترس نیست"
                                    : weatherMissing
                                      ? point.condition || "در دسترس نیست"
                                      : point.condition}
                                </span>
                                <b><bdi>{!unavailable && point.temp != null ? `${point.temp}°` : "—"}</bdi></b>
                                <small>
                                  <bdi>{!unavailable && point.wind != null ? `باد ${point.wind} km/h` : "باد —"}</bdi>
                                </small>
                                {!unavailable && point.state !== "normal" ? (
                                  <em>{point.state === "critical" ? "احتیاط" : "تغییر"}</em>
                                ) : null}
                              </RoutePointLink>
                            );
                          })}
                        </div>
                      </div>
                    </div>
                  </div>
                </section>
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
                    min={plannerBounds.min}
                    max={plannerBounds.maxExclusive}
                    period={displayPeriod}
                    apiPeriod={data.period}
                    ticks={ticks}
                    rangeLabel={plannerBounds.label}
                    display={startDisplay}
                    currentMinutes={gaugeNow}
                    stepMinutes={plannerBounds.stepMinutes}
                    onChange={handleDraftChange}
                    onCommit={commitStartMinutes}
                  />
                  <SpeedControl value={displaySpeed} options={data.speed_options} onChange={handleSpeedChange} />
                </div>
                <ShareCard forecast={data} />
              </aside>
            </div>
            <footer className="site-footer">
              <span>هوای نقطه، برنامهٔ مسیر</span>
            </footer>
          </>
        ) : null}
      </div>
    </main>
  );
}
