import { useEffect, useMemo, type CSSProperties } from "react";
import {
  useLocation,
  useNavigate,
  useParams,
  useSearchParams,
} from "react-router-dom";
import { ForecastDayPeriodControls } from "../../components/DaySelector";
import { ErrorState } from "../../components/ErrorState";
import { LoadingState } from "../../components/LoadingState";
import { PageShell } from "../../components/PageShell";
import { ShareCard } from "../../components/ShareCard";
import { RouteChooser } from "../../components/RelatedRoutes";
import { RoutePointLink } from "../../components/RoutePointLink";
import { DesignIcon, WeatherIcon } from "../../components/DesignIcon";
import { numberLabel } from "../../components/HourlyForecast";
import { StaleDataNotice } from "../../components/StaleDataNotice";
import { openAccountLogin } from "../../components/Header";
import { NotFoundPage } from "../../pages/NotFoundPage";
import {
  asPeriodId,
  formatClockDisplay,
  parseClockToMinutes,
  resolvePlannerBounds,
  toClock,
} from "../../lib/periods";
import {
  classifyAllPeriods,
  resolveRouteStartMinutes,
} from "../../lib/periodState";
import { usePageTitle } from "../../lib/pageTitle";
import { buildRouteBackState } from "../../lib/routeNavigation";
import { scrollToDetailHero } from "../../lib/detailEntryScroll";
import { useDayBundle } from "../../lib/useDayBundle";
import type {
  DayInfo,
  PeriodId,
  RouteDayBundle,
  RouteForecast,
} from "../../types";

const WEATHER_HAZARD_CODES = new Set([
  "drizzle",
  "freezing-drizzle",
  "rain",
  "freezing-rain",
  "snow",
  "shower",
  "thunder",
]);

