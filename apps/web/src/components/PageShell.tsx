import { useLocation } from "react-router-dom";
import { initialSeoContentFor } from "../lib/initialSeoContent";
import type { ReactNode } from "react";
import { Header } from "./Header";
import { BackNavigation } from "./BackNavigation";
export function PageShell({
  children,
  className,
  back = false,
  showInitialContent = false,
}: {
  children: ReactNode;
  className: string;
  back?: boolean;
  showInitialContent?: boolean;
}) {
  const location = useLocation();
  const initialContent = showInitialContent ? initialSeoContentFor(location.pathname, location.search) : null;
  return (
    <main className={className}>
      <div className="landscape" aria-hidden="true" />
      <div className="shell">
        <Header />
        {back ? (
          <div className="back-row">
            <BackNavigation />
          </div>
        ) : null}
        {initialContent ? <section className="seo-fallback" data-seo-fallback="true" dangerouslySetInnerHTML={{ __html: initialContent }} /> : null}
        {children}
        <footer
          className="footer forecast-attribution"
          aria-label="منبع دادهٔ هواشناسی"
        >
          دادهٔ هواشناسی: Open-Meteo
        </footer>
      </div>
    </main>
  );
}
