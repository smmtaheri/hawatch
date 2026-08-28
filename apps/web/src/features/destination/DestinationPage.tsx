import { useEffect, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { api, ApiError } from "../../api/client";
import { BackNavigation } from "../../components/BackNavigation";
import { Breadcrumbs } from "../../components/Breadcrumbs";
import { DaySelector } from "../../components/DaySelector";
import { DecisionCard } from "../../components/DecisionCard";
import { DestinationCard } from "../../components/DestinationCard";
import { EmptyState } from "../../components/EmptyState";
import { ErrorState } from "../../components/ErrorState";
import { Header } from "../../components/Header";
import { HourlyForecast } from "../../components/HourlyForecast";
import { LoadingState } from "../../components/LoadingState";
import { PeriodToggle } from "../../components/PeriodToggle";
import { StaleDataNotice } from "../../components/StaleDataNotice";
import { buildForecastParams } from "../../lib/periods";
import type { DestinationForecast, PeriodId } from "../../types";

export function DestinationPage() {
  const { slug = "touchal" } = useParams();
  const [searchParams] = useSearchParams();
  const [date, setDate] = useState<string | undefined>(() => searchParams.get("date") ?? undefined);
  const [period, setPeriod] = useState<PeriodId | undefined>(
    () => (searchParams.get("period") as PeriodId | null) ?? undefined,
  );
  const [data, setData] = useState<DestinationForecast | null>(null);
  const [status, setStatus] = useState<"loading" | "ready" | "error" | "missing">("loading");
  const displayPeriod = period ?? (data?.meta.selected_period as PeriodId | undefined) ?? "morning";

  function load() {
    setStatus("loading");
    api
      .destinationForecast(
        slug,
        buildForecastParams({
          date,
          period,
          includeDate: Boolean(date),
          includePeriod: Boolean(period),
        }),
      )
      .then((payload) => {
        setData(payload);
        if (!date) setDate(payload.meta.selected_date);
        if (!period) setPeriod(payload.meta.selected_period as PeriodId);
        setStatus("ready");
      })
      .catch((error) => setStatus(error instanceof ApiError && error.status === 404 ? "missing" : "error"));
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [slug, date, period]);

  if (status === "missing") {
    return (
      <main className="destination-page">
        <Header />
        <EmptyState title="مقصد پیدا نشد" detail="به صفحهٔ خانه برگرد و مقصد دیگری را انتخاب کن." />
      </main>
    );
  }

  const selected = date ?? data?.meta.selected_date ?? "";
  const routes = data?.destination.routes ?? [];

  return (
    <main className={`destination-page destination-${slug}`}>
      <div className="destination-shell">
        <Header />
        {status === "error" ? <ErrorState onRetry={() => load()} /> : null}
        {status === "loading" && !data ? <LoadingState /> : null}
        {data ? (
          <>
            {data.meta.freshness === "stale" ? <StaleDataNotice generatedAt={data.meta.generated_at} /> : null}
            <section className="destination-hero">
              <BackNavigation to="/" ariaLabel="بازگشت به هوم" />
              <img src={data.destination.image} alt={data.destination.image_alt} />
              <div className="destination-hero-overlay" />
              <div className="destination-heading">
                <Breadcrumbs items={[{ label: "مقصدها", to: "/#search-results" }, { label: data.destination.name }]} />
                <h1>{data.destination.name}</h1>
                <p>
                  {data.destination.category}　·　{data.destination.elevation_label}
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
                  <div className="section-title-row">
                    <div>
                      <h2>پیش‌بینی {data.destination.name}</h2>
                      <p className="muted">روز و ساعت را انتخاب کن تا تغییر شرایط مقصد و مسیرهایش را قبل از حرکت ببینی.</p>
                    </div>
                    <span className="updated">{data.updated_label}</span>
                  </div>
                  <DaySelector days={data.days} selected={selected} onSelect={setDate} />
                  <div className="mobile-weather-controls">
                    <div className="mobile-route-picker" aria-label="انتخاب مسیر">
                      <div className="mobile-route-picker-heading">
                        <span>مسیرها</span>
                        <small>{routes.length} مسیر</small>
                      </div>
                      <div className="mobile-route-picker-list">
                        {routes.map((route) => (
                          <Link
                            key={route.slug}
                            className={`mobile-route-picker-button ${route.featured ? "selected" : ""}`}
                            to={route.href}
                            aria-label={`مشاهدهٔ مسیر ${route.title}`}
                          >
                            {route.title}
                          </Link>
                        ))}
                      </div>
                    </div>
                    <div className="destination-period-row">
                      <span className="planner-label">بازهٔ نمایش هوا</span>
                      <PeriodToggle value={displayPeriod} onChange={setPeriod} />
                    </div>
                  </div>
                  {data.empty ? (
                    <EmptyState title="پیش‌بینی این روز در دسترس نیست" detail="روز دیگری را انتخاب کن یا بعداً دوباره سر بزن." />
                  ) : (
                    <HourlyForecast hours={data.hourly} headline={data.period.headline} />
                  )}
                </section>
                <section className="technical-card card-surface">
                  <div className="section-title-row">
                    <h2>جزئیات تخصصی {data.days.find((day) => day.date === selected)?.label ?? "امروز"}</h2>
                    <span className="updated">اطلاعات نمونه برای تصمیم‌گیری مسیر</span>
                  </div>
                  <div className="metric-grid">
                    {data.metrics.map((metric) => (
                      <div className="metric" key={metric.label}>
                        <span className="metric-label">
                          {metric.icon}　{metric.label}
                        </span>
                        <strong className={metric.color || ""}>{metric.value}</strong>
                        <small>{metric.note}</small>
                      </div>
                    ))}
                  </div>
                </section>
              </div>
              <aside className="destination-side">
                <section
                  className={`top-routes-card compact-route-box card-surface ${routes.length === 1 ? "single-route" : ""} ${routes.length === 0 ? "no-routes" : ""}`}
                  id="routes"
                >
                  <div className="compact-route-heading">
                    <div>
                      <span className="eyebrow teal-text">تصمیم بعدی</span>
                      <h2>مسیرها</h2>
                    </div>
                  </div>
                  <div className="route-cards">
                    {routes.length ? (
                      routes.map((route) => <DestinationCard key={route.slug} route={route} />)
                    ) : (
                      <div className="route-empty-state">
                        <strong>هنوز ترکی برای این مقصد ثبت نشده</strong>
                        <span>این صفحه فقط پیش‌بینی مقصد را نشان می‌دهد؛ به‌محض ثبت ترک پیاده‌روی، اینجا اضافه می‌شود.</span>
                      </div>
                    )}
                  </div>
                </section>
                <DecisionCard chip={data.decision.chip} title={data.decision.title} text={data.decision.text} />
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
