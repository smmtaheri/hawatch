import type { PlaceForecastResponse, PlaceKind, PeriodId } from "../../types";
import { asPeriodId } from "../../lib/periods";

export type { PlaceKind };

export interface PlaceForecastViewModel {
  kind: PlaceKind;
  subject: PlaceForecastResponse["subject"];
  days: PlaceForecastResponse["forecast"]["days"];
  period: PlaceForecastResponse["forecast"]["period"];
  current: PlaceForecastResponse["forecast"]["current"];
  hourly: PlaceForecastResponse["forecast"]["hourly"];
  metrics: PlaceForecastResponse["metrics"];
  hero: PlaceForecastResponse["hero"];
  decision: PlaceForecastResponse["decision"];
  related_routes: PlaceForecastResponse["related_routes"];
  related_routes_title: string;
  empty: boolean;
  partial: boolean;
  meta: PlaceForecastResponse["forecast"]["meta"];
  destinationSlug?: string;
}

/** Normalize destination or point place responses onto one view model. */
export function adaptPlaceForecast(payload: PlaceForecastResponse): PlaceForecastViewModel {
  const subject = payload.subject;
  const forecast = payload.forecast;
  const kind = subject.kind;
  const relatedRoutes =
    payload.related_routes ??
    payload.destination?.routes ??
    [];
  const title =
    payload.related_routes_title ??
    (kind === "destination"
      ? `مسیرهای منتهی به ${subject.name}`
      : "مسیرهای عبوری از این نقطه");

  return {
    kind,
    subject,
    days: forecast.days,
    period: forecast.period,
    current: forecast.current,
    hourly: forecast.hourly,
    metrics: payload.metrics ?? [],
    hero: {
      status: payload.hero.status,
      alert: payload.hero.alert ?? "✓　شرایط فعلاً آرام‌تر است",
    },
    decision: payload.decision,
    related_routes: relatedRoutes,
    related_routes_title: title,
    empty: payload.empty,
    partial: Boolean(payload.partial),
    meta: forecast.meta,
    destinationSlug: kind === "destination" ? subject.slug : undefined,
  };
}

export function asSelectedPeriod(value: string | undefined | null): PeriodId | undefined {
  return asPeriodId(value);
}
