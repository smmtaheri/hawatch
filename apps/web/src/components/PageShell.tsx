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
      {/* Grade the original light route photo without moving or regenerating
          any scenery. Curves match the destination's dark photo separately
          for its desktop and mobile compositions. Only .landscape uses them. */}
      <svg width="0" height="0" aria-hidden="true" focusable="false" style={{ position: "absolute", pointerEvents: "none" }}>
        <defs>
          <filter id="route-night-desktop" x="0" y="0" width="100%" height="100%" colorInterpolationFilters="sRGB">
            <feComponentTransfer>
              <feFuncR type="gamma" amplitude="0.5152" exponent="2.01" offset="0.0014" />
              <feFuncG type="gamma" amplitude="0.4622" exponent="2.58" offset="0.1378" />
              <feFuncB type="gamma" amplitude="0.4754" exponent="4" offset="0.2391" />
            </feComponentTransfer>
          </filter>
          <filter id="route-night-mobile" x="0" y="0" width="100%" height="100%" colorInterpolationFilters="sRGB">
            <feComponentTransfer>
              <feFuncR type="gamma" amplitude="0.5109" exponent="2.28" offset="0.0095" />
              <feFuncG type="gamma" amplitude="0.5205" exponent="2.4" offset="0.1123" />
              <feFuncB type="gamma" amplitude="0.4980" exponent="2.61" offset="0.1995" />
            </feComponentTransfer>
          </filter>
        </defs>
      </svg>
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
