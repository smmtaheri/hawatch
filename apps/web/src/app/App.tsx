import { BrowserRouter, Route, Routes, useLocation } from "react-router-dom";
import { lazy, useEffect, useLayoutEffect, useRef } from "react";
import { trackPageView } from "../api/client";
import { HomePage } from "../pages/HomePage";
import { NotFoundPage } from "../pages/NotFoundPage";
import { RoutePageViewTracker } from "./RoutePageViewTracker";
import { PageLoadingBoundary } from "./PageLoadingBoundary";
import { prepareForecastPage } from "../api/weekForecast";
import { startPageLoad } from "../lib/pageLoad";

const DestinationsPage = lazy(() =>
  import("../features/destinations/DestinationsPage").then((module) => ({
    default: module.DestinationsPage,
  })),
);
const RoutesPage = lazy(() =>
  import("../features/destinations/DestinationsPage").then((module) => ({
    default: module.RoutesPage,
  })),
);
const LoginPage = lazy(() =>
  import("../pages/LoginPage").then((module) => ({ default: module.LoginPage })),
);
const WeekForecastPage = lazy(() =>
  import("../features/week/WeekForecastPage").then((module) => ({
    default: module.WeekForecastPage,
  })),
);
const SubscriptionPlansPage = lazy(() =>
  import("../pages/SubscriptionPlansPage").then((module) => ({
    default: module.SubscriptionPlansPage,
  })),
);

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
          <Route path="/" element={<HomePage />} />
          <Route path="/destinations" element={<DestinationsPage />} />
          <Route path="/destinations/" element={<DestinationsPage />} />
          <Route path="/destinations/page/:page" element={<DestinationsPage />} />
          <Route path="/destinations/page/:page/" element={<DestinationsPage />} />
          <Route path="/routes" element={<RoutesPage />} />
          <Route path="/routes/" element={<RoutesPage />} />
          <Route path="/routes/page/:page" element={<RoutesPage />} />
          <Route path="/routes/page/:page/" element={<RoutesPage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/account/plans" element={<SubscriptionPlansPage />} />
          <Route path="/routes/:slug" element={<WeekForecastPage key={location.pathname} kind="route" />} />
          <Route path="/points/:slug" element={<WeekForecastPage key={location.pathname} kind="point" />} />
          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </PageLoadingBoundary>

    </>
  );
}
