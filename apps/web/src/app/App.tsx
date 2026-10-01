import { BrowserRouter, Route, Routes, useLocation } from "react-router-dom";
import { useEffect, useLayoutEffect, useRef } from "react";
import { trackPageView } from "../api/client";
import { HomePage } from "../pages/HomePage";
import { DestinationsPage, RoutesPage } from "../features/destinations/DestinationsPage";
import { LoginPage } from "../pages/LoginPage";
import { PointDetailPage } from "../pages/PointDetailPage";
import { RoutePage } from "../pages/RoutePage";
import { NotFoundPage } from "../pages/NotFoundPage";
import { SubscriptionPlansPage } from "../pages/SubscriptionPlansPage";

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
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/destinations" element={<DestinationsPage />} />
        <Route path="/destinations/" element={<DestinationsPage />} />
        <Route path="/destinations/page/:page" element={<DestinationsPage />} />
        <Route path="/destinations/page/:page/" element={<DestinationsPage />} />
        <Route path="/routes" element={<RoutesPage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/account/plans" element={<SubscriptionPlansPage />} />
        <Route path="/routes/:slug" element={<RoutePage />} />
        <Route path="/points/:slug" element={<PointDetailPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Routes>

    </>
  );
}
