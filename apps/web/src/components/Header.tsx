import { useEffect, useRef, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { Logo } from "./Logo";
import { SocialLinks } from "./SocialLinks";
import { ThemeToggle } from "./ThemeToggle";
import { DesignIcon } from "./DesignIcon";
import { normalizeIranPhone, useAuth } from "../features/auth/authSession";

export function openAccountLogin(returnTo?: string) {
  window.dispatchEvent(
    new CustomEvent("hawatch-open-login", { detail: { returnTo } }),
  );
}

export function Header() {
  const location = useLocation();
  const navigate = useNavigate();
  const { isAuthenticated, logout, login, session } = useAuth();
  const [open, setOpen] = useState(false);
  const [step, setStep] = useState<"phone" | "code">("phone");
  const [phone, setPhone] = useState("");
  const [code, setCode] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const anchor = useRef<HTMLDivElement>(null);
  const button = useRef<HTMLButtonElement>(null);
  const continuation = useRef<string | undefined>(undefined);
  const submitting = useRef(false);

  useEffect(() => {
    const show = (event: Event) => {
      const value = (event as CustomEvent<{ returnTo?: string }>).detail
        ?.returnTo;
      continuation.current =
        value?.startsWith("/") && !value.startsWith("//") ? value : undefined;
      setOpen(true);
    };
    window.addEventListener("hawatch-open-login", show);
    return () => window.removeEventListener("hawatch-open-login", show);
  }, []);
  useEffect(() => {
    if (
      (location.state as { openAccountLogin?: boolean } | null)
        ?.openAccountLogin
    ) {
      setOpen(true);
      navigate(location.pathname + location.search, {
        replace: true,
        state: null,
      });
    }
  }, [location.state, location.pathname, location.search, navigate]);
  useEffect(() => {
    if (!open) return;
    const outside = (event: PointerEvent) => {
      if (!anchor.current?.contains(event.target as Node)) setOpen(false);
    };
    const escape = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setOpen(false);
        button.current?.focus({ preventScroll: true });
      }
    };
    document.addEventListener("pointerdown", outside);
    document.addEventListener("keydown", escape);
    return () => {
      document.removeEventListener("pointerdown", outside);
      document.removeEventListener("keydown", escape);
    };
  }, [open]);
  useEffect(() => {
    if (open && !isAuthenticated)
      anchor.current
        ?.querySelector<HTMLInputElement>("input")
        ?.focus({ preventScroll: true });
  }, [open, step, isAuthenticated]);

  async function verify() {
    if (submitting.current) return;
    submitting.current = true;
    setBusy(true);
    setError("");
    try {
      const digits = code
        .replace(/[۰-۹]/g, (d) => String("۰۱۲۳۴۵۶۷۸۹".indexOf(d)))
        .replace(/[٠-٩]/g, (d) => String("٠١٢٣٤٥٦٧٨٩".indexOf(d)));
      await login(phone, digits);
      setCode("");
      if (continuation.current) {
        navigate(continuation.current, { replace: true });
        continuation.current = undefined;
      }
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "ورود ناموفق بود.");
    } finally {
      submitting.current = false;
      setBusy(false);
    }
  }

  return (
    <header className="global-header site-header">
      <div className="brand-links">
        <Logo />
        <nav className="catalog-nav" aria-label="فهرست‌ها">
          <Link
            to="/destinations"
            aria-current={
              location.pathname.startsWith("/destinations") ? "page" : undefined
            }
          >
            همهٔ مقصدها
          </Link>
          <Link
            to="/routes"
            aria-current={location.pathname === "/routes" ? "page" : undefined}
          >
            همهٔ مسیرها
          </Link>
        </nav>
      </div>
      <nav className="nav header-actions" aria-label="کنترل‌های صفحه">
        <ThemeToggle />
        <div className="account-wrap" ref={anchor}>
          <button
            ref={button}
            className={`nav-button account-button ${isAuthenticated ? "logged" : ""}`}
            type="button"
            aria-label={isAuthenticated ? "حساب" : "ورود"}
            aria-expanded={open}
            aria-controls="account-panel"
            aria-haspopup="dialog"
            onClick={() => setOpen((value) => !value)}
          >
            <DesignIcon name="user" />
          </button>
          {open ? (
            <div
              className="account-menu"
              id="account-panel"
              role="dialog"
              aria-label={isAuthenticated ? "حساب کاربری" : "ورود به هواچ"}
            >
              {isAuthenticated ? (
                <>
                  <div className="account-plan-line">
                    <strong>{session?.plan?.title || "عضویت رایگان"}</strong>
                    {session?.plan?.tier === "paid" &&
                    session.days_remaining != null ? (
                      <small className="account-expiry">
                        ({session.days_remaining.toLocaleString("fa-IR")} روز
                        مانده)
                      </small>
                    ) : null}
                  </div>
                  <Link
                    className="account-subscription"
                    to="/account/plans"
                    onClick={() => setOpen(false)}
                  >
                    خرید اشتراک
                  </Link>
                  <button
                    className="account-logout"
                    type="button"
                    disabled={busy}
                    onClick={async () => {
                      if (submitting.current) return;
                      submitting.current = true;
                      setBusy(true);
                      try {
                        await logout();
                        setStep("phone");
                        setCode("");
                        setError("");
                      } catch {
                        setError("خروج ناموفق بود. دوباره تلاش کن.");
                      } finally {
                        submitting.current = false;
                        setBusy(false);
                      }
                    }}
                  >
                    خروج از حساب
                  </button>
                </>
              ) : (
                <form
                  onSubmit={(event) => {
                    event.preventDefault();
                    if (step === "code") {
                      void verify();
                      return;
                    }
                    if (!/^989\d{9}$/.test(normalizeIranPhone(phone))) {
                      setError("شمارهٔ موبایل معتبر وارد کن.");
                      return;
                    }
                    setError("");
                    setStep("code");
                  }}
                >
                  <h2 className="account-menu-title">
                    {step === "phone" ? "ورود" : "تأیید شماره"}
                  </h2>
                  {step === "code" ? (
                    <div className="account-phone-line">
                      <bdi dir="ltr">{phone}</bdi>
                      <button
                        type="button"
                        onClick={() => {
                          setStep("phone");
                          setError("");
                        }}
                      >
                        ویرایش
                      </button>
                    </div>
                  ) : null}
                  <label
                    htmlFor={
                      step === "phone" ? "account-phone" : "account-code"
                    }
                  >
                    {step === "phone" ? "شمارهٔ موبایل" : "کد ورود"}
                  </label>
                  {step === "phone" ? (
                    <input
                      id="account-phone"
                      className="account-input"
                      type="tel"
                      inputMode="tel"
                      autoComplete="tel"
                      dir="ltr"
                      value={phone}
                      aria-invalid={!!error}
                      onChange={(e) => setPhone(e.target.value)}
                    />
                  ) : (
                    <input
                      id="account-code"
                      className="account-input account-otp"
                      inputMode="numeric"
                      autoComplete="one-time-code"
                      dir="ltr"
                      value={code}
                      aria-invalid={!!error}
                      onChange={(e) => setCode(e.target.value)}
                    />
                  )}
                  <p
                    className="account-error"
                    role={error ? "alert" : undefined}
                  >
                    {error}
                  </p>
                  <button
                    className="account-submit"
                    type="submit"
                    disabled={busy}
                  >
                    {busy
                      ? "در حال ورود…"
                      : step === "phone"
                        ? "ادامه"
                        : "تأیید و ورود"}
                  </button>
                </form>
              )}
              {isAuthenticated && error ? (
                <p role="alert" className="account-error">
                  {error}
                </p>
              ) : null}
            </div>
          ) : null}
        </div>
        <SocialLinks />
      </nav>
    </header>
  );
}
