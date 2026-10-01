import { BackNavigation } from "../components/BackNavigation";
import { PageShell } from "../components/PageShell";
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
    <PageShell className="not-found-page">
        <section className="not-found-state hawatch-state empty" aria-labelledby="not-found-title">
          <h1 id="not-found-title">{title}</h1>
          <p>{detail}</p>
          <BackNavigation />
        </section>
    </PageShell>
  );
}
