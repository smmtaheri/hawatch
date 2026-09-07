import type { DayInfo, PeriodId } from "../types";
import type { PeriodPhase } from "../lib/periodState";
import { PeriodToggle } from "./PeriodToggle";

export function DayPickerHeading() {
  return (
    <div className="forecast-day-heading">
      <span className="planner-label">انتخاب روز</span>
    </div>
  );
}

export function PeriodControlRow({
  period,
  onChange,
  periodStates,
  label = "بازهٔ نمایش هوا",
  className = "point-period-row",
}: {
  period: PeriodId;
  onChange: (period: PeriodId) => void;
  periodStates?: Partial<Record<PeriodId, PeriodPhase>>;
  label?: string;
  className?: string;
}) {
  return (
    <div className={`period-control-row ${className}`.trim()}>
      <span className="planner-label">{label}</span>
      <PeriodToggle value={period} onChange={onChange} periodStates={periodStates} />
    </div>
  );
}

export function ForecastDayPeriodControls({
  days,
  selectedDate,
  onSelectDate,
  period,
  onSelectPeriod,
  periodStates,
  dayClassName = "",
  periodLabel = "بازهٔ نمایش هوا",
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
    <div className="forecast-day-period-controls">
      <DayPickerHeading />
      <DaySelector days={days} selected={selectedDate} onSelect={onSelectDate} onLocked={onLockedDate} className={dayClassName} />
      <PeriodControlRow
        period={period}
        onChange={onSelectPeriod}
        periodStates={periodStates}
        label={periodLabel}
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
  return (
    <div className={`day-tabs ${className}`.trim()} role="tablist">
      {days.map((day) => (
        <button
          key={day.date}
          className={[
            selected === day.date ? "selected" : "",
            day.is_yesterday && selected !== day.date ? "is-yesterday past-day" : "",
            day.is_past && !day.is_today && selected !== day.date ? "is-past past-day" : "",
            day.access && day.access !== "available" ? "is-locked" : "",
          ]
            .filter(Boolean)
            .join(" ")}
          type="button"
          role="tab"
          aria-selected={selected === day.date}
          aria-label={day.access === "login_required" ? `${day.label}، ورود` : day.access === "plan_required" ? `${day.label}، خرید اشتراک` : undefined}
          onClick={() => (day.access && day.access !== "available" ? onLocked?.(day) : onSelect(day.date))}
        >
          <span className="day-tab-copy">
            <strong>{day.label}</strong>
            <span className="day-tab-date">{day.jalali}</span>
          </span>
          {day.access && day.access !== "available" ? (
            <span className="day-lock-badge" aria-hidden="true">
              <svg
                className="day-lock-symbol"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth="1.5"
                focusable="false"
              >
                <rect x="3.75" y="10.75" width="16.5" height="11.5" rx="2" />
                <path d="M7.5 10.75V7.5a4.5 4.5 0 0 1 9 0v3.25" />
              </svg>
            </span>
          ) : null}
        </button>
      ))}
    </div>
  );
}
