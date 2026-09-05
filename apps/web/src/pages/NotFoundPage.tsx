import { BackNavigation } from "../components/BackNavigation";
import { Header } from "../components/Header";
import { SiteFooter } from "../components/SiteFooter";
import { usePageTitle } from "../lib/pageTitle";

export function NotFoundPage({
  title = "صفحه پیدا نشد",
  detail = "آدرس واردشده معتبر نیست یا این صفحه دیگر در دسترس نیست.",
}: {
  title?: string;
  detail?: string;
}) {
  usePageTitle(undefined, { robots: "noindex,follow", canonical: false });

  return (
    <main className="not-found-page">
      <div className="home-shell">
        <Header />
        <section className="not-found-state hawatch-state empty" aria-labelledby="not-found-title">
          <h1 id="not-found-title">{title}</h1>
          <p>{detail}</p>
          <BackNavigation />
        </section>
        <SiteFooter />
      </div>
    </main>
  );
}
