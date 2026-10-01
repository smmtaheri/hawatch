import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../../api/client";
import { PageShell } from "../../components/PageShell";
import { ErrorState } from "../../components/ErrorState";
import { LoadingState } from "../../components/LoadingState";
import {
  SearchCombobox,
  type SearchComboboxHandle,
} from "../../components/SearchCombobox";
import { CategoryIcon, DesignIcon } from "../../components/DesignIcon";
import { StaleDataNotice } from "../../components/StaleDataNotice";
import { usePageTitle } from "../../lib/pageTitle";
import type { CatalogCounts, PointSummary } from "../../types";

export function HomePage() {
  usePageTitle();
  const [query, setQuery] = useState("");
  const [popularPoints, setPopularPoints] = useState<PointSummary[]>([]);
  const [counts, setCounts] = useState<CatalogCounts | null>(null);
  const [freshness, setFreshness] = useState("ready");
  const [status, setStatus] = useState<"loading" | "ready" | "error">(
    "loading",
  );
  const searchRef = useRef<SearchComboboxHandle>(null);
  const request = useRef(0);
  function load() {
    const id = ++request.current;
    setStatus("loading");
    api
      .points()
      .then((payload) => {
        if (id !== request.current) return;
        setPopularPoints(payload.results);
        setCounts(payload.meta.catalog_counts ?? null);
        setFreshness(payload.meta.freshness);
        setStatus("ready");
      })
      .catch(() => {
        if (id === request.current) setStatus("error");
      });
  }
  useEffect(() => {
    load();
    return () => {
      ++request.current;
    };
  }, []);
  return (
    <PageShell className="home-page">
      <section className="home-hero">
        <h1>پیش‌بینی هوای نقاط و مسیرها</h1>
        <p>برای برنامه‌ریزی طبیعت‌گردی</p>
      </section>
      <div className="home-workspace">
        <div className="home-main">
          <form
            className="search-field home-search-box"
            role="search"
            onSubmit={(e) => {
              e.preventDefault();
              searchRef.current?.submit();
            }}
          >
            <SearchCombobox ref={searchRef} value={query} onChange={setQuery} />
            {query ? (
              <button
                className="search-clear"
                type="button"
                aria-label="پاک کردن جست‌وجو"
                onClick={() => setQuery("")}
              >
                <DesignIcon name="close" />
              </button>
            ) : null}
            <button type="submit">جست‌وجو</button>
          </form>
          <section className="popular" id="search-results">
            <h2>مقصدهای محبوب</h2>
            {freshness === "stale" ? <StaleDataNotice /> : null}
            {status === "loading" ? (
              <LoadingState label="در حال بارگذاری نقاط…" />
            ) : null}
            {status === "error" ? <ErrorState onRetry={load} /> : null}
            <div className="popular-grid">
              {popularPoints.map((item) => (
                <Link className="popular-card" key={item.slug} to={item.href}>
                  <CategoryIcon
                    category={item.category_key}
                    placeType={item.place_type}
                  />
                  <strong>{item.tile_name || item.name}</strong>
                  <DesignIcon name="chevron-left" />
                </Link>
              ))}
            </div>
          </section>
        </div>
        {counts ? (
          <aside className="home-stats" aria-label="آمار کاتالوگ هواچ">
            <div>
              <strong>{counts.points.toLocaleString("fa-IR")}</strong>
              <span>نقطهٔ فعال</span>
            </div>
            <div>
              <strong>{counts.routes.toLocaleString("fa-IR")}</strong>
              <span>مسیر ثبت‌شده</span>
            </div>
          </aside>
        ) : null}
      </div>
    </PageShell>
  );
}
