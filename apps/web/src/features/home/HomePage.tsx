import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../../api/client";
import { Header } from "../../components/Header";
import { EmptyState } from "../../components/EmptyState";
import { ErrorState } from "../../components/ErrorState";
import { LoadingState } from "../../components/LoadingState";
import { StaleDataNotice } from "../../components/StaleDataNotice";
import { DestinationIcon } from "../../components/DestinationIcon";
import type { DestinationSummary } from "../../types";

function tileWords(name: string) {
  return name.split(" ").filter(Boolean);
}

export function HomePage() {
  const [query, setQuery] = useState("");
  const [submitted, setSubmitted] = useState("");
  const [destinations, setDestinations] = useState<DestinationSummary[]>([]);
  const [empty, setEmpty] = useState(false);
  const [freshness, setFreshness] = useState("ready");
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");

  function load(search = "") {
    setStatus("loading");
    api
      .destinations(search)
      .then((payload) => {
        setDestinations(payload.results);
        setEmpty(payload.empty);
        setFreshness(payload.meta.freshness);
        setStatus("ready");
      })
      .catch(() => setStatus("error"));
  }

  useEffect(() => {
    load();
  }, []);

  const heading = submitted ? "نتایج مرتبط" : "مقصدهای محبوب";
  const visible = useMemo(() => destinations, [destinations]);

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
                const next = query.trim();
                setSubmitted(next);
                load(next);
              }}
            >
              <input
                aria-label="جست‌وجوی مقصد"
                placeholder="مثلاً توچال، دماوند یا دریاسر"
                value={query}
                onChange={(event) => {
                  setQuery(event.target.value);
                  if (submitted) {
                    setSubmitted("");
                    load();
                  }
                }}
              />
              <button type="submit">جست‌وجو</button>
            </form>
            <div className="hero-destinations" id="search-results">
              <div className="hero-destinations-heading">
                <span>{heading}</span>
                <i />
              </div>
              {freshness === "stale" ? <StaleDataNotice /> : null}
              {status === "loading" ? <LoadingState label="در حال بارگذاری مقصدها…" /> : null}
              {status === "error" ? <ErrorState onRetry={() => load(submitted)} /> : null}
              {status === "ready" && empty ? (
                <EmptyState
                  title="مقصد مرتبطی پیدا نشد؛ نام مقصد دیگری را امتحان کن."
                  detail="برای دیدن پیش‌بینی، روی مقصد موردنظرت بزن."
                />
              ) : null}
              {status === "ready" && !empty ? (
                <div className="destination-grid">
                  {visible.map((item) => (
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
              {status === "ready" && submitted && !empty ? (
                <p className="muted">برای دیدن پیش‌بینی، روی مقصد موردنظرت بزن.</p>
              ) : null}
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}
