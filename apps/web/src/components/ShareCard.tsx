import { useState } from "react";
import type { RouteForecast } from "../types";

export function ShareCard({ forecast }: { forecast: RouteForecast }) {
  const decision = forecast.decision;
  const [copyState, setCopyState] = useState<"idle" | "copied" | "failed">("idle");

  async function copyLink() {
    const url = new URL(window.location.href);
    url.searchParams.set("date", forecast.meta.selected_date);
    url.searchParams.set("period", String(forecast.period.id));
    url.searchParams.set("start_time", forecast.start_time);
    url.searchParams.set("speed", forecast.speed);
    try {
      await navigator.clipboard.writeText(url.toString());
      setCopyState("copied");
    } catch {
      setCopyState("failed");
    }
    window.setTimeout(() => setCopyState("idle"), 2400);
  }

  const telegram = `https://t.me/share/url?url=${encodeURIComponent(window.location.href)}&text=${encodeURIComponent(`خلاصهٔ برنامهٔ ${forecast.route.title} در هواچ · ${decision.status}`)}`;

  return (
    <section className={`route-decision route-forecast route-share-card share-state-${decision.state}`}>
      <div className="share-card-heading">
        <div>
          <span className="decision-chip">{decision.chip}</span>
          <h2>{decision.title}</h2>
          <p>{decision.hero_status}</p>
        </div>
        <span className="share-status-badge">
          <i aria-hidden="true" />
          {decision.status}
        </span>
      </div>
      <div className="share-summary">
        <div>
          <span>شروع حرکت</span>
          <strong>{decision.start}</strong>
        </div>
        <div>
          <span>رسیدن به مقصد</span>
          <strong>{decision.finish}</strong>
        </div>
        <div>
          <span>سرعت</span>
          <strong>{decision.speed}</strong>
        </div>
        <div>
          <span>نقطهٔ حساس</span>
          <strong>{decision.critical_name}</strong>
        </div>
      </div>
      <div className="share-summary-copy">
        <strong>{decision.summary}</strong>
        <span>
          {decision.critical_time} · {decision.critical_note}
        </span>
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
