import { BrowserRouter, Route, Routes, useLocation } from "react-router-dom";
import { lazy, Suspense, useEffect, useLayoutEffect, useRef } from "react";
import { trackPageView } from "../api/client";
import { HomePage } from "../pages/HomePage";
import { LoadingState } from "../components/LoadingState";

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
const PointDetailPage = lazy(() =>
  import("../pages/PointDetailPage").then((module) => ({
    default: module.PointDetailPage,
  })),
);
const RoutePage = lazy(() =>
  import("../pages/RoutePage").then((module) => ({ default: module.RoutePage })),
);
const NotFoundPage = lazy(() =>
  import("../pages/NotFoundPage").then((module) => ({
    default: module.NotFoundPage,
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
      <Suspense fallback={<LoadingState label="در حال آماده‌سازی صفحه…" />}>
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
          <Route path="/routes/:slug" element={<RoutePage />} />
          <Route path="/points/:slug" element={<PointDetailPage />} />
          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </Suspense>

    </>
  );
}
