import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import type { RouteSummary } from "../types";
import { DestinationCard } from "./DestinationCard";

function featuredRoutes(routes: RouteSummary[]): RouteSummary[] {
  return [...routes.filter((route) => route.featured), ...routes.filter((route) => !route.featured)].slice(0, 2);
}

export function MobileRouteSelector({ routes, title }: { routes: RouteSummary[]; title: string }) {
  const [isOpen, setIsOpen] = useState(false);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const closeButtonRef = useRef<HTMLButtonElement>(null);
  const touchStartY = useRef<number | null>(null);
  const topRoutes = featuredRoutes(routes);
  const hasMoreRoutes = routes.length > topRoutes.length;

  useEffect(() => {
    if (!isOpen) return;

    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    closeButtonRef.current?.focus();

    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") setIsOpen(false);
    }

    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("keydown", onKeyDown);
      document.body.style.overflow = previousOverflow;
      triggerRef.current?.focus();
    };
  }, [isOpen]);

  if (!routes.length) return null;

  return (
    <section className="mobile-route-selection" aria-label={title}>
      <div className="mobile-route-selection-heading">
        <div>
          <span className="eyebrow teal-text">مسیرهای پیشنهادی</span>
          <h2>{title}</h2>
        </div>
        <span className="mobile-route-selection-count">{routes.length} مسیر</span>
      </div>
      <div className="mobile-route-selection-top">
        {topRoutes.map((route) => (
          <DestinationCard key={route.slug} route={route} />
        ))}
      </div>
      {hasMoreRoutes ? (
        <button
          ref={triggerRef}
          className="mobile-route-selection-trigger"
          type="button"
          aria-haspopup="dialog"
          aria-expanded={isOpen}
          onClick={() => setIsOpen(true)}
        >
          انتخاب از بین {routes.length} مسیر
          <span aria-hidden="true">←</span>
        </button>
      ) : null}
      {isOpen ? (
        <div className="mobile-route-sheet-layer" role="presentation">
          <button
            className="mobile-route-sheet-backdrop"
            type="button"
            aria-label="بستن پنجرهٔ انتخاب مسیر"
            onClick={() => setIsOpen(false)}
          />
          <section
            className="mobile-route-sheet"
            role="dialog"
            aria-modal="true"
            aria-labelledby="mobile-route-sheet-title"
            onTouchStart={(event) => {
              touchStartY.current = event.touches[0]?.clientY ?? null;
            }}
            onTouchEnd={(event) => {
              const startY = touchStartY.current;
              const endY = event.changedTouches[0]?.clientY;
              touchStartY.current = null;
              if (startY !== null && endY !== undefined && endY - startY > 64) setIsOpen(false);
            }}
          >
            <div className="mobile-route-sheet-handle" aria-hidden="true" />
            <div className="mobile-route-sheet-heading">
              <div>
                <span className="eyebrow teal-text">{title}</span>
                <h2 id="mobile-route-sheet-title">انتخاب مسیر</h2>
              </div>
              <button
                ref={closeButtonRef}
                className="mobile-route-sheet-close"
                type="button"
                aria-label="بستن انتخاب مسیر"
                onClick={() => setIsOpen(false)}
              >
                ×
              </button>
            </div>
            <div className="mobile-route-sheet-list">
              {routes.map((route) => (
                <Link key={route.slug} to={route.href} className="mobile-route-sheet-item">
                  <span className="mobile-route-sheet-item-icon" aria-hidden="true">
                    ⌁
                  </span>
                  <span className="mobile-route-sheet-item-copy">
                    <strong>{route.title}</strong>
                    <small>
                      {route.distance_label}　·　{route.timing_pending ? "زمان تخمینی در دسترس نیست" : route.timing_status === "estimated" ? "تخمینی" : "زمان‌بندی شده"}
                    </small>
                  </span>
                  <span className="mobile-route-sheet-item-arrow" aria-hidden="true">
                    ←
                  </span>
                </Link>
              ))}
            </div>
          </section>
        </div>
      ) : null}
    </section>
  );
}
