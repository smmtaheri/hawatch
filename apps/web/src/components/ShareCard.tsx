import { useState } from "react";
import type { RouteForecast } from "../types";
import { GearIcon } from "./GearIcon";
import { buildRouteShareUrl, buildRouteTelegramShareUrl } from "../lib/routeShare";

const GEAR_LABELS: Record<string, string> = {
  "waterproof-shell": "کاپشن ضدآب",
  "insulated-jacket": "کاپشن گرم",
  "base-layer": "لایهٔ پایه",
  "hiking-boots": "کفش کوه",
  "trekking-poles": "باتوم",
  backpack: "کوله‌پشتی",
  gloves: "دستکش گرم",
  beanie: "کلاه گرم",
  sunglasses: "عینک آفتابی",
  headlamp: "هدلامپ",
  "water-bottle": "آب",
  "energy-snack": "خوراکی انرژی‌زا",
  sunscreen: "ضدآفتاب",
  "first-aid": "کمک‌های اولیه",
  "emergency-blanket": "پتوی نجات",
  compass: "نقشه و قطب‌نما",
  "power-bank": "پاوربانک",
  gaiters: "گتر",
  microspikes: "یخ‌شکن",
  whistle: "سوت نجات",
};

const DEFAULT_GEAR = ["hiking-boots", "backpack", "water-bottle"];

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
  const gear = decision.gear?.length ? decision.gear : DEFAULT_GEAR;

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
          <span>رسیدن به نقطه</span>
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
      </div>
      <div className="share-gear" aria-label="تجهیزات پیشنهادی">
        <span className="share-section-label">تجهیزات پیشنهادی</span>
        <ul>
          {gear.map((item) => (
            <li key={item}>
              <GearIcon name={item} size={30} title={GEAR_LABELS[item] ?? item} />
              <span>{GEAR_LABELS[item] ?? item}</span>
            </li>
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
