import {
  SPECIALIST_METRIC_ICON_NAMES,
  type SpecialistMetricIconName,
} from "../types";

const SPRITE_URL = "/icons/specialist/hawatch-specialist-icons.svg";

function isSpecialistMetricIcon(value: string): value is SpecialistMetricIconName {
  return (SPECIALIST_METRIC_ICON_NAMES as readonly string[]).includes(value);
}

export function SpecialistMetricIcon({ icon, tone = "teal" }: { icon: string; tone?: string }) {
  if (!isSpecialistMetricIcon(icon)) {
    return (
      <span className="specialist-metric-icon specialist-metric-icon-fallback" aria-hidden="true">
        {icon}
      </span>
    );
  }

  return (
    <svg
      className={`specialist-metric-icon specialist-metric-icon--${tone || "teal"}`}
      viewBox="0 0 24 24"
      aria-hidden="true"
      focusable="false"
    >
      <use href={`${SPRITE_URL}#icon-${icon}`} />
    </svg>
  );
}
