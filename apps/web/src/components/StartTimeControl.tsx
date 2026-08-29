import { periodLastStartMinutes } from "../lib/periods";
import type { PeriodId } from "../types";

export function StartTimeControl({
  minutes,
  min,
  max,
  period,
  ticks,
  rangeLabel,
  display,
  currentMinutes,
  onChange,
  onCommit,
}: {
  minutes: number;
  min: number;
  max: number;
  period?: PeriodId;
  ticks: string[];
  rangeLabel: string;
  display: string;
  currentMinutes?: number;
  onChange: (value: number) => void;
  onCommit: (value: number) => void;
}) {
  const sliderMax = period ? periodLastStartMinutes(period) : max;
  const boundedMinutes = Math.max(min, Math.min(sliderMax, minutes));
  const percent = ((boundedMinutes - min) / Math.max(1, sliderMax - min)) * 100;
  const boundedCurrentMinutes =
    currentMinutes === undefined ? undefined : Math.max(min, Math.min(sliderMax, currentMinutes));
  const elapsedPercent =
    boundedCurrentMinutes !== undefined
      ? ((boundedCurrentMinutes - min) / Math.max(1, sliderMax - min)) * 100
      : undefined;

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
          {elapsedPercent !== undefined ? (
            <span
              className="gauge-elapsed"
              style={{ width: `${Math.max(0, Math.min(100, elapsedPercent))}%` }}
            />
          ) : null}
          <span className="gauge-fill" style={{ width: `${percent}%` }} />
          <span className="gauge-dot" style={{ left: `${percent}%` }} />
        </div>
        <input
          aria-label="ساعت شروع حرکت"
          type="range"
          min={min}
          max={sliderMax}
          step={30}
          value={boundedMinutes}
          onChange={(event) => onChange(Number(event.target.value))}
          onPointerUp={(event) => onCommit(Number((event.target as HTMLInputElement).value))}
          onTouchEnd={(event) => onCommit(Number((event.target as HTMLInputElement).value))}
          onKeyUp={(event) => {
            if (event.key === "Enter" || event.key === " ") {
              onCommit(Number((event.target as HTMLInputElement).value));
            }
          }}
          onBlur={(event) => onCommit(Number(event.target.value))}
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