export function RoutePage() {
  const { slug = "" } = useParams();
  const location = useLocation();
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const {
    data: bundle,
    context,
    status,
    reload,
  } = useDayBundle<RouteDayBundle>("route", slug);
  const frame = bundle ?? context;
  const period =
    asPeriodId(params.get("period")) ??
    asPeriodId(frame?.meta.selected_period) ??
    "morning";
  const selected = params.get("date") ?? frame?.meta.selected_date ?? "";
  const apiPeriod = frame?.periods[period];
  const bounds = resolvePlannerBounds(period, apiPeriod);
  const speedRaw = params.get("speed") ?? frame?.speed ?? "متوسط";
  const speed =
    ({ slow: "آرام", medium: "متوسط", fast: "سریع" } as Record<string, string>)[
      speedRaw
    ] ?? speedRaw;
  const displaySpeed = frame?.speed_options.includes(speed) ? speed : "متوسط";
  const minutes = params.get("start_time")
    ? parseClockToMinutes(params.get("start_time")!, period, apiPeriod)
    : resolveRouteStartMinutes(
        selected,
        period,
        frame?.meta.current_local_time,
        undefined,
        apiPeriod,
      );
  const forecast = useMemo<RouteForecast | null>(() => {
    if (!bundle) return null;
    const plan = bundle.plans[`${displaySpeed}:${minutes}`];
    if (!plan) return null;
    return {
      ...bundle,
      ...plan,
      points: bundle.points.map((point, i) => ({
        ...point,
        ...plan.points[i],
      })),
      period: bundle.periods[period],
      start_minutes: minutes,
      start_time: formatClockDisplay(minutes),
      speed: displaySpeed,
      meta: {
        ...bundle.meta,
        selected_date: selected,
        selected_period: period,
        selected_start_time: toClock(minutes),
        selected_speed: displaySpeed,
      },
    };
  }, [bundle, displaySpeed, minutes, period, selected]);
  // Keep the previous frame visible while a sibling route loads, but never
  // publish that frame's SEO metadata for the new URL.
  const seoRoute = frame?.route.slug === slug ? frame.route : undefined;
  usePageTitle(seoRoute?.title, {
    title: seoRoute?.seo_title,
    description: seoRoute?.seo_description,
    robots: status === "missing" ? "noindex,follow" : undefined,
    canonical: status === "missing" ? false : undefined,
  });
  useEffect(() => {
    if (!bundle?.route.slug) return;
    const frame = window.requestAnimationFrame(() => {
      scrollToDetailHero(".route-page .route-hero");
    });
    return () => window.cancelAnimationFrame(frame);
  }, [bundle?.route.slug]);

  function update(next: Record<string, string>) {
    const copy = new URLSearchParams(params);
    for (const [key, value] of Object.entries(next)) copy.set(key, value);
    setParams(copy, { replace: true });
  }
  function changePeriod(next: PeriodId) {
    const minute = resolveRouteStartMinutes(
      selected,
      next,
      frame?.meta.current_local_time,
      undefined,
      frame?.periods[next],
    );
    update({ date: selected, period: next, start_time: toClock(minute) });
  }
  function changeDate(date: string) {
    const minute = resolveRouteStartMinutes(
      date,
      period,
      frame?.meta.current_local_time,
      undefined,
      apiPeriod,
    );
    update({ date, period, start_time: toClock(minute) });
  }
  function access(day: DayInfo) {
    if (day.access === "plan_required") {
      navigate("/account/plans");
      return;
    }
    const copy = new URLSearchParams(params);
    copy.set("date", day.date);
    copy.set("period", period);
    openAccountLogin(`${location.pathname}?${copy}`);
  }
  if (status === "missing")
    return (
      <NotFoundPage
        title="مسیر پیدا نشد"
        detail="از صفحهٔ مقصد، مسیر دیگری را انتخاب کن."
      />
    );
  const fromRoute = forecast
    ? buildRouteBackState(forecast.route, params)
    : undefined;
  return (
    <PageShell className="route-page" back>
      {status === "error" ? <ErrorState onRetry={reload} /> : null}
      {status === "loading" && !frame ? <LoadingState /> : null}
      {frame ? (
        <>
          {frame.meta.freshness === "stale" ? <StaleDataNotice /> : null}
          <section className="hero route-hero">
            <div className="hero-title">
              <h1>{frame.route.title}</h1>
            </div>
            <div className="route-hero-meta">
              <RouteChooser routes={frame.route.siblings} carryPlan />
              <p className="route-stats">
                <span>
                  <bdi>
                    {frame.route.distance_label.replace(/km/g, "کیلومتر")}
                  </bdi>
                </span>
                <span className="route-stats-separator"> · </span>
                <span>
                  <bdi>{frame.route.ascent_label.replace(/ m/g, " متر")}</bdi>{" "}
                  صعود
                </span>
              </p>
            </div>
          </section>
          <div className="route-grid">
            <section className="route-main">
              <div className="route-selectors">
                <ForecastDayPeriodControls
                  days={frame.days}
                  selectedDate={selected}
                  onSelectDate={changeDate}
                  period={period}
                  onSelectPeriod={changePeriod}
                  periodStates={classifyAllPeriods(
                    selected,
                    frame.meta.current_local_time,
                  )}
                  onLockedDate={access}
                />
              </div>
              <section className="departure" aria-label="تنظیم حرکت">
                <div className="departure-controls">
                  <div className="range-control">
                    <label htmlFor="departure-time">ساعت شروع</label>
                    <div className="time-slider">
                      <input
                        id="departure-time"
                        type="range"
                        min={bounds.min}
                        max={bounds.lastStart}
                        step={bounds.stepMinutes}
                        value={minutes}
                        aria-valuetext={formatClockDisplay(minutes)}
                        style={
                          {
                            "--time-progress": `${((minutes - bounds.min) / Math.max(1, bounds.lastStart - bounds.min)) * 100}%`,
                          } as CSSProperties
                        }
                        onChange={(e) =>
                          update({
                            date: selected,
                            period,
                            start_time: toClock(Number(e.target.value)),
                          })
                        }
                      />
                      <output htmlFor="departure-time" dir="ltr">
                        {formatClockDisplay(minutes)}
                      </output>
                    </div>
                  </div>
                  <div className="speed-control">
                    <span className="control-label" id="speed-label">
                      سرعت حرکت
                    </span>
                    <div
                      className="speed"
                      role="group"
                      aria-labelledby="speed-label"
                    >
                      {frame.speed_options.map((option) => (
                        <button
                          key={option}
                          type="button"
                          aria-pressed={displaySpeed === option}
                          onClick={() =>
                            update({
                              date: selected,
                              period,
                              speed: option,
                              start_time: toClock(minutes),
                            })
                          }
                        >
                          {option}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
              </section>
              <section className="points">
                <div className="points-head">
                  <h2>نقاط مهم مسیر</h2>
                </div>
                <div
                  className="point-cards"
                  tabIndex={0}
                  aria-label="پیش‌بینی نقاط مسیر؛ برای دیدن ادامه، افقی حرکت کنید"
                >
                  {forecast ? (
                    forecast.points.map((point) => (
                      <RoutePointLink
                        key={point.slug}
                        pointHref={point.href}
                        ariaLabel={`${point.name} · ${point.time}`}
                        fromRoute={fromRoute}
                        className={`point-card route-point-weather-card ${point.state === "critical" ? "severe" : ""}`}
                      >
                        <strong className="point-name">{point.name}</strong>
                        <time dateTime={point.arrival_at ?? undefined}>
                          <bdi dir="ltr">{point.time}</bdi>
                          {point.arrival_minutes != null &&
                          point.arrival_minutes >= 1440
                            ? ` · ${Math.floor(point.arrival_minutes / 1440).toLocaleString("fa-IR")} روز بعد`
                            : null}
                        </time>
                        <WeatherIcon
                          code={point.weather_code}
                          at={point.forecast_at}
                          isDay={point.is_day}
                        />
                        <div
                          className={`weather-label ${point.state === "critical" && WEATHER_HAZARD_CODES.has(String(point.weather_code ?? "")) ? "risk-red" : ""}`}
                        >
                          {point.condition}
                        </div>
                        <div className="degree">
                          <bdi>{numberLabel(point.temp, "°")}</bdi>
                        </div>
                        <div className="wind-line">
                          باد <bdi>{numberLabel(point.wind, " km/h")}</bdi>
                          <DesignIcon name="wind" />
                        </div>
                      </RoutePointLink>
                    ))
                  ) : (
                    <LoadingState label="در حال دریافت هوای نقاط روز جدید…" />
                  )}
                </div>
              </section>
            </section>
            {forecast ? (
              <ShareCard forecast={forecast} />
            ) : (
              <aside className="trip-summary">
                <h2>خلاصهٔ مسیر</h2>
                <LoadingState />
              </aside>
            )}
          </div>
        </>
      ) : null}
    </PageShell>
  );
}
