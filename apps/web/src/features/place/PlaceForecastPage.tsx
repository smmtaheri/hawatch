import { useEffect } from "react";
import { useLocation, useNavigate, useParams } from "react-router-dom";
import { ForecastDayPeriodControls } from "../../components/DaySelector";
import { EmptyState } from "../../components/EmptyState";
import { ErrorState } from "../../components/ErrorState";
import { HourlyForecast, numberLabel } from "../../components/HourlyForecast";
import { LoadingState } from "../../components/LoadingState";
import { NotFoundPage } from "../../pages/NotFoundPage";
import { PageShell } from "../../components/PageShell";
import {
  RelatedRoutes,
  RelatedDestinations,
} from "../../components/RelatedRoutes";
import { WeatherIcon } from "../../components/DesignIcon";
import { StaleDataNotice } from "../../components/StaleDataNotice";
import { openAccountLogin } from "../../components/Header";
import { usePageTitle } from "../../lib/pageTitle";
import { classifyAllPeriods } from "../../lib/periodState";
import { scrollToDetailHero } from "../../lib/detailEntryScroll";
import type { DayInfo } from "../../types";
import type { PlaceKind } from "./placeForecastAdapter";
import { usePlaceForecast } from "./usePlaceForecast";

function PlaceForecastPage({ kind }: { kind: PlaceKind }) {
  const { slug = "" } = useParams();
  const location = useLocation();
  const navigate = useNavigate();
  const {
    data: weather,
    frame: data,
    bundle,
    status,
    displayPeriod,
    selected,
    selectDate,
    selectPeriod,
    reload,
  } = usePlaceForecast({ kind, slug });
  // Keep the previous frame visible while a sibling point loads, but never
  // publish that frame's SEO metadata for the new URL.
  const seoSubject = data?.subject.slug === slug ? data.subject : undefined;
  usePageTitle(seoSubject?.name, {
    title: seoSubject?.seo_title,
    description: seoSubject?.seo_description,
    robots:
      status === "missing" || seoSubject?.seo_indexable === false
        ? "noindex,follow"
        : undefined,
    canonical: status === "missing" ? false : undefined,
  });
  useEffect(() => {
    if (!data?.subject.slug) return;
    const frame = window.requestAnimationFrame(() => {
      scrollToDetailHero(".point-page .point-hero");
    });
    return () => window.cancelAnimationFrame(frame);
  }, [data?.subject.slug]);

  function access(day: DayInfo) {
    if (day.access === "plan_required") {
      navigate("/account/plans");
      return;
    }
    const params = new URLSearchParams(location.search);
    params.set("date", day.date);
    params.set("period", displayPeriod);
    openAccountLogin(`${location.pathname}?${params}`);
  }
  if (status === "missing")
    return (
      <NotFoundPage
        title="نقطه پیدا نشد"
        detail="از جست‌وجوی خانه نام دیگری را امتحان کن."
      />
    );
  const dayLabel = data?.days.find((d) => d.date === selected)?.label ?? "";
  const summary = bundle?.daily_summary;
  return (
    <PageShell className="point-page" back>
      {status === "error" ? <ErrorState onRetry={reload} /> : null}
      {status === "loading" && !data ? <LoadingState /> : null}
      {data ? (
        <>
          {data.meta.freshness === "stale" ? <StaleDataNotice /> : null}
          <section
            className={`hero point-hero ${data.subject.name.length > 14 ? "long-title" : ""}`}
          >
            <div className="hero-title">
              <h1>{data.subject.seo_h1 || `آب‌وهوای ${data.subject.name}`}</h1>
              <p>
                {data.subject.elevation_label
                  ? `ارتفاع ${data.subject.elevation_label}`
                  : data.subject.region}
              </p>
            </div>
            <div className="summary">
              {summary ? (
                <>
                  <div className="summary-weather">
                    <WeatherIcon
                      code={summary.weather_code}
                      at={summary.forecast_at}
                      className=""
                    />
                    <div className="temperature-stat">
                      <span>بیشینه</span>
                      <strong>
                        <bdi>{numberLabel(summary.apparent_max_c, "°")}</bdi>
                      </strong>
                    </div>
                    <div className="temperature-stat">
                      <span>کمینه</span>
                      <strong>
                        <bdi>{numberLabel(summary.apparent_min_c, "°")}</bdi>
                      </strong>
                    </div>
                  </div>
                  <p className="day-summary-line">
                    <span className="day-summary-label">{dayLabel} · </span>
                    <span>{summary.condition}</span>
                    {summary.warnings?.map((warning, index) => (
                      <span key={`${warning.code}:${warning.start_at}:${index}`} className={warning.severity === "critical" ? "risk-red" : "risk-yellow"}>
                        {" · "}{warning.label}{" "}
                        <bdi>{new Date(warning.start_at).toLocaleTimeString("fa-IR", {timeZone: "Asia/Tehran", hour: "2-digit", minute: "2-digit", hour12: false})}</bdi>
                        {" تا "}
                        <bdi>{new Date(warning.end_at).toLocaleTimeString("fa-IR", {timeZone: "Asia/Tehran", hour: "2-digit", minute: "2-digit", hour12: false})}</bdi>
                      </span>
                    ))}
                    {!summary.complete ? <span> · دادهٔ روز ناقص است</span> : null}
                  </p>
                </>
              ) : (
                <p className="day-summary-line" role="status">
                  در حال دریافت پیش‌بینی روز…
                </p>
              )}
            </div>
          </section>
          <div className="content-grid">
            <section className="forecast" aria-label="پیش‌بینی مقصد">
              <ForecastDayPeriodControls
                days={data.days}
                selectedDate={selected}
                onSelectDate={selectDate}
                period={displayPeriod}
                onSelectPeriod={selectPeriod}
                periodStates={classifyAllPeriods(
                  selected,
                  data.meta.current_local_time,
                )}
                onLockedDate={access}
              />
              {!weather ? (
                status === "loading" ? (
                  <LoadingState />
                ) : null
              ) : weather.empty || !weather.hourly.length ? (
                <EmptyState
                  title="پیش‌بینی این روز در دسترس نیست"
                  detail="روز دیگری را انتخاب کن یا بعداً دوباره سر بزن."
                />
              ) : (
                <>
                  {data.partial ? (
                    <p className="partial-notice" role="status">
                      بعضی ساعت‌های این بازه در دسترس نیستند.
                    </p>
                  ) : null}
                  <HourlyForecast
                    key={`${slug}:${selected}:${displayPeriod}`}
                    hours={data.hourly}
                    dayLabel={dayLabel}
                  />
                </>
              )}
            </section>
            {data.related_routes.length ? (
              <RelatedRoutes
                routes={data.related_routes}
                title={data.related_routes_title}
              />
            ) : data.related_destinations.length ? (
              <RelatedDestinations
                destinations={data.related_destinations}
                title={data.related_destinations_title}
              />
            ) : null}
          </div>
        </>
      ) : null}
    </PageShell>
  );
}
export function PointPlacePage() {
  return <PlaceForecastPage kind="point" />;
}
export { PlaceForecastPage };
