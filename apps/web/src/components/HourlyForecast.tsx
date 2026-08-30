import { useEffect, useRef } from "react";
import type { CSSProperties } from "react";

import type { HourlyReading } from "../types";

/** Hourly cards + severity legend. Period `headline` is API-only and not shown. */
export function HourlyForecast({ hours }: { hours: HourlyReading[] }) {
  const gridRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const grid = gridRef.current;
    if (!grid || !hours.length || typeof window === "undefined") return;

    const isMobile =
      typeof window.matchMedia === "function"
        ? window.matchMedia("(max-width: 720px)").matches
        : window.innerWidth <= 720;
    if (!isMobile) return;

    const target =
      grid.querySelector<HTMLElement>(".hour-item.is-current") ?? grid.querySelector<HTMLElement>(".hour-item");
    if (!target || typeof target.scrollIntoView !== "function") return;

    const reduceMotion =
      typeof window.matchMedia === "function" && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const frame = window.requestAnimationFrame(() => {
      target.scrollIntoView({
        behavior: reduceMotion ? "auto" : "smooth",
        block: "nearest",
        inline: "center",
      });
    });

    return () => window.cancelAnimationFrame(frame);
  }, [hours]);

  return (
    <div className="hourly-box">
      <div className="hourly-head">
        <div className="legend">
          <span>
            <i className="legend-dot teal-dot" />
            عادی
          </span>
          <span>
            <i className="legend-dot amber-dot" />
            تغییر مهم
          </span>
          <span>
            <i className="legend-dot coral-dot" />
            نقطه حساس
          </span>
        </div>
      </div>
      <div ref={gridRef} className="hours-grid" style={{ "--hour-count": Math.max(hours.length, 1) } as CSSProperties}>
        {hours.map((hour) => (
          <div
            key={hour.forecast_at ?? hour.time}
            className={`hour-item ${hour.state} ${hour.is_past ? "is-past" : ""} ${hour.is_current ? "is-current" : ""} ${hour.is_future ? "is-future" : ""}`}
          >
            <strong>{hour.time}</strong>
            <span className="weather-symbol">{hour.icon}</span>
            <span className="condition">{hour.condition}</span>
            <b>{hour.temperature_label}</b>
            <small>{hour.wind_label}</small>
            {hour.state !== "normal" ? <em>{hour.state === "critical" ? "احتیاط" : "تغییر مهم"}</em> : null}
          </div>
        ))}
      </div>
    </div>
  );
}
