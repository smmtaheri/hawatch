import { BrowserRouter, Route, Routes, useLocation, type Location } from "react-router-dom";
import { useEffect, useRef } from "react";
import { trackPageView } from "../api/client";
import { HomePage } from "../pages/HomePage";
import { LoginOverlay, LoginPage } from "../pages/LoginPage";
import { PointDetailPage } from "../pages/PointDetailPage";
import { RoutePage } from "../pages/RoutePage";
import { NotFoundPage } from "../pages/NotFoundPage";

export function App() {
  return (
    <BrowserRouter>
      <AppRoutes />
    </BrowserRouter>
  );
}

type LoginLocationState = {
  backgroundLocation?: Location;
};

/**
 * A normal login click keeps its originating route rendered below the overlay.
 * A direct /login URL has no background location and therefore remains a
 * refresh-safe full page route.
 */
export function AppRoutes() {
  const location = useLocation();
  const trackedNavigationRef = useRef<string | null>(null);
  const state = location.state as LoginLocationState | null;
  const backgroundLocation = location.pathname === "/login" ? state?.backgroundLocation : undefined;

  useEffect(() => {
    const match = location.pathname.match(/^\/(points|routes)\/([^/]+)\/?$/);
    if (!match) return;
    const fingerprint = `${location.key}:${location.pathname}`;
    if (trackedNavigationRef.current === fingerprint) return;
    trackedNavigationRef.current = fingerprint;
    trackPageView(match[1] === "points" ? "point" : "route", match[2]);
  }, [location.key, location.pathname]);

  return (
    <>
      <Routes location={backgroundLocation ?? location}>
        <Route path="/" element={<HomePage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/routes/:slug" element={<RoutePage />} />
        <Route path="/points/:slug" element={<PointDetailPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
      {backgroundLocation ? <LoginOverlay /> : null}
    </>
  );
}
