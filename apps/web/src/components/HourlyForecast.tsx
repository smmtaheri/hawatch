import { useId, useState } from "react";
import type { CSSProperties } from "react";
import type { HourlyReading } from "../types";
import { DesignIcon, WeatherIcon } from "./DesignIcon";
export function numberLabel(value: number | null | undefined, suffix = "") {
  return typeof value === "number" && Number.isFinite(value)
    ? `${value.toLocaleString("fa-IR")}${suffix}`
    : "نامشخص";
}

function isCriticalWind(hour: HourlyReading) {
  return hour.wind_alert?.severity === "critical";
}

export function HourlyForecast({
  hours,
  dayLabel = "",
}: {
  hours: HourlyReading[];
  dayLabel?: string;
}) {
  const id = useId();
  const [expanded, setExpanded] = useState<string | null>(null);
  const selected = hours.find(
    (hour) => (hour.forecast_at ?? hour.time) === expanded,
  );
  const selectedIndex = selected ? hours.indexOf(selected) : -1;
  const metrics: [string, number | null | undefined, string, boolean][] = selected
    ? [
        ["دمای حسی", selected.apparent_temperature_c, "°", false],
        ["باد", selected.wind_speed_kmh, " km/h", isCriticalWind(selected) && selected.wind_speed_kmh >= 30],
        ["تندباد", selected.wind_gust_kmh, " km/h", isCriticalWind(selected) && (selected.wind_gust_kmh ?? 0) >= 40],
        ["باران", selected.rain_mm, " mm", false],
        ["برف", selected.snowfall_cm, " cm", false],
        ["احتمال بارش", selected.precipitation_probability, "٪", false],
        ["دید افقی", selected.visibility_km, " km", false],
        ["تراز صفر درجه", selected.freezing_level_m, " m", false],
        ["پایهٔ ابر", selected.cloud_base_m, " m", false],
        ["تابش فرابنفش", selected.uv_index, "", false],
        ["پوشش ابر", selected.cloud_cover_pct, "٪", false],
      ]
    : [];
  return (
    <>
      <div className="hours hours-grid" aria-label="پیش‌بینی ساعتی">
        {hours.map((hour) => {
          const key = hour.forecast_at ?? hour.time;
          const open = expanded === key;
          const specialistHazard = hour.wind_alert?.severity === "critical";
          return (
            <article
              key={key}
              className={`hour-card hour-item ${hour.state} ${hour.is_past ? "past is-past" : ""} ${hour.is_current ? "is-current" : ""} ${hour.state === "critical" ? "severe" : ""} ${open ? "expanded" : ""}`}
            >
              {hour.state === "critical" ? (
                <DesignIcon name="warning" className="hazard" />
              ) : null}
              <div className="stamp">
                <time dateTime={hour.forecast_at} dir="ltr">
                  {hour.time}
                </time>
                {hour.is_current ? (
                  <span className="current-dot" aria-label="بازهٔ جاری" />
                ) : null}
              </div>
              <WeatherIcon
                code={hour.weather_code}
                at={hour.forecast_at}
                isDay={hour.is_day}
              />
              <div className="weather-label">{hour.condition}</div>
              <div className="degree">
                <bdi>{numberLabel(hour.apparent_temperature_c, "°")}</bdi>
              </div>
              <div className="wind-line">
                <span>باد</span>
                <bdi>{numberLabel(hour.wind_speed_kmh, " km/h")}</bdi>
                <DesignIcon name="wind" />
              </div>
              <button
                className={`details-trigger ${specialistHazard ? "risk-red" : ""}`}
                type="button"
                aria-expanded={open}
                aria-controls={id}
                onClick={() => setExpanded(open ? null : key)}
              >
                جزئیات تخصصی{" "}
                <DesignIcon name={open ? "chevron-up" : "chevron-down"} />
              </button>
            </article>
          );
        })}
      </div>
      {selected ? (
        <section
          className="detail-panel"
          id={id}
          style={
            { "--anchor": `${[83, 50, 17][selectedIndex]}%` } as CSSProperties
          }
        >
          <h2>
            جزئیات تخصصی <bdi dir="ltr">{selected.time}</bdi>
            <small>{dayLabel}</small>
          </h2>
          <div className="metrics">
            {metrics.map(([label, value, unit, alert]) => (
              <div className="metric" key={label}>
                <span className={alert ? "risk-red" : ""}>{label}</span>
                <strong className={alert ? "risk-red" : ""}>
                  <bdi>{numberLabel(value, unit)}</bdi>
                </strong>
              </div>
            ))}
          </div>
        </section>
      ) : null}
    </>
  );
}
