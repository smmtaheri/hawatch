import { toClock } from "./periods";
import type { RouteForecast } from "../types";

/** Canonical share URL for a route forecast (ASCII start_time, planner params only). */
export function buildRouteShareUrl(forecast: RouteForecast, origin = window.location.origin): string {
  const url = new URL(forecast.route.href, origin);
  url.searchParams.set("date", forecast.meta.selected_date);
  url.searchParams.set("period", String(forecast.period.id));
  url.searchParams.set("start_time", toClock(forecast.start_minutes));
  url.searchParams.set("speed", forecast.speed);
  return url.toString();
}

export function buildRouteTelegramShareUrl(forecast: RouteForecast, origin = window.location.origin): string {
  const shareUrl = buildRouteShareUrl(forecast, origin);
  const text = `خلاصهٔ برنامهٔ ${forecast.route.title} در هواچ · ${forecast.decision.status}`;
  return `https://t.me/share/url?url=${encodeURIComponent(shareUrl)}&text=${encodeURIComponent(text)}`;
}
