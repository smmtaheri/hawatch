import { PERIOD_OPTIONS } from "../lib/periods";
import type { PeriodId } from "../types";

export function PeriodToggle({
  value,
  onChange,
}: {
  value: PeriodId;
  onChange: (period: PeriodId) => void;
}) {
  return (
    <div className="daypart-toggle" role="group" aria-label="انتخاب بازهٔ زمانی">
      {PERIOD_OPTIONS.map((option) => (
        <button
          key={option.id}
          className={value === option.id ? "selected" : ""}
          type="button"
          aria-pressed={value === option.id}
          onClick={() => onChange(option.id)}
        >
          <strong>{option.label}</strong>
          <small>{option.rangeLabel}</small>
        </button>
      ))}
    </div>
  );
}
