import { useEffect, useMemo, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { api } from "../../api/client";
import { BackNavigation } from "../../components/BackNavigation";
import { Header } from "../../components/Header";
import { LoadingState } from "../../components/LoadingState";
import { usePageTitle } from "../../lib/pageTitle";
import type { ForecastPlanSummary } from "../../types";
import { useAuth } from "./authSession";

function faDigits(value: number) {
  return String(value).replace(/\d/g, (digit) => "۰۱۲۳۴۵۶۷۸۹"[Number(digit)]);
}

function accessLabel(plan: ForecastPlanSummary | undefined) {
  if (!plan) return "دسترسی پیش‌بینی پس از ورود فعال می‌شود";
  const futureDays = Math.max(0, plan.visible_days_from_yesterday - 1);
  if (futureDays === 0) return "دسترسی تا امروز";
  return `دسترسی تا ${faDigits(futureDays)} روز آینده`;
}

function safeReturnTo(value: string | null) {
  if (!value || !value.startsWith("/") || value.startsWith("//") || value.startsWith("/login")) return "/";
  return value;
}

export function SubscriptionPlansPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const { isAuthenticated, session } = useAuth();
  const [plans, setPlans] = useState<ForecastPlanSummary[]>([]);
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");
  const [message, setMessage] = useState("");
  usePageTitle("طرح‌های دسترسی");

  useEffect(() => {
    let mounted = true;
    api.plans()
      .then((payload) => {
        if (!mounted) return;
        setPlans(payload.plans);
        setStatus("ready");
      })
      .catch(() => {
        if (mounted) setStatus("error");
      });
    return () => {
      mounted = false;
    };
  }, []);

  const freePlan = useMemo(
    () => plans.find((plan) => plan.tier === "free") ?? plans[0],
    [plans],
  );
  const professionalPlan = useMemo(
    () => plans.find((plan) => plan.code === "professional" && plan.tier === "paid")
      ?? plans.find((plan) => plan.tier === "paid"),
    [plans],
  );
  const returnTo = safeReturnTo(new URLSearchParams(location.search).get("returnTo"));

  function beginPurchase() {
    if (!isAuthenticated) {
      const search = `?${new URLSearchParams({ returnTo: location.pathname + location.search }).toString()}`;
      navigate({ pathname: "/login", search }, { state: { backgroundLocation: location } });
      return;
    }
    setMessage("درگاه پرداخت به‌زودی فعال می‌شود.");
  }

  return (
    <main className="subscription-page">
      <div className="subscription-shell">
        <Header />
        <div className="page-back-navigation">
          <BackNavigation />
        </div>
        <section className="subscription-heading" aria-labelledby="subscription-title">
          <span className="eyebrow teal-text">دسترسی هواچ</span>
          <h1 id="subscription-title">طرح مناسب پیش‌بینی را انتخاب کن</h1>
          <p>روزهای قابل‌نمایش از تنظیمات پنل مدیریت خوانده می‌شوند و هر زمان قابل تغییرند.</p>
        </section>
        {status === "loading" ? <LoadingState /> : null}
        {status === "error" ? (
          <section className="subscription-message card-surface" role="alert">
            بارگذاری طرح‌ها ناموفق بود. دوباره تلاش کن.
          </section>
        ) : null}
        {status === "ready" ? (
          <section className="subscription-plan-grid" aria-label="طرح‌های اشتراک">
            <article className="subscription-plan-card free card-surface">
              <span className="subscription-plan-badge">فعلی</span>
              <h2>{freePlan?.title ?? "عضویت رایگان"}</h2>
              <p className="subscription-plan-access">{accessLabel(freePlan)}</p>
              <p className="subscription-plan-note">برای شروع، همین حالا بدون پرداخت استفاده کن.</p>
              {session?.plan?.tier === "free" ? <span className="subscription-current">طرح فعال حساب تو</span> : null}
            </article>
            <article className="subscription-plan-card paid card-surface">
              <span className="subscription-plan-badge paid-badge">پیشنهاد حرفه‌ای</span>
              <h2>{professionalPlan?.title ?? "طرح حرفه‌ای"}</h2>
              <p className="subscription-plan-access">
                {professionalPlan?.duration_months === 3 ? "عضویت سه‌ماهه" : "عضویت حرفه‌ای"}
              </p>
              <p className="subscription-plan-note">دسترسی گسترده‌تر به پیش‌بینی روزهای آینده.</p>
              <button type="button" className="subscription-plan-cta" onClick={beginPurchase}>
                {isAuthenticated ? "خرید اشتراک" : "ورود برای خرید"}
              </button>
              {message ? <p className="subscription-plan-message" role="status">{message}</p> : null}
            </article>
          </section>
        ) : null}
        {returnTo !== "/" ? <button type="button" className="subscription-return-link" onClick={() => navigate(returnTo)}>بازگشت به پیش‌بینی</button> : null}
      </div>
    </main>
  );
}
