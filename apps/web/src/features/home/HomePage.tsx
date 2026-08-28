import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../../api/client";
import { Header } from "../../components/Header";
import { EmptyState } from "../../components/EmptyState";
import { ErrorState } from "../../components/ErrorState";
import { LoadingState } from "../../components/LoadingState";
import { SearchCombobox, type SearchComboboxHandle } from "../../components/SearchCombobox";
import { StaleDataNotice } from "../../components/StaleDataNotice";
import { DestinationIcon } from "../../components/DestinationIcon";
import type { DestinationSummary, SearchSuggestion } from "../../types";

function tileWords(name: string) {
  return name.split(" ").filter(Boolean);
}

export function HomePage() {
  const [query, setQuery] = useState("");
  const [submittedQuery, setSubmittedQuery] = useState("");
  const [searchResults, setSearchResults] = useState<SearchSuggestion[]>([]);
  const [popularDestinations, setPopularDestinations] = useState<DestinationSummary[]>([]);
  const [freshness, setFreshness] = useState("ready");
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");
  const searchRef = useRef<SearchComboboxHandle>(null);

  function loadPopular() {
    setStatus("loading");
    api
      .destinations()
      .then((payload) => {
        setPopularDestinations(payload.results);
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
    setStatus("ready");
  }

  const showingSearch = Boolean(submittedQuery);
  const heading = showingSearch ? "نتایج مرتبط" : "مقصدهای محبوب";

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
                }}
                onUnifiedSearch={handleUnifiedSearch}
              />
              <button type="submit">جست‌وجو</button>
            </form>
            <div className="hero-destinations" id="search-results">
              <div className="hero-destinations-heading">
                <span>{heading}</span>
                <i />
              </div>
              {freshness === "stale" ? <StaleDataNotice /> : null}
              {status === "loading" && !showingSearch ? <LoadingState label="در حال بارگذاری مقصدها…" /> : null}
              {status === "error" && !showingSearch ? <ErrorState onRetry={loadPopular} /> : null}
              {showingSearch && !searchResults.length ? (
                <EmptyState
                  title="نتیجه‌ای پیدا نشد؛ نام دیگری را امتحان کن."
                  detail="مقصد یا نقطهٔ مسیر را با حداقل دو حرف جست‌وجو کن."
                />
              ) : null}
              {showingSearch && searchResults.length ? (
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
                <div className="destination-grid">
                  {popularDestinations.map((item) => (
                    <Link key={item.slug} to={item.href} className="destination-tile">
                      <span className="destination-tile-copy">
                        <strong>
                          {tileWords(item.tile_name).map((word) => (
                            <span className="destination-name-word" key={word}>
                              {word}
                            </span>
                          ))}
                        </strong>
                        <small>{item.short_category}</small>
                      </span>
                      <span className="tile-icon">
                        <DestinationIcon categoryKey={item.category_key} />
                      </span>
                      <span className="tile-arrow">←</span>
                    </Link>
                  ))}
                </div>
              ) : null}
              {showingSearch && searchResults.length ? (
                <p className="muted">برای دیدن پیش‌بینی، روی نتیجهٔ موردنظرت بزن.</p>
              ) : null}
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}
