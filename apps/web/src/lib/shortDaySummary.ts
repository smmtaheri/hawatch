import type { WeatherWarning } from "../types";

const rank = { normal: 0, change: 1, critical: 2 };
const labels: Record<string, string> = {
  cold: "سرمای شدید",
  heat: "گرمای شدید",
  lightning: "رعدوبرق",
  freezing_rain: "بارش یخ‌زن",
  visibility: "دید کم",
  snow_wind_visibility: "کولاک",
  wet_cold: "بارش سرد",
  rain: "بارش سنگین",
  snow: "برف سنگین",
};

/** Up to three words after the day label, with one dominant warning only. */
export function shortDaySummary(condition: string, warnings: WeatherWarning[] = []): string {
  const dominant = warnings.reduce<WeatherWarning | undefined>((best, warning) =>
    !best || rank[warning.severity] > rank[best.severity] ? warning : best, undefined);
  if (!dominant) return condition;
  const label = dominant.code === "wind"
    ? dominant.severity === "critical" ? "باد شدید" : "تندباد"
    : labels[dominant.code] ?? "هوای نامساعد";
  if (condition.includes(label)) return label;
  const combined = `${condition}، ${label}`;
  return combined.trim().split(/\s+/).length <= 3 ? combined : label;
}
