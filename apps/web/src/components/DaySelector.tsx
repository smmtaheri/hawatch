import { useEffect, useRef, useState } from "react";
import type { DayInfo, PeriodId } from "../types";
import type { PeriodPhase } from "../lib/periodState";
import { PeriodToggle } from "./PeriodToggle";
import { DesignIcon } from "./DesignIcon";
export function DayPickerHeading() {
  return <span className="sr-only">انتخاب روز</span>;
}
export function PeriodControlRow({
  period,
  onChange,
  periodStates,
}: {
  period: PeriodId;
  onChange: (period: PeriodId) => void;
  periodStates?: Partial<Record<PeriodId, PeriodPhase>>;
  label?: string;
  className?: string;
}) {
  return (
    <PeriodToggle
      value={period}
      onChange={onChange}
      periodStates={periodStates}
    />
  );
}
export function ForecastDayPeriodControls({
  days,
  selectedDate,
  onSelectDate,
  period,
  onSelectPeriod,
  periodStates,
  onLockedDate,
}: {
  days: DayInfo[];
  selectedDate: string;
  onSelectDate: (date: string) => void;
  period: PeriodId;
  onSelectPeriod: (period: PeriodId) => void;
  periodStates?: Partial<Record<PeriodId, PeriodPhase>>;
  dayClassName?: string;
  periodLabel?: string;
  onLockedDate?: (day: DayInfo) => void;
}) {
  return (
    <div className="selector-stack">
      <DaySelector
        days={days}
        selected={selectedDate}
        onSelect={onSelectDate}
        onLocked={onLockedDate}
      />
      <PeriodControlRow
        period={period}
        onChange={onSelectPeriod}
        periodStates={periodStates}
      />
    </div>
  );
}
export function DaySelector({
  days,
  selected,
  onSelect,
  onLocked,
  className = "",
}: {
  days: DayInfo[];
  selected: string;
  onSelect: (date: string) => void;
  onLocked?: (day: DayInfo) => void;
  className?: string;
}) {
  const scroller = useRef<HTMLDivElement>(null);
  const [overflow, setOverflow] = useState(false);
  const [progress, setProgress] = useState(0);
  function measure() {
    const el = scroller.current;
    if (!el) return;
    const max = el.scrollWidth - el.clientWidth;
    setOverflow(max > 2);
    setProgress(max > 0 ? (Math.abs(el.scrollLeft) / max) * 163 : 0);
  }
  useEffect(() => {
    measure();
    const el = scroller.current;
    if (!el) return;
    const observer =
      typeof ResizeObserver !== "undefined"
        ? new ResizeObserver(measure)
        : null;
    observer?.observe(el);
    window.addEventListener("resize", measure);
    return () => {
      observer?.disconnect();
      window.removeEventListener("resize", measure);
    };
  }, [days]);
  function scroll(direction: number) {
    const el = scroller.current;
    el?.scrollBy?.({
      left: direction * el.clientWidth,
      behavior: window.matchMedia?.("(prefers-reduced-motion: reduce)").matches
        ? "auto"
        : "smooth",
    });
  }
  return (
    <div className="date-shell">
      <div
        ref={scroller}
        className={`days day-tabs ${className}`}
        role="tablist"
        aria-label="انتخاب روز"
        onScroll={measure}
      >
        {days.map((day) => (
          <button
            key={day.date}
            type="button"
            role="tab"
            aria-selected={selected === day.date}
            className={`day ${selected === day.date ? "selected" : ""} ${day.is_past && selected !== day.date ? "past" : ""} ${day.access && day.access !== "available" ? "locked" : ""}`}
            aria-label={
              day.access === "login_required"
                ? `${day.label}، ورود`
                : day.access === "plan_required"
                  ? `${day.label}، خرید اشتراک`
                  : undefined
            }
            onClick={() =>
              day.access && day.access !== "available"
                ? onLocked?.(day)
                : onSelect(day.date)
            }
          >
            {day.access && day.access !== "available" ? (
              <DesignIcon name="lock" className="lock" />
            ) : null}
            <strong className="day-title">{day.label}</strong>
            <span>{day.jalali}</span>
          </button>
        ))}
      </div>
      {overflow ? (
        <>
          <button
            type="button"
            className="carousel-arrow carousel-prev"
            aria-label="روزهای قبلی"
            onClick={() => scroll(1)}
          >
            <DesignIcon name="chevron-right" />
          </button>
          <button
            type="button"
            className="carousel-arrow carousel-next"
            aria-label="روزهای بعدی"
            onClick={() => scroll(-1)}
          >
            <DesignIcon name="chevron-left" />
          </button>
          <div className="scroll-cue" aria-hidden="true">
            <span style={{ transform: `translateX(${progress}%)` }} />
          </div>
        </>
      ) : null}
    </div>
  );
}
