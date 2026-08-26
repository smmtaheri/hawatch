import { Link } from "react-router-dom";

export function BackNavigation({ to, label, ariaLabel }: { to: string; label?: string; ariaLabel: string }) {
  return (
    <Link className="mobile-back-link" to={to} aria-label={ariaLabel}>
      ← {label ?? "بازگشت"}
    </Link>
  );
}
