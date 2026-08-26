import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { DestinationPage } from "../pages/DestinationPage";
import { HomePage } from "../pages/HomePage";
import { RoutePage } from "../pages/RoutePage";

export function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/destination/:slug" element={<DestinationPage />} />
        <Route path="/routes/:slug" element={<RoutePage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
