import { useEffect, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { usePageTitle } from "../../lib/pageTitle";
import { useAuth } from "./authSession";

type LoginSurfaceProps = {
  presentation: "dialog" | "page";
};

function validReturnTo(value: string | null) {
  if (!value || !value.startsWith("/") || value.startsWith("//") || value.startsWith("/login")) return "/";
  return value;
}

function LoginSurface({ presentation }: LoginSurfaceProps) {
  const previousTitle = useRef(document.title);
  usePageTitle("ورود");
  const navigate = useNavigate();
  const location = useLocation();
  const panelRef = useRef<HTMLElement>(null);
  const returnTo = validReturnTo(new URLSearchParams(location.search).get("returnTo"));
  const isOverlay = presentation === "dialog";
  const { isAuthenticated, loading, login } = useAuth();
  const [submitting, setSubmitting] = useState(false);
  const [step, setStep] = useState<"phone" | "otp">("phone");
  const [phone, setPhone] = useState("");
  const [otp, setOtp] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    if (!loading && isAuthenticated) navigate(returnTo, { replace: true });
  }, [isAuthenticated, loading, navigate, returnTo]);

  useEffect(() => () => {
    document.title = previousTitle.current;
  }, []);

  useEffect(() => {
    if (!isOverlay) return;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    panelRef.current?.focus();

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") navigate(-1);
    };
    window.addEventListener("keydown", onKeyDown);
    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener("keydown", onKeyDown);
    };
  }, [isOverlay, navigate]);

  const close = () => {
    if (isOverlay) {
      navigate(-1);
      return;
    }
    navigate(returnTo, { replace: true });
  };

  return (
    <div className={`login-overlay login-overlay--${presentation}`}>
      {isOverlay ? <button className="login-overlay-backdrop" type="button" aria-label="بستن ورود" onClick={close} /> : null}
      <section
        ref={panelRef}
        className="login-overlay-panel"
        role={isOverlay ? "dialog" : undefined}
        aria-modal={isOverlay || undefined}
        aria-labelledby="login-title"
        tabIndex={-1}
      >
        <div className="login-overlay-topbar">
          <span className="login-overlay-brand" aria-label="هواچ">
            <img className="login-overlay-logo login-overlay-logo--dark" src="/brand/hawatch-logo-light.svg" alt="" />
            <img className="login-overlay-logo login-overlay-logo--light" src="/brand/hawatch-logo-dark.svg" alt="" />
          </span>
          <button className="login-overlay-close" type="button" onClick={close} aria-label="بستن ورود">
            ×
          </button>
        </div>

        <div className="login-overlay-content">
          <span className="login-overlay-kicker">ورود امن</span>
          <h1 id="login-title">ورود به هواچ</h1>
          <p className="login-overlay-lede">برای ذخیرهٔ مسیرها و ادامهٔ برنامه‌ریزی، شمارهٔ موبایلت را وارد کن.</p>

          <div className="login-overlay-step" aria-label={`مرحلهٔ ${step === "phone" ? "۱" : "۲"} از ۲`}>
            <span className={step === "phone" ? "is-active" : "is-complete"} aria-hidden="true" />
            <span className={step === "otp" ? "is-active" : ""} aria-hidden="true" />
            <span>مرحلهٔ {step === "phone" ? "۱" : "۲"} از ۲</span>
          </div>

          {step === "phone" ? (
            <form className="login-overlay-form" onSubmit={(event) => {
              event.preventDefault();
              if (!phone.trim()) {
                setError("شمارهٔ موبایل را وارد کنید.");
                return;
              }
              setError("");
              setStep("otp");
            }}>
              <label htmlFor="login-phone">شمارهٔ موبایل</label>
              <div className="login-overlay-phone-field">
                <span dir="ltr" aria-hidden="true">+98</span>
                <input
                  id="login-phone"
                  type="tel"
                  inputMode="tel"
                  autoComplete="tel"
                  dir="ltr"
                  value={phone}
                  onChange={(event) => setPhone(event.target.value)}
                  placeholder="شمارهٔ موبایل"
                  aria-describedby="login-error"
                />
              </div>
              <button className="login-overlay-submit" type="submit">
                ادامه
              </button>
            </form>
          ) : (
            <form className="login-overlay-form" onSubmit={async (event) => {
              event.preventDefault();
              setSubmitting(true);
              try {
                await login(phone, otp);
                navigate(returnTo, { replace: true });
              } catch (error) {
                setError(error instanceof Error ? error.message : "ورود ناموفق بود.");
              } finally {
                setSubmitting(false);
              }
            }}>
              <label htmlFor="login-otp">کد ورود</label>
              <input
                id="login-otp"
                className="login-overlay-otp-input"
                type="text"
                inputMode="numeric"
                autoComplete="one-time-code"
                dir="ltr"
                value={otp}
                onChange={(event) => setOtp(event.target.value)}
                placeholder=""
                aria-describedby="login-error"
              />
              <button className="login-overlay-submit" type="submit" disabled={submitting}>
                {submitting ? "در حال ورود…" : "ورود به هواچ"}
              </button>
              <button type="button" className="login-overlay-back-step" onClick={() => { setError(""); setStep("phone"); }}>
                تغییر شماره
              </button>
            </form>
          )}

          {error ? <p id="login-error" className="login-overlay-error" role="alert">{error}</p> : null}
        </div>
      </section>
    </div>
  );
}

/** Direct /login navigation, including reloads and links outside the app. */
export function LoginPage() {
  return <LoginSurface presentation="page" />;
}

/** Normal in-app navigation: a mobile full-screen layer or desktop dialog. */
export function LoginOverlay() {
  return <LoginSurface presentation="dialog" />;
}
