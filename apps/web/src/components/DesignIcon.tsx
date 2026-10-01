import icons from "./designIcons.json";
import weatherMap from "../lib/weather-map.json";
import { tehranWallClock } from "../lib/tehranTime";

export function DesignIcon({
  name,
  className = "",
}: {
  name: string;
  className?: string;
}) {
  const paths = icons[name as keyof typeof icons] ?? icons.unknown;
  return (
    <svg
      viewBox={name.startsWith("category-") ? "0 0 32 32" : "0 0 64 64"}
      className={`${name.startsWith("category-") ? "" : "icon"} ${className}`}
      fill="none"
      stroke="currentColor"
      strokeWidth={name.startsWith("category-") ? 1.8 : 2.6}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
      dangerouslySetInnerHTML={{ __html: paths }}
    />
  );
}

export function WeatherIcon({
  code,
  at,
  isDay,
  className = "weather-icon",
}: {
  code?: string | number | null;
  at?: string | null;
  isDay?: boolean | null;
  className?: string;
}) {
  const entry = weatherMap[String(code) as keyof typeof weatherMap];
  const normalized: Record<string, string> = {
    clear: "clear",
    "clear-night": "clear",
    "mainly-clear": "mostly-clear",
    "partly-cloudy": "partly-cloudy",
    overcast: "cloudy",
    fog: "fog",
    drizzle: "drizzle",
    "freezing-drizzle": "freezing-rain",
    rain: "rain",
    "freezing-rain": "freezing-rain",
    snow: "snow",
    shower: "showers",
    thunder: "thunderstorm",
    gale: "gust",
    windy: "wind",
  };
  let name = entry?.icon ?? normalized[String(code)] ?? "unknown";
  // ForecastRecord currently has no provider is_day column. Use its forecast
  // time in Tehran as the existing normalizer does; theme never selects night.
  const hour = at ? tehranWallClock(at).hour : null;
  const day = isDay ?? (hour !== null ? hour >= 6 && hour < 18 : null);
  if (["clear", "mostly-clear", "partly-cloudy", "fog"].includes(name)) {
    name = day === null ? "unknown" : `${name}-${day ? "day" : "night"}`;
  } else if (name === "showers" && day === false) name = "showers-night";
  return <DesignIcon name={name} className={className} />;
}

export function CategoryIcon({
  category,
  placeType,
}: {
  category?: string;
  placeType?: string;
}) {
  const mapping: Record<string, string> = {
    peak: "mountain",
    mountain: "mountain",
    alpine: "mountain",
    forest: "forest",
    lake: "lake",
    desert: "desert",
    waterfall: "waterfall",
    village: "village",
    city: "city",
    meadow: "plain",
    ski_resort: "ski",
    beach: "coast",
    neighborhood: "neighborhood",
    park: "park",
    volcano: "volcano",
  };
  const name =
    mapping[placeType || ""] ||
    (icons[`category-${placeType}` as keyof typeof icons]
      ? placeType
      : undefined) ||
    mapping[category || ""] ||
    "landmark";
  return <DesignIcon name={`category-${name}`} className="category-icon" />;
}
