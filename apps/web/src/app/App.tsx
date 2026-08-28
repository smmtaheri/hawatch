import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { DestinationPage } from "../pages/DestinationPage";
import { HomePage } from "../pages/HomePage";
import { LegacyRoutePointRedirect } from "../features/point/PointNavigation";
import { PointDetailPage } from "../pages/PointDetailPage";
import { RoutePage } from "../pages/RoutePage";

export function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/destination/:slug" element={<DestinationPage />} />
        <Route path="/routes/:slug" element={<RoutePage />} />
        <Route path="/points/:slug" element={<PointDetailPage />} />
        <Route path="/routes/:routeSlug/points/:pointSlug" element={<LegacyRoutePointRedirect />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
