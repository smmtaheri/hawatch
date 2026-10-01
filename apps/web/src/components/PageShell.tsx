import type { ReactNode } from "react";
import { Header } from "./Header";
import { BackNavigation } from "./BackNavigation";
export function PageShell({
  children,
  className,
  back = false,
}: {
  children: ReactNode;
  className: string;
  back?: boolean;
}) {
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
