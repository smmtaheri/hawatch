export function SpeedControl({
  value,
  options,
  onChange,
}: {
  value: string;
  options: string[];
  onChange: (speed: string) => void;
}) {
  return (
    <div className="planner-speed">
      <span className="planner-label">سرعت حرکت</span>
      <div className="segmented-control">
        {options.map((option) => (
          <button
            key={option}
            className={value === option ? "selected" : ""}
            type="button"
            aria-pressed={value === option}
            onClick={() => onChange(option)}
          >
            {option}
          </button>
        ))}
      </div>
      <small>زمان رسیدن همهٔ نقاط با این انتخاب تغییر می‌کند.</small>
    </div>
  );
}
