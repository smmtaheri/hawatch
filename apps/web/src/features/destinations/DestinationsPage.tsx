import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../../api/client";
import { EmptyState } from "../../components/EmptyState";
import { ErrorState } from "../../components/ErrorState";
import { Header } from "../../components/Header";
import { LoadingState } from "../../components/LoadingState";
import { DestinationArtwork, hasDestinationArtwork } from "../../components/DestinationArtwork";
import { PointIcon, resolvePointCategoryKey } from "../../components/PointIcon";
import { usePageTitle } from "../../lib/pageTitle";
import type { PointSummary } from "../../types";

const DESTINATIONS_TITLE = "مقصدهای اصلی هواچ | قله‌ها، دریاچه‌ها و مسیرها";
const DESTINATIONS_DESCRIPTION =
  "مقصدهای اصلی هواچ؛ پیش‌بینی آب‌وهوای قله‌ها، دریاچه‌ها و عارضه‌های مهم برای برنامه‌ریزی مسیر.";

function destinationMeta(destination: PointSummary) {
  return [destination.short_category || destination.category, destination.region].filter(Boolean).join(" · ");
}

export function DestinationsPage() {
  const [destinations, setDestinations] = useState<PointSummary[]>([]);
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");

  usePageTitle(undefined, {
    title: DESTINATIONS_TITLE,
    description: DESTINATIONS_DESCRIPTION,
  });

  function load() {
    setStatus("loading");
    api.destinations()
      .then((payload) => {
        setDestinations(payload.destinations);
        setStatus("ready");
      })
      .catch(() => setStatus("error"));
  }

  useEffect(() => {
    load();
  }, []);

  return (
    <main className="destinations-page">
      <div className="destinations-shell">
        <Header />
        <section className="destinations-heading" aria-labelledby="destinations-title">
          <h1 id="destinations-title">مقصدهای اصلی هواچ</h1>
          <p>مقصدهای مستقل و شناخته‌شده را برای دیدن پیش‌بینی هوا انتخاب کن.</p>
        </section>

        {status === "loading" ? <LoadingState label="در حال بارگذاری مقصدها…" /> : null}
        {status === "error" ? <ErrorState onRetry={load} message="بارگذاری مقصدها ناموفق بود." /> : null}
        {status === "ready" && !destinations.length ? (
          <EmptyState title="هنوز مقصدی ثبت نشده است." detail="بعداً دوباره سر بزن." />
        ) : null}
        {status === "ready" && destinations.length ? (
          <section className="destination-grid" aria-label="فهرست مقصدهای اصلی">
            {destinations.map((destination) => (
              <Link key={destination.slug} to={destination.href} className="destination-card">
                <span
                  className={`destination-card-icon${hasDestinationArtwork(resolvePointCategoryKey(destination.category_key, destination.place_type)) ? " has-artwork" : ""}`}
                  aria-hidden="true"
                >
                  {hasDestinationArtwork(resolvePointCategoryKey(destination.category_key, destination.place_type)) ? (
                    <DestinationArtwork categoryKey={resolvePointCategoryKey(destination.category_key, destination.place_type)} />
                  ) : (
                    <PointIcon categoryKey={destination.category_key} placeType={destination.place_type} />
                  )}
                </span>
                <span className="destination-card-copy">
                  <strong>{destination.name}</strong>
                  <small>{destinationMeta(destination)}</small>
                  <small>{destination.elevation_label}</small>
                </span>
                <span className="destination-card-arrow" aria-hidden="true">←</span>
              </Link>
            ))}
          </section>
        ) : null}
      </div>
    </main>
  );
}
