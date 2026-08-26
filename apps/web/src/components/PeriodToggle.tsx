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
      <button
        className={value === "morning" ? "selected" : ""}
        type="button"
        aria-pressed={value === "morning"}
        onClick={() => onChange("morning")}
      >
        <strong>صبح</strong>
        <small>۰۰ تا ۱۲</small>
      </button>
      <button
        className={value === "afternoon" ? "selected" : ""}
        type="button"
        aria-pressed={value === "afternoon"}
        onClick={() => onChange("afternoon")}
      >
        <strong>بعدازظهر</strong>
        <small>۱۲ تا ۲۴</small>
      </button>
    </div>
  );
}
