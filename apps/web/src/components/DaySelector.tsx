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
}: {
  days: DayInfo[];
  selectedDate: string;
  onSelectDate: (date: string) => void;
  period: PeriodId;
  onSelectPeriod: (period: PeriodId) => void;
  periodStates?: Partial<Record<PeriodId, PeriodPhase>>;
  dayClassName?: string;
  periodLabel?: string;
}) {
  return (
    <div className="forecast-day-period-controls">
      <DayPickerHeading />
      <DaySelector days={days} selected={selectedDate} onSelect={onSelectDate} className={dayClassName} />
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
  className = "",
}: {
  days: DayInfo[];
  selected: string;
  onSelect: (date: string) => void;
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
          ]
            .filter(Boolean)
            .join(" ")}
          type="button"
          role="tab"
          aria-selected={selected === day.date}
          onClick={() => onSelect(day.date)}
        >
          <strong>{day.label}</strong>
          <span>{day.jalali}</span>
        </button>
      ))}
    </div>
  );
}
