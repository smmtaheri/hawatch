import { useEffect, useRef, useState } from "react";
import type { RouteForecast } from "../types";
import { renderSummaryPng } from "../lib/shareImage";
import { buildRouteShareUrl } from "../lib/routeShare";
import { Dialog } from "./Dialog";
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

export function ShareCard({ forecast }: { forecast: RouteForecast }) {
  const ref = useRef<HTMLElement>(null);
  const generation = useRef(0);
  const [share, setShare] = useState<{
    file: File | null;
    preview: string;
    error: string;
  } | null>(null);
  const [message, setMessage] = useState("");
  const decision = forecast.decision;
  const pending = Boolean(forecast.timing_pending ?? decision.timing_pending);
  const incomplete = forecast.points.some((point) => !point.weather_available);
  const shareUrl = buildRouteShareUrl(
    forecast,
    import.meta.env.VITE_PUBLIC_SITE_ORIGIN || window.location.origin,
  );
  const shareMessage = `خلاصهٔ مسیر ${forecast.route.title} در هواچ`;
  useEffect(
    () => () => {
      generation.current++;
    },
    [],
  );
  useEffect(() => {
    const preview = share?.preview;
    return () => {
      if (preview) URL.revokeObjectURL(preview);
    };
  }, [share?.preview]);
  async function prepare() {
    if (!ref.current) return;
    const revision = ++generation.current;
    setMessage("");
    setShare({ file: null, preview: "", error: "" });
    try {
      const file = await renderSummaryPng(
        ref.current,
        forecast.route.title,
        forecast.meta.selected_date,
        `hawatch-${forecast.route.slug}-${forecast.meta.selected_date}-${forecast.start_minutes}-${forecast.speed}.png`,
        shareUrl,
      );
      if (revision !== generation.current) return;
      setShare({ file, preview: URL.createObjectURL(file), error: "" });
    } catch (error) {
      if (revision === generation.current)
        setShare({
          file: null,
          preview: "",
          error:
            error instanceof Error ? error.message : "ساخت تصویر ناموفق بود.",
        });
    }
  }
  function close() {
    generation.current++;
    setShare(null);
  }
  async function nativeShare() {
    if (!share?.file) return;
    const fileShare = navigator.canShare?.({ files: [share.file] });
    try {
      if (fileShare) {
        await navigator.share({
          files: [share.file],
          title: forecast.route.title,
          text: shareMessage,
          url: shareUrl,
        });
      } else {
        await navigator.share({
          title: forecast.route.title,
          text: `${shareMessage}\n${shareUrl}`,
        });
      }
    } catch (error) {
      if (!(error instanceof DOMException && error.name === "AbortError"))
        setMessage("ارسال تصویر انجام نشد؛ می‌توانید تصویر را ذخیره کنید.");
    }
  }
  return (
    <>
      <aside
        ref={ref}
        className={`trip-summary share-state-${decision.state}`}
        aria-labelledby="trip-summary-title"
      >
        <h2 id="trip-summary-title">خلاصهٔ مسیر</h2>
        <div className="trip-facts">
          <div className="trip-fact">
            <small>شروع حرکت</small>
            <strong>{decision.start}</strong>
          </div>
          <div className="trip-fact">
            <small>رسیدن به نقطه</small>
            <strong>{pending ? "نامشخص" : decision.finish}</strong>
          </div>
          <div className="trip-fact">
            <small>سرعت حرکت</small>
            <strong>{decision.speed}</strong>
          </div>
          <div className="trip-fact">
            <small>طول مسیر</small>
            <strong>
              {forecast.route.distance_label.replace(/km/g, "کیلومتر")}
            </strong>
          </div>
        </div>
        {pending ? (
          <p className="timing-pending-notice" role="status">
            زمان‌بندی دقیق مسیر هنوز نهایی نشده است؛ زمان رسیدن به نقاط فعلاً در
            دسترس نیست.
          </p>
        ) : null}
        {incomplete ? (
          <p className="forecast-data-notice" role="status">
            پیش‌بینی بعضی نقاط در زمان رسیدن در دسترس نیست؛ ارزیابی هوا کامل
            نیست.
          </p>
        ) : null}
        <p
          className={`trip-sentence ${decision.state === "critical" ? "risk-red" : decision.state === "change" ? "risk-yellow" : ""}`}
        >
          {decision.summary}
        </p>
        <h3 className="equipment-heading">تجهیزات پیشنهادی</h3>
        <div className="equipment">
          {decision.gear?.map((item) => (
            <span key={item}>{GEAR_LABELS[item] ?? item}</span>
          ))}
        </div>
        <div className="share-actions">
          <button type="button" onClick={() => void prepare()}>
            <span className="share-action-label share-action-label-mobile">
              اشتراک‌گذاری
            </span>
            <span className="share-action-label share-action-label-desktop">
              ذخیرهٔ عکس
            </span>
          </button>
        </div>
      </aside>
      {share ? (
        <Dialog
          title="اشتراک‌گذاری خلاصهٔ مسیر"
          className="share-dialog"
          onClose={close}
        >
          {share.preview ? (
            <img
              className="share-preview"
              src={share.preview}
              alt="تصویر خلاصهٔ برنامهٔ انتخاب‌شده"
            />
          ) : (
            <p role="status">{share.error || "در حال ساخت تصویر…"}</p>
          )}
          {share.file ? (
            <div className="share-dialog-actions">
              {typeof navigator.share === "function" &&
              window.matchMedia?.("(max-width: 767px)").matches ? (
                <button
                  type="button"
                  className="primary-button"
                  onClick={() => void nativeShare()}
                >
                  ارسال تصویر
                </button>
              ) : (
                <a
                  className="outline-button"
                  href={share.preview}
                  download={share.file.name}
                >
                  ذخیرهٔ عکس
                </a>
              )}
            </div>
          ) : null}
          {message ? (
            <p className="share-status" role="status">
              {message}
            </p>
          ) : null}
        </Dialog>
      ) : null}
    </>
  );
}
