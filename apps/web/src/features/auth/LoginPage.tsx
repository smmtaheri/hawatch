import { useEffect, useRef } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { usePageTitle } from "../../lib/pageTitle";

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

          <div className="login-overlay-step" aria-label="مرحلهٔ ۱ از ۲">
            <span className="is-active" aria-hidden="true" />
            <span aria-hidden="true" />
            <span>مرحلهٔ ۱ از ۲</span>
          </div>

          <form className="login-overlay-form" onSubmit={(event) => event.preventDefault()}>
            <label htmlFor="login-phone">شمارهٔ موبایل</label>
            <div className="login-overlay-phone-field">
              <span dir="ltr" aria-hidden="true">+98</span>
              <input
                id="login-phone"
                type="tel"
                inputMode="tel"
                autoComplete="tel"
                dir="ltr"
                placeholder="0912 123 4567"
                aria-describedby="login-unavailable"
              />
            </div>
            <button className="login-overlay-submit" type="submit" disabled>
              دریافت کد ورود
            </button>
          </form>

          <p id="login-unavailable" className="login-overlay-unavailable" role="status">
            ورود پیامکی هنوز فعال نشده است.
          </p>
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
