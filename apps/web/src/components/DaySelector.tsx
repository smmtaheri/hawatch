import type { DayInfo } from "../types";

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
