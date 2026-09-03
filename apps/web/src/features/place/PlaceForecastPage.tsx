import { useEffect } from "react";
import { Navigate, useLocation, useParams } from "react-router-dom";
import { BackNavigation } from "../../components/BackNavigation";
import { Breadcrumbs } from "../../components/Breadcrumbs";
import { ForecastDayPeriodControls } from "../../components/DaySelector";
import { DesktopRouteSelector } from "../../components/DesktopRouteSelector";
import { EmptyState } from "../../components/EmptyState";
import { ErrorState } from "../../components/ErrorState";
import { Header } from "../../components/Header";
import { HourlyForecast } from "../../components/HourlyForecast";
import { LoadingState } from "../../components/LoadingState";
import { MobileRouteSelector } from "../../components/MobileRouteSelector";
import { SpecialistMetrics } from "../../components/SpecialistMetrics";
import { StaleDataNotice } from "../../components/StaleDataNotice";
import { usePageTitle } from "../../lib/pageTitle";
import { classifyAllPeriods } from "../../lib/periodState";
import { scrollToDetailHero } from "../../lib/detailEntryScroll";
import type { PeriodId } from "../../types";
import type { PlaceKind } from "./placeForecastAdapter";
import { usePlaceForecast } from "./usePlaceForecast";

function PlaceForecastPage({ kind }: { kind: PlaceKind }) {
  const { slug = kind === "destination" ? "touchal" : "" } = useParams();
  const location = useLocation();
  const {
    data,
    status,
    displayPeriod,
    selected,
    selectDate,
    selectPeriod,
    reload,
    canonicalRedirect,
  } = usePlaceForecast({ kind, slug });
  usePageTitle(data?.subject.name);

  // Detail pages open at their identity hero. The public site header is
  // already at document top, so targeting it makes deep-link navigation look
  // like no scroll happened at all.
  useEffect(() => {
    if (!data?.subject.slug) return;
    const frame = window.requestAnimationFrame(() => {
      scrollToDetailHero(".destination-page .destination-hero");
    });
    return () => window.cancelAnimationFrame(frame);
  }, [data?.subject.slug]);

  if (canonicalRedirect) {
    return <Navigate to={canonicalRedirect} replace state={location.state} />;
  }

  if (status === "missing") {
    return (
      <main className="destination-page">
        <div className="destination-shell">
          <Header />
          <div className="page-back-navigation">
            <BackNavigation />
          </div>
          <EmptyState
            title={kind === "destination" ? "مقصد پیدا نشد" : "نقطهٔ هواشناسی پیدا نشد"}
            detail={
              kind === "destination"
                ? "به صفحهٔ خانه برگرد و مقصد دیگری را انتخاب کن."
                : "از جست‌وجوی خانه نام دیگری را امتحان کن."
            }
          />
        </div>
      </main>
    );
  }

  const routes = data?.related_routes ?? [];
  const periodStates =
    data?.meta.current_local_time && selected
      ? classifyAllPeriods(selected, data.meta.current_local_time)
      : undefined;
  const heroImage = data?.subject.hero_image;
  const pageClass =
    kind === "destination" && data?.destinationSlug
      ? `destination-page destination-${data.destinationSlug}`
      : "destination-page";
  const dayLabel = data?.days.find((day) => day.date === selected)?.label ?? "امروز";

  return (
    <main className={pageClass} data-place-kind={kind}>
      <div className="destination-shell">
        <Header />
        <div className="page-back-navigation">
          <BackNavigation />
        </div>
        {status === "error" ? <ErrorState onRetry={() => reload()} /> : null}
        {status === "loading" && !data ? <LoadingState /> : null}
        {data ? (
          <>
            {data.meta.freshness === "stale" ? <StaleDataNotice /> : null}
            <section className={`destination-hero${heroImage ? "" : " destination-hero--fallback"}`}>
              <div className="destination-hero-fallback" aria-hidden="true" />
              {heroImage ? <img src={heroImage} alt={data.subject.hero_image_alt} /> : null}
              <div className="destination-hero-overlay" />
              <div className="destination-heading">
                <Breadcrumbs
                  items={[{ label: "مقصدها", to: "/#search-results" }, { label: data.subject.name }]}
                />
                <h1>{data.subject.name}</h1>
                <p>
                  {data.subject.context_label || data.subject.category || data.subject.region}
                  {data.subject.elevation_label ? `　·　${data.subject.elevation_label}` : ""}
                </p>
              </div>
              <div className="hero-status-stack">
                <div className="status-pill now">{data.hero.status}</div>
                <div className="status-pill change">{data.hero.alert}</div>
              </div>
            </section>
            <div className="destination-layout">
              <div className="destination-main">
                <section className="weather-card card-surface">
                  <ForecastDayPeriodControls
                    days={data.days}
                    selectedDate={selected}
                    onSelectDate={selectDate}
                    period={displayPeriod}
                    onSelectPeriod={selectPeriod as (next: PeriodId) => void}
                    periodStates={periodStates}
                  />
                  {data.empty || data.partial ? (
                    <EmptyState
                      title={data.partial ? "پیش‌بینی ناقص" : "پیش‌بینی این روز در دسترس نیست"}
                      detail="روز دیگری را انتخاب کن یا بعداً دوباره سر بزن."
                    />
                  ) : (
                    <HourlyForecast hours={data.hourly} />
                  )}
                </section>
                <MobileRouteSelector routes={routes} title={data.related_routes_title} />
                <section className="technical-card card-surface">
                  <div className="section-title-row">
                    <h2>جزئیات تخصصی {dayLabel}</h2>
                  </div>
                  {data.metrics.length ? (
                    <SpecialistMetrics metrics={data.metrics} dayLabel={dayLabel} />
                  ) : (
                    <EmptyState
                      title="جزئیات تخصصی در دسترس نیست"
                      detail="برای این روز و بازه، متریک تخصصی ثبت نشده است."
                    />
                  )}
                </section>
              </div>
              <aside className="destination-side">
                {routes.length ? (
                  <DesktopRouteSelector routes={routes} title={data.related_routes_title} />
                ) : (
                  <section className="top-routes-card compact-route-box no-routes card-surface" id="routes" aria-label={data.related_routes_title}>
                    <div className="compact-route-heading">
                      <div>
                        <span className="eyebrow teal-text">تصمیم بعدی</span>
                        <h2>{data.related_routes_title}</h2>
                      </div>
                    </div>
                    <div className="route-cards">
                      <div className="route-empty-state">
                        <strong>هنوز مسیری برای این نقطه ثبت نشده</strong>
                        <span>
                          این صفحه فقط پیش‌بینی را نشان می‌دهد؛ به‌محض ثبت ترک پیاده‌روی، اینجا اضافه می‌شود.
                        </span>
                      </div>
                    </div>
                  </section>
                )}
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

export function DestinationPlacePage() {
  return <PlaceForecastPage kind="destination" />;
}

export function PointPlacePage() {
  return <PlaceForecastPage kind="point" />;
}

export { PlaceForecastPage };
