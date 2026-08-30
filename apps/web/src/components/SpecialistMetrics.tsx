import { useEffect, useRef, useState } from "react";
import type { Metric } from "../types";
import { SpecialistMetricIcon } from "./SpecialistMetricIcon";

function MetricTile({ metric }: { metric: Metric }) {
  return (
    <div className="metric">
      <span className="metric-label">
        <SpecialistMetricIcon icon={metric.icon} tone={metric.color} />
        <span>{metric.label}</span>
      </span>
      <strong className={metric.color || ""}>{metric.value}</strong>
      <small>{metric.note}</small>
    </div>
  );
}

export function SpecialistMetrics({ metrics, dayLabel }: { metrics: Metric[]; dayLabel: string }) {
  const [isOpen, setIsOpen] = useState(false);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const closeButtonRef = useRef<HTMLButtonElement>(null);
  const touchStartY = useRef<number | null>(null);
  const preview = metrics.slice(0, 2);
  const remaining = metrics.length - preview.length;

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

  return (
    <>
      <div className="metric-grid specialist-metrics-desktop">
        {metrics.map((metric) => (
          <MetricTile key={metric.label} metric={metric} />
        ))}
      </div>
      <div className="specialist-metrics-mobile">
        <div className="specialist-metrics-preview">
          {preview.map((metric) => (
            <MetricTile key={metric.label} metric={metric} />
          ))}
        </div>
        {remaining > 0 ? (
          <button
            ref={triggerRef}
            className="specialist-metrics-trigger"
            type="button"
            aria-haspopup="dialog"
            aria-expanded={isOpen}
            onClick={() => setIsOpen(true)}
          >
            دیدن {remaining.toLocaleString("fa-IR")} جزئیات بیشتر
            <span aria-hidden="true">←</span>
          </button>
        ) : null}
      </div>
      {isOpen ? (
        <div className="specialist-metrics-sheet-layer" role="presentation">
          <button
            className="specialist-metrics-sheet-backdrop"
            type="button"
            aria-label="بستن جزئیات تخصصی"
            onClick={() => setIsOpen(false)}
          />
          <section
            className="specialist-metrics-sheet"
            role="dialog"
            aria-modal="true"
            aria-labelledby="specialist-metrics-sheet-title"
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
            <div className="specialist-metrics-sheet-handle" aria-hidden="true" />
            <div className="specialist-metrics-sheet-heading">
              <h2 id="specialist-metrics-sheet-title">جزئیات تخصصی {dayLabel}</h2>
              <button
                ref={closeButtonRef}
                className="specialist-metrics-sheet-close"
                type="button"
                aria-label="بستن جزئیات تخصصی"
                onClick={() => setIsOpen(false)}
              >
                ×
              </button>
            </div>
            <div className="specialist-metrics-sheet-grid">
              {metrics.map((metric) => (
                <MetricTile key={metric.label} metric={metric} />
              ))}
            </div>
          </section>
        </div>
      ) : null}
    </>
  );
}
