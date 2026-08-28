import type { HourlyReading } from "../types";

export function HourlyForecast({
  hours,
  headline,
}: {
  hours: HourlyReading[];
  headline: string;
}) {
  return (
    <div className="hourly-box">
      <div className="hourly-head">
        <span>{headline}</span>
        <div className="legend">
          <span>
            <i className="legend-dot teal-dot" />
            عادی
          </span>
          <span>
            <i className="legend-dot amber-dot" />
            تغییر مهم
          </span>
          <span>
            <i className="legend-dot coral-dot" />
            نقطه حساس
          </span>
        </div>
      </div>
      <div className="hours-grid">
        {hours.map((hour) => (
          <div
            key={hour.forecast_at ?? hour.time}
            className={`hour-item ${hour.state} ${hour.is_past ? "is-past" : ""} ${hour.is_current ? "is-current" : ""}`}
          >
            <strong>{hour.time}</strong>
            <span className="weather-symbol">{hour.icon}</span>
            <span className="condition">{hour.condition}</span>
            <b>{hour.temperature_label}</b>
            <small>{hour.wind_label}</small>
            {hour.state !== "normal" ? <em>{hour.state === "critical" ? "احتیاط" : "تغییر مهم"}</em> : null}
          </div>
        ))}
      </div>
    </div>
  );
}
