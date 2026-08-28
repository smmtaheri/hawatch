import { PERIOD_OPTIONS } from "../lib/periods";
import type { PeriodPhase } from "../lib/periodState";
import type { PeriodId } from "../types";

export function PeriodToggle({
  value,
  onChange,
  periodStates,
}: {
  value: PeriodId;
  onChange: (period: PeriodId) => void;
  periodStates?: Partial<Record<PeriodId, PeriodPhase>>;
}) {
  return (
    <div className="daypart-toggle" role="group" aria-label="انتخاب بازهٔ زمانی">
      {PERIOD_OPTIONS.map((option) => {
        const phase = periodStates?.[option.id];
        const isSelected = value === option.id;
        return (
          <button
            key={option.id}
            className={[
              isSelected ? "selected" : "",
              phase === "past" && !isSelected ? "past-period" : "",
              phase === "current" ? "current-period" : "",
              phase === "future" ? "future-period" : "",
            ]
              .filter(Boolean)
              .join(" ")}
            type="button"
            aria-pressed={isSelected}
            onClick={() => onChange(option.id)}
          >
            <strong>{option.label}</strong>
            <small>{option.rangeLabel}</small>
          </button>
        );
      })}
    </div>
  );
}
