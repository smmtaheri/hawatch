import { Link } from "react-router-dom";
import type { RouteSummary } from "../types";

function toFaDigits(value: number | string) {
  return String(value).replace(/\d/g, (digit) => "۰۱۲۳۴۵۶۷۸۹"[Number(digit)]);
}

function metricLabel(label: string | null | undefined, value: number | null, unit: string) {
  const normalized = label?.trim() ?? "";
  if (normalized && /[0-9۰-۹]/.test(normalized)) return label!;
  if (value == null) return "—";
  const formatted = Number.isInteger(value) ? String(value) : value.toFixed(1);
  return `${toFaDigits(formatted)} ${unit}`;
}

export function PointCard({
  route,
  role,
  onNavigate,
}: {
  route: RouteSummary;
  role?: "menuitem";
  onNavigate?: () => void;
}) {
  const ascentLabel = metricLabel(route.ascent_label, route.ascent_m, "m");
  const distanceLabel = metricLabel(route.distance_label, route.distance_km, "km");

  return (
    <Link to={route.href} className="route-card" role={role} onClick={onNavigate}>
      <span className="route-icon">⌁</span>
      <span className="route-copy">
        <h3>{route.title}</h3>
        <small className="route-details">
          <span className="route-detail">ارتفاع‌گیری: {ascentLabel}</span>
          <span className="route-detail">مسافت: {distanceLabel}</span>
        </small>
      </span>
      <span className="compact-route-arrow">←</span>
    </Link>
  );
}
