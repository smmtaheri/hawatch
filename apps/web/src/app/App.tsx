import { BrowserRouter, Route, Routes, useLocation } from "react-router-dom";
import { useEffect, useLayoutEffect, useRef } from "react";
import { trackPageView } from "../api/client";
import { HomePage } from "../pages/HomePage";
import { NotFoundPage } from "../pages/NotFoundPage";
import { RoutePageViewTracker } from "./RoutePageViewTracker";
import { PageLoadingBoundary } from "./PageLoadingBoundary";
import { prepareForecastPage } from "../api/weekForecast";
import { startPageLoad } from "../lib/pageLoad";
import { DestinationsPage, RoutesPage } from "../features/destinations/DestinationsPage";
import { LoginPage } from "../pages/LoginPage";
import { WeekForecastPage } from "../features/week/WeekForecastPage";
import { SubscriptionPlansPage } from "../pages/SubscriptionPlansPage";
import { PUBLIC_PAGE_ROUTES, type PublicPageComponent } from "./publicPageRoutes.generated";
import type { ReactNode } from "react";

export function App() {
  return (
    <BrowserRouter>
      <AppRoutes />
    </BrowserRouter>
  );
}

export function AppRoutes() {
  const location = useLocation();
  const trackedNavigationRef = useRef<string | null>(null);
  useLayoutEffect(() => {
    startPageLoad(location.pathname);
    prepareForecastPage(location.pathname);
    window.scrollTo({ top: 0, left: 0, behavior: "instant" });
  }, [location.pathname]);

  const pageElement = (component: PublicPageComponent): ReactNode => {
    switch (component) {
      case "home":
        return <HomePage />;
      case "destinations":
        return <DestinationsPage />;
      case "routes":
        return <RoutesPage />;
      case "login":
        return <LoginPage />;
      case "plans":
        return <SubscriptionPlansPage />;
      case "point-forecast":
        return <WeekForecastPage key={location.pathname} kind="point" />;
      case "route-forecast":
        return <WeekForecastPage key={location.pathname} kind="route" />;
      default: {
        const unreachable: never = component;
        throw new Error(`Unknown public page component: ${unreachable}`);
      }
    }
  };

  useEffect(() => {
    const match = location.pathname.match(/^\/(points|routes)\/([^/]+)\/?$/);
    if (!match) return;
    const fingerprint = location.pathname;
    if (trackedNavigationRef.current === fingerprint) return;
    trackedNavigationRef.current = fingerprint;
    trackPageView(match[1] === "points" ? "point" : "route", match[2]);
  }, [location.pathname]);

  return (
    <>
      <RoutePageViewTracker />
      <PageLoadingBoundary>
        <Routes>
          {PUBLIC_PAGE_ROUTES.map(({ id, path, component }) => (
            <Route key={`${id}:${path}`} path={path} element={pageElement(component)} />
          ))}
          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </PageLoadingBoundary>

    </>
  );
}
