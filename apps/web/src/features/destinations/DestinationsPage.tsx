import { useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../../api/client";
import { PageShell } from "../../components/PageShell";
import { CategoryIcon, DesignIcon } from "../../components/DesignIcon";
import { ErrorState } from "../../components/ErrorState";
import { LoadingState } from "../../components/LoadingState";
import { usePageTitle } from "../../lib/pageTitle";
import type { PointSummary, RouteSummary } from "../../types";

export function CatalogPage({ kind }: { kind: "destinations" | "routes" }) {
  const routeList = kind === "routes";
  const { page: pageParam } = useParams();
  const initialPage = Math.max(1, Number(pageParam) || 1);
  const [query, setQuery] = useState("");
  const [search, setSearch] = useState("");
  const [points, setPoints] = useState<PointSummary[]>([]);
  const [routes, setRoutes] = useState<RouteSummary[]>([]);
  const [status, setStatus] = useState<"loading" | "ready" | "error">(
    "loading",
  );
  const [next, setNext] = useState<number | null>(null);
  const [loadingMore, setLoadingMore] = useState(false);
  const [moreError, setMoreError] = useState(false);
  const [retry, setRetry] = useState(0);
  const generation = useRef(0);
  const moreBusy = useRef(false);
  const sentinel = useRef<HTMLDivElement>(null);
  usePageTitle(undefined, {
    title: routeList
      ? "مسیرهای هواچ | پیش‌بینی هوای مسیر"
      : "مقصدهای اصلی هواچ | قله‌ها، دریاچه‌ها و مسیرها",
    description: routeList
      ? "هوای مسیر را در زمان رسیدن به هر نقطه ببین."
      : "مقصدهای اصلی هواچ؛ پیش‌بینی آب‌وهوای قله‌ها، دریاچه‌ها و عارضه‌های مهم برای برنامه‌ریزی مسیر.",
  });
  useEffect(() => {
    const timer = window.setTimeout(() => setSearch(query), 120);
    return () => window.clearTimeout(timer);
  }, [query]);
  useEffect(() => {
    const id = ++generation.current;
    setStatus("loading");
    setPoints([]);
    setRoutes([]);
    setNext(null);
    setMoreError(false);
    setLoadingMore(false);
    moreBusy.current = false;
    const promise = routeList
      ? api.routes(search)
      : api.destinations(initialPage, search);
    void promise
      .then((payload) => {
        if (id !== generation.current) return;
        if ("routes" in payload) setRoutes(payload.routes);
        else {
          setPoints(payload.destinations);
          setNext(payload.pagination.next_page);
        }
        setStatus("ready");
      })
      .catch(() => {
        if (id === generation.current) setStatus("error");
      });
    return () => {
      ++generation.current;
    };
  }, [routeList, search, initialPage, retry]);
  async function more() {
    if (next === null || moreBusy.current) return;
    moreBusy.current = true;
    setLoadingMore(true);
    setMoreError(false);
    const id = generation.current;
    try {
      const payload = await api.destinations(next, search);
      if (id !== generation.current) return;
      setPoints((current) => [
        ...current,
        ...payload.destinations.filter(
          (p) => !current.some((old) => old.slug === p.slug),
        ),
      ]);
      setNext(payload.pagination.next_page);
    } catch {
      if (id === generation.current) setMoreError(true);
    } finally {
      if (id === generation.current) {
        moreBusy.current = false;
        setLoadingMore(false);
      }
    }
  }
  useEffect(() => {
    if (!sentinel.current || next === null || !window.IntersectionObserver)
      return;
    if (moreError) return;
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) void more();
      },
      { rootMargin: "400px" },
    );
    observer.observe(sentinel.current);
    return () => observer.disconnect();
  }, [next, search, moreError]);
  const empty = routeList ? !routes.length : !points.length;
  return (
    <PageShell
      className={routeList ? "route-page routes-page" : "destinations-page"}
      back
    >
      <section className="catalog-hero">
        <h1>{routeList ? "مسیرهای هواچ" : "مقصدهای اصلی هواچ"}</h1>
        <p>
          {routeList
            ? "هوای مسیرت را در زمان رسیدن به هر نقطه ببین."
            : "مقصدت را برای دیدن پیش‌بینی هوا انتخاب کن."}
        </p>
      </section>
      <form
        className="search-field"
        role="search"
        onSubmit={(e) => {
          e.preventDefault();
          setSearch(query);
        }}
      >
        <label className="sr-only" htmlFor="catalog-search">
          {routeList ? "جست‌وجوی مسیرها" : "جست‌وجوی مقصدها"}
        </label>
        <input
          id="catalog-search"
          type="search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder={
            routeList
              ? "مثلاً دربند تا توچال"
              : "مثلاً توچال، جنگل ابر یا دریاچهٔ تار"
          }
        />
        <button type="submit">جست‌وجو</button>
      </form>
      {status === "loading" ? (
        <LoadingState
          label={
            routeList ? "در حال بارگذاری مسیرها…" : "در حال بارگذاری مقصدها…"
          }
        />
      ) : null}
      {status === "error" ? (
        <ErrorState onRetry={() => setRetry((v) => v + 1)} />
      ) : null}
      {status === "ready" ? (
        <section
          className={`catalog-grid ${routeList ? "route-catalog" : "destination-grid"}`}
          aria-label={routeList ? "فهرست مسیرها" : "فهرست مقصدهای اصلی"}
        >
          {empty ? (
            <div className="empty-search">
              <p>نتیجه‌ای برای این جست‌وجو پیدا نشد.</p>
              <button
                className="outline-button"
                type="button"
                onClick={() => setQuery("")}
              >
                نمایش همه
              </button>
            </div>
          ) : null}
          {routeList
            ? routes.map((route) => (
                <Link className="catalog-row" key={route.slug} to={route.href}>
                  <DesignIcon name="category-route" className="category-icon" />
                  <span>
                    <strong>{route.title}</strong>
                    <small>
                      مسافت:{" "}
                      <bdi>
                        {route.distance_label.replace(/km/g, "کیلومتر")}
                      </bdi>{" "}
                      · صعود:{" "}
                      <bdi>{route.ascent_label.replace(/ m/g, " متر")}</bdi>
                    </small>
                  </span>
                  <DesignIcon name="chevron-left" />
                </Link>
              ))
            : points.map((point) => (
                <Link
                  className="catalog-row destination-card"
                  key={point.slug}
                  to={point.href}
                >
                  <CategoryIcon
                    category={point.category_key}
                    placeType={point.place_type}
                  />
                  <span>
                    <strong>{point.name}</strong>
                    <small>
                      {point.region} · {point.elevation_label}
                    </small>
                  </span>
                  <DesignIcon name="chevron-left" />
                </Link>
              ))}
        </section>
      ) : null}
      {next !== null ? (
        <div className="destinations-load-more" ref={sentinel}>
          {moreError ? (
            <p role="alert">دریافت ادامهٔ فهرست ناموفق بود.</p>
          ) : null}
          {loadingMore ? (
            <p role="status">در حال بارگذاری مقصدهای بیشتر…</p>
          ) : (
            <a
              className="outline-button"
              href={`/destinations/page/${next}`}
              onClick={(e) => {
                e.preventDefault();
                void more();
              }}
            >
              نمایش مقصدهای بیشتر
            </a>
          )}
        </div>
      ) : null}
    </PageShell>
  );
}
export function DestinationsPage() {
  return <CatalogPage kind="destinations" />;
}
export function RoutesPage() {
  return <CatalogPage kind="routes" />;
}
