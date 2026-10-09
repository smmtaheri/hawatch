import { useLocation } from "react-router-dom";
import { initialSeoContentFor } from "../lib/initialSeoContent";
import type { ReactNode } from "react";
import { Header } from "./Header";
import { BackNavigation } from "./BackNavigation";
import { ROUTE_NIGHT_TONE } from "../styles/new-design/routeBackgroundTone";
const [routeNightDesktopR, routeNightDesktopG, routeNightDesktopB] = ROUTE_NIGHT_TONE.desktop;
const [routeNightMobileR, routeNightMobileG, routeNightMobileB] = ROUTE_NIGHT_TONE.mobile;
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
              <feFuncR type="gamma" {...routeNightDesktopR} />
              <feFuncG type="gamma" {...routeNightDesktopG} />
              <feFuncB type="gamma" {...routeNightDesktopB} />
            </feComponentTransfer>
          </filter>
          <filter id="route-night-mobile" x="0" y="0" width="100%" height="100%" colorInterpolationFilters="sRGB">
            <feComponentTransfer>
              <feFuncR type="gamma" {...routeNightMobileR} />
              <feFuncG type="gamma" {...routeNightMobileG} />
              <feFuncB type="gamma" {...routeNightMobileB} />
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
