import { useCallback, useEffect, useRef, useState, type MouseEvent } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../../api/client";
import { EmptyState } from "../../components/EmptyState";
import { ErrorState } from "../../components/ErrorState";
import { Header } from "../../components/Header";
import { LoadingState } from "../../components/LoadingState";
import { DestinationIcon } from "../../components/PointIcon";
import { usePageTitle } from "../../lib/pageTitle";
import type { PointSummary } from "../../types";

const DESTINATIONS_TITLE = "مقصدهای اصلی هواچ | قله‌ها، دریاچه‌ها و مسیرها";
const DESTINATIONS_DESCRIPTION =
  "مقصدهای اصلی هواچ؛ پیش‌بینی آب‌وهوای قله‌ها، دریاچه‌ها و عارضه‌های مهم برای برنامه‌ریزی مسیر.";

function positivePage(value?: string) {
  const page = Number(value || "1");
  return Number.isInteger(page) && page > 0 ? page : 1;
}

function appendUnique(current: PointSummary[], incoming: PointSummary[]) {
  const seen = new Set(current.map((destination) => destination.slug));
  return [...current, ...incoming.filter((destination) => !seen.has(destination.slug))];
}

function destinationMeta(destination: PointSummary) {
  return [destination.short_category || destination.category, destination.region].filter(Boolean).join(" · ");
}

export function DestinationsPage() {
  const { page: pageParam } = useParams<{ page?: string }>();
  const initialPage = positivePage(pageParam);
  const [destinations, setDestinations] = useState<PointSummary[]>([]);
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");
  const [hasNext, setHasNext] = useState(false);
  const [nextPage, setNextPage] = useState<number | null>(null);
  const [nextHref, setNextHref] = useState<string | null>(null);
  const [loadingMore, setLoadingMore] = useState(false);
  const [loadMoreError, setLoadMoreError] = useState(false);
  const sentinelRef = useRef<HTMLDivElement | null>(null);
  const loadedPagesRef = useRef<Set<number>>(new Set());
  const inFlightPagesRef = useRef<Set<number>>(new Set());
  const supportsAutoLoad = useState(
    () => typeof window !== "undefined" && "IntersectionObserver" in window,
  )[0];

  usePageTitle(undefined, {
    title: initialPage === 1 ? DESTINATIONS_TITLE : `${DESTINATIONS_TITLE} | بخش ${initialPage}`,
    description: DESTINATIONS_DESCRIPTION,
  });

  const loadPage = useCallback(async (page: number, replace = false) => {
    if (loadedPagesRef.current.has(page) || inFlightPagesRef.current.has(page)) return;
    inFlightPagesRef.current.add(page);
    if (replace) {
      setStatus("loading");
    } else {
      setLoadingMore(true);
      setLoadMoreError(false);
    }

    try {
      const payload = await api.destinations(page);
      const pagination = payload.pagination || {
        page,
        page_size: payload.destinations.length,
        total: payload.destinations.length,
        has_next: false,
        next_page: null,
        next_href: null,
        previous_href: null,
      };
      loadedPagesRef.current.add(page);
      setDestinations((current) => (
        replace ? payload.destinations : appendUnique(current, payload.destinations)
      ));
      setHasNext(pagination.has_next);
      setNextPage(pagination.next_page);
      setNextHref(pagination.next_href);
      setStatus("ready");
    } catch {
      if (replace) {
        setStatus("error");
      } else {
        setLoadMoreError(true);
      }
    } finally {
      inFlightPagesRef.current.delete(page);
      if (!replace) setLoadingMore(false);
    }
  }, []);

  useEffect(() => {
    loadedPagesRef.current.clear();
    inFlightPagesRef.current.clear();
    setDestinations([]);
    setHasNext(false);
    setNextPage(null);
    setNextHref(null);
    setLoadMoreError(false);
    void loadPage(initialPage, true);
  }, [initialPage, loadPage]);

  useEffect(() => {
    const sentinel = sentinelRef.current;
    if (!supportsAutoLoad || !sentinel || status !== "ready" || !hasNext || nextPage === null) return;

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) void loadPage(nextPage);
      },
      { rootMargin: "600px 0px" },
    );
    observer.observe(sentinel);
    return () => observer.disconnect();
  }, [hasNext, loadPage, nextPage, status, supportsAutoLoad]);

  function retryNextPage(event: MouseEvent<HTMLAnchorElement>) {
    event.preventDefault();
    if (nextPage !== null) void loadPage(nextPage);
  }

  return (
    <main className="destinations-page">
      <div className="destinations-shell">
        <Header />
        <section className="destinations-heading" aria-labelledby="destinations-title">
          <h1 id="destinations-title">مقصدهای اصلی هواچ</h1>
          <p>مقصدهای مستقل و شناخته‌شده را برای دیدن پیش‌بینی هوا انتخاب کن.</p>
        </section>

        {status === "loading" ? <LoadingState label="در حال بارگذاری مقصدها…" /> : null}
        {status === "error" ? (
          <ErrorState onRetry={() => void loadPage(initialPage, true)} message="بارگذاری مقصدها ناموفق بود." />
        ) : null}
        {status === "ready" && !destinations.length ? (
          <EmptyState title="هنوز مقصدی ثبت نشده است." detail="بعداً دوباره سر بزن." />
        ) : null}
        {status === "ready" && destinations.length ? (
          <>
            <section className="destination-grid" aria-label="فهرست مقصدهای اصلی">
              {destinations.map((destination) => (
                <Link key={destination.slug} to={destination.href} className="destination-card">
                  <DestinationIcon
                    className="destination-card-icon"
                    categoryKey={destination.category_key}
                    placeType={destination.place_type}
                  />
                  <span className="destination-card-copy">
                    <strong>{destination.name}</strong>
                    <small>{destinationMeta(destination)}</small>
                    <small>{destination.elevation_label}</small>
                  </span>
                  <span className="destination-card-arrow" aria-hidden="true">←</span>
                </Link>
              ))}
            </section>
            {hasNext ? (
              <div ref={sentinelRef} className="destinations-load-more" aria-live="polite">
                {loadingMore ? <span>در حال بارگذاری مقصدهای بیشتر…</span> : null}
                {!supportsAutoLoad || loadMoreError ? (
                  <a href={nextHref || `/destinations/page/${nextPage}`} onClick={retryNextPage}>
                    نمایش مقصدهای بیشتر
                  </a>
                ) : null}
              </div>
            ) : null}
          </>
        ) : null}
      </div>
    </main>
  );
}
