export function StartTimeControl({
  minutes,
  min,
  max,
  ticks,
  rangeLabel,
  display,
  onChange,
}: {
  minutes: number;
  min: number;
  max: number;
  ticks: string[];
  rangeLabel: string;
  display: string;
  onChange: (value: number) => void;
}) {
  const percent = ((minutes - min) / Math.max(1, max - min)) * 100;
  return (
    <div className="time-gauge">
      <div className="gauge-heading">
        <div>
          <span className="planner-label">ساعت شروع</span>
          <small>از {rangeLabel}</small>
        </div>
        <strong>{display}</strong>
      </div>
      <div className="gauge-wrap">
        <div className="gauge-line">
          <span className="gauge-fill" style={{ width: `${percent}%` }} />
          <span className="gauge-dot" style={{ right: `${percent}%` }} />
        </div>
        <input
          aria-label="ساعت شروع حرکت"
          type="range"
          min={min}
          max={max}
          step={30}
          value={minutes}
          onChange={(event) => onChange(Number(event.target.value))}
        />
        <div className="gauge-ticks">
          {ticks.map((tick) => (
            <span key={tick}>{tick}</span>
          ))}
        </div>
      </div>
    </div>
  );
}
