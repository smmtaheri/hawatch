import { useId, useState } from "react";
import type { CSSProperties } from "react";
import type { HourlyReading, Severity, WeatherWarning } from "../types";
import { DesignIcon, WeatherIcon } from "./DesignIcon";
export function numberLabel(value: number | null | undefined, suffix = "") {
  return typeof value === "number" && Number.isFinite(value)
    ? `${value.toLocaleString("fa-IR")}${suffix}`
    : "نامشخص";
}

export function warningClass(severity: Severity | undefined) {
  return severity === "critical" ? "risk-red" : severity === "change" ? "risk-yellow" : "";
}

export function metricSeverity(warnings: WeatherWarning[] = [], field?: string): Severity {
  const relevant = warnings.filter(w => field ? w.metrics.includes(field) : w.metrics.length > 0);
  return relevant.some(w => (field ? w.metric_severities?.[field] ?? w.severity : w.severity) === "critical") ? "critical" : relevant.length ? "change" : "normal";
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
  const metrics: [string, number | null | undefined, string, string][] = selected
    ? [
        ["دمای هوا", selected.temperature_c, "°", "temperature_c"],
        ["دمای حسی", selected.apparent_temperature_c, "°", "apparent_temperature_c"],
        ["سرمای باد", selected.wind_chill_c, "°", "wind_chill_c"],
        ["شاخص گرما", selected.heat_index_c, "°", "heat_index_c"],
        ["رطوبت نسبی", selected.relative_humidity_pct, "٪", "relative_humidity_pct"],
        ["باد", selected.wind_speed_kmh, " km/h", "wind_speed_kmh"],
        ["تندباد", selected.wind_gust_kmh, " km/h", "wind_gust_kmh"],
        ["بارش", selected.precipitation_mm, " mm", "precipitation_mm"],
        ["باران", selected.rain_mm, " mm", "rain_mm"],
        ["برف", selected.snowfall_cm, " cm", "snowfall_cm"],
        ["احتمال بارش", selected.precipitation_probability, "٪", "precipitation_probability"],
        ["دید افقی", selected.visibility_km, " km", "visibility_km"],
        ["تراز صفر درجه", selected.freezing_level_m, " m", "freezing_level_m"],
        ["پایهٔ ابر", selected.cloud_base_m, " m", "cloud_base_m"],
        ["تابش فرابنفش", selected.uv_index, "", "uv_index"],
        ["پوشش ابر", selected.cloud_cover_pct, "٪", "cloud_cover_pct"],
      ]
    : [];
  return (
    <>
      <div className="hours hours-grid" aria-label="پیش‌بینی ساعتی">
        {hours.map((hour) => {
          const key = hour.forecast_at ?? hour.time;
          const open = expanded === key;
          const specialistHazard = metricSeverity(hour.warnings);
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
                className={`details-trigger ${warningClass(specialistHazard)}`}
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
          <h2 className={warningClass(metricSeverity(selected.warnings))}>
            جزئیات تخصصی <bdi dir="ltr">{selected.time}</bdi>
            <small>{dayLabel}</small>
          </h2>
          {selected.data_quality === "partial" ? <p className="weather-data-note">اطلاعات ارزیابی این ساعت ناقص است.</p> : null}
          <div className="weather-warning-reasons">
            {selected.warnings?.map(warning => (
              <p key={warning.code} className={warningClass(warning.severity)}>{warning.label}: {warning.reason}</p>
            ))}
          </div>
          <div className="metrics">
            {metrics.map(([label, value, unit, field]) => (
              <div className="metric" key={label}>
                <span className={warningClass(metricSeverity(selected.warnings, field))}>{label}</span>
                <strong className={warningClass(metricSeverity(selected.warnings, field))}>
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
