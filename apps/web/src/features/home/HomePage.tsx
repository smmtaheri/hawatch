import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../../api/client";
import { Header } from "../../components/Header";
import { EmptyState } from "../../components/EmptyState";
import { ErrorState } from "../../components/ErrorState";
import { LoadingState } from "../../components/LoadingState";
import { SearchCombobox, type SearchComboboxHandle } from "../../components/SearchCombobox";
import { StaleDataNotice } from "../../components/StaleDataNotice";
import { PointIcon } from "../../components/PointIcon";
import { usePageTitle } from "../../lib/pageTitle";
import type { CatalogCounts, PointSummary, SearchSuggestion } from "../../types";

function tileWords(name: string) {
  return name.split(" ").filter(Boolean);
}

export function HomePage() {
  usePageTitle();
  const [query, setQuery] = useState("");
  const [submittedQuery, setSubmittedQuery] = useState("");
  const [searchResults, setSearchResults] = useState<SearchSuggestion[]>([]);
  const [searchError, setSearchError] = useState(false);
  const [popularPoints, setPopularPoints] = useState<PointSummary[]>([]);
  const [catalogCounts, setCatalogCounts] = useState<CatalogCounts | null>(null);
  const [freshness, setFreshness] = useState("ready");
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");
  const searchRef = useRef<SearchComboboxHandle>(null);

  function loadPopular() {
    setStatus("loading");
    api
      .points()
      .then((payload) => {
        setPopularPoints(payload.results);
        setCatalogCounts(payload.meta.catalog_counts ?? null);
        setFreshness(payload.meta.freshness);
        setStatus("ready");
      })
      .catch(() => setStatus("error"));
  }

  useEffect(() => {
    loadPopular();
  }, []);

  function handleUnifiedSearch(nextQuery: string, results: SearchSuggestion[]) {
    setSubmittedQuery(nextQuery);
    setSearchResults(results);
    setSearchError(false);
    setStatus("ready");
  }

  function handleUnifiedSearchStart(nextQuery: string) {
    setSubmittedQuery(nextQuery);
    setSearchResults([]);
    setSearchError(false);
    setStatus("loading");
  }

  function handleUnifiedSearchError(nextQuery: string) {
    setSubmittedQuery(nextQuery);
    setSearchResults([]);
    setSearchError(true);
    setStatus("ready");
  }

  const showingSearch = Boolean(submittedQuery);
  const heading = showingSearch ? "نتایج مرتبط" : "نقاط شاخص";

  return (
    <main className="home-page">
      <div className="home-shell">
        <section className="home-hero">
          <Header />
          <div className="hero-copy">
            <p className="eyebrow">هوای مسیرت را ببین</p>
            <form
              className="search-box"
              onSubmit={(event) => {
                event.preventDefault();
                searchRef.current?.submit();
              }}
            >
              <SearchCombobox
                ref={searchRef}
                value={query}
                onChange={setQuery}
                onClearSubmitted={() => {
                  setSubmittedQuery("");
                  setSearchResults([]);
                  setSearchError(false);
                }}
                onUnifiedSearchStart={handleUnifiedSearchStart}
                onUnifiedSearch={handleUnifiedSearch}
                onUnifiedSearchError={handleUnifiedSearchError}
              />
              <button type="submit">جست‌وجو</button>
            </form>
            <div className="hero-points" id="search-results">
              <div className="hero-points-heading">
                <span>{heading}</span>
                <i />
              </div>
              {freshness === "stale" ? <StaleDataNotice /> : null}
              {status === "loading" && !showingSearch ? <LoadingState label="در حال بارگذاری نقاط…" /> : null}
              {status === "error" && !showingSearch ? <ErrorState onRetry={loadPopular} /> : null}
              {showingSearch && searchError ? (
                <ErrorState
                  onRetry={() => searchRef.current?.submit()}
                  message="جست‌وجوی نقطه ناموفق بود. دوباره تلاش کن."
                />
              ) : null}
              {showingSearch && !searchError && status === "loading" ? (
                <LoadingState label="در حال جست‌وجو…" />
              ) : null}
              {showingSearch && !searchError && status === "ready" && !searchResults.length ? (
                <EmptyState
                  title="نتیجه‌ای پیدا نشد؛ نام دیگری را امتحان کن."
                  detail="نام نقطه را با حداقل دو حرف جست‌وجو کن."
                />
              ) : null}
              {showingSearch && !searchError && status === "ready" && searchResults.length ? (
                <ul className="search-results-list" aria-label="نتایج جست‌وجو">
                  {searchResults.map((item) => (
                    <li key={`${item.type}-${item.slug}`}>
                      <Link to={item.href} className="search-result-row">
                        <span className="search-result-label">{item.label}</span>
                        <span className="search-result-hint">— {item.hint}</span>
                      </Link>
                    </li>
                  ))}
                </ul>
              ) : null}
              {!showingSearch && status === "ready" ? (
                <div className="point-grid">
                  {popularPoints.map((item) => (
                    <Link key={item.slug} to={item.href} className="point-tile">
                      <span className="point-tile-copy">
                        <strong>
                          {tileWords(item.tile_name).map((word) => (
                            <span className="point-name-word" key={word}>
                              {word}
                            </span>
                          ))}
                        </strong>
                        <small>{item.short_category}</small>
                      </span>
                      <span className="tile-icon">
                        <PointIcon categoryKey={item.category_key} />
                      </span>
                      <span className="tile-arrow">←</span>
                    </Link>
                  ))}
                </div>
              ) : null}
              {!showingSearch && catalogCounts ? (
                <section className="home-catalog-stats" aria-label="آمار کاتالوگ هواچ">
                  <div className="home-catalog-stat">
                    <strong>{catalogCounts.points.toLocaleString("fa-IR")}</strong>
                    <span>نقطهٔ فعال</span>
                  </div>
                  <div className="home-catalog-stat">
                    <strong>{catalogCounts.routes.toLocaleString("fa-IR")}</strong>
                    <span>مسیر ثبت‌شده</span>
                  </div>
                </section>
              ) : null}
              {showingSearch && !searchError && status === "ready" && searchResults.length ? (
                <p className="muted">برای دیدن پیش‌بینی، روی نتیجهٔ موردنظرت بزن.</p>
              ) : null}
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}
