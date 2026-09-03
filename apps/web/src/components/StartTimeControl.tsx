import { resolvePlannerBounds } from "../lib/periods";
import type { PeriodId, PlannerPeriodInfo } from "../types";

export function StartTimeControl({
  minutes,
  min,
  max,
  period,
  apiPeriod,
  ticks,
  rangeLabel,
  display,
  currentMinutes,
  stepMinutes,
  onChange,
  onCommit,
}: {
  minutes: number;
  min: number;
  max: number;
  period?: PeriodId;
  apiPeriod?: PlannerPeriodInfo | null;
  ticks: string[];
  rangeLabel: string;
  display: string;
  currentMinutes?: number;
  stepMinutes?: number;
  onChange: (value: number) => void;
  onCommit: (value: number) => void;
}) {
  const bounds = period ? resolvePlannerBounds(period, apiPeriod) : null;
  const sliderMax = bounds?.lastStart ?? max;
  const sliderMin = bounds?.min ?? min;
  const step = stepMinutes ?? bounds?.stepMinutes ?? 60;
  const boundedMinutes = Math.max(sliderMin, Math.min(sliderMax, minutes));
  const span = Math.max(1, sliderMax - sliderMin);
  const percent = ((boundedMinutes - sliderMin) / span) * 100;
  const boundedCurrentMinutes =
    currentMinutes === undefined ? undefined : Math.max(sliderMin, Math.min(sliderMax, currentMinutes));
  const elapsedPercent =
    boundedCurrentMinutes !== undefined
      ? ((boundedCurrentMinutes - sliderMin) / span) * 100
      : undefined;

  return (
    <div className="time-gauge">
      <div className="gauge-heading">
        <div>
          <span className="planner-label">ساعت شروع</span>
          <small>از {rangeLabel}</small>
        </div>
        <strong><bdi>{display}</bdi></strong>
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
          <span className="gauge-dot" style={{ right: `${percent}%` }} />
        </div>
        <input
          aria-label="ساعت شروع حرکت"
          type="range"
          min={sliderMin}
          max={sliderMax}
          step={step}
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
            <span key={tick}><bdi>{tick}</bdi></span>
          ))}
        </div>
      </div>
    </div>
  );
}
