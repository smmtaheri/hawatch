import { AppShell } from "../../components/AppShell";
import { BackNavigation } from "../../components/BackNavigation";
import { usePageTitle } from "../../lib/pageTitle";

export function LoginPage() {
  usePageTitle("ورود");

  return (
    <AppShell className="auth-page">
      <div className="auth-shell">
        <BackNavigation />
        <div className="auth-layout">
          <div className="auth-intro">
            <span className="auth-kicker">ورود به هواچ</span>
            <h1>
              برنامهٔ مسیرت را <em>آماده</em> کن.
            </h1>
            <p>با ورود به هواچ، مسیرها و مقصدهای مورد علاقه‌ات را ساده‌تر دنبال کن.</p>
          </div>
          <section className="auth-card" aria-labelledby="login-title">
            <div className="auth-card-heading">
              <span className="auth-step">حساب هواچ</span>
              <h2 id="login-title">ورود</h2>
              <p>ورود با شمارهٔ موبایل در مرحلهٔ بعد فعال می‌شود.</p>
            </div>
            <p className="auth-hint" role="status">
              این بخش آماده است؛ احراز هویت و دریافت کد هنوز فعال نشده است.
            </p>
          </section>
        </div>
      </div>
    </AppShell>
  );
}
