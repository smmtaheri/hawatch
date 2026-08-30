import { useState } from "react";
import type { RouteForecast } from "../types";
import { buildRouteShareUrl, buildRouteTelegramShareUrl } from "../lib/routeShare";

export function ShareCard({ forecast }: { forecast: RouteForecast }) {
  const decision = forecast.decision;
  const timingPending = Boolean(forecast.timing_pending ?? decision.timing_pending);
  const [copyState, setCopyState] = useState<"idle" | "copied" | "failed">("idle");
  const shareUrl = buildRouteShareUrl(forecast);

  async function copyLink() {
    try {
      await navigator.clipboard.writeText(shareUrl);
      setCopyState("copied");
    } catch {
      setCopyState("failed");
    }
    window.setTimeout(() => setCopyState("idle"), 2400);
  }

  const telegram = buildRouteTelegramShareUrl(forecast);

  return (
    <section className={`route-decision route-forecast route-share-card share-state-${decision.state}`}>
      <div className="share-card-heading">
        <div>
          <span className="decision-chip">{decision.chip}</span>
        </div>
        <span className="share-status-badge">
          <i aria-hidden="true" />
          {decision.status}
        </span>
      </div>
      {timingPending ? (
        <div className="timing-pending-notice" role="status">
          زمان‌بندی دقیق مسیر هنوز نهایی نشده است؛ زمان رسیدن به نقاط فعلاً در دسترس نیست.
        </div>
      ) : null}
      <div className="share-summary">
        <div>
          <span>شروع حرکت</span>
          <strong>{decision.start}</strong>
        </div>
        <div>
          <span>رسیدن به مقصد</span>
          <strong>{timingPending ? "نامشخص" : decision.finish}</strong>
        </div>
        <div>
          <span>سرعت</span>
          <strong>{decision.speed}</strong>
        </div>
        <div>
          <span>نقطهٔ حساس</span>
          <strong>{decision.critical_name || "—"}</strong>
        </div>
      </div>
      <div className="share-summary-copy">
        <strong>{decision.summary}</strong>
        {!timingPending && decision.critical_time && decision.critical_time !== "—" ? (
          <span>
            {decision.critical_time}
            {decision.critical_note ? ` · ${decision.critical_note}` : ""}
          </span>
        ) : null}
      </div>
      <div className="share-recommendations">
        <span className="share-section-label">پیشنهادهای این برنامه</span>
        <ul>
          {decision.recommendations.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </div>
      <div className="share-actions">
        <button className="share-copy-button" type="button" onClick={copyLink}>
          {copyState === "copied" ? "لینک کپی شد ✓" : copyState === "failed" ? "کپی ناموفق بود" : "کپی لینک برنامه"}
        </button>
        <a className="share-telegram-button" href={telegram} target="_blank" rel="noopener noreferrer">
          ارسال در تلگرام <span aria-hidden="true">↗</span>
        </a>
      </div>
    </section>
  );
}
