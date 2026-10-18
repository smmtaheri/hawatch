// Global styles precede page styles in the single production stylesheet.
import "./styles/new-design/base.css";
import "./styles/new-design/route.css";
import "./styles/new-design/site.css";
import "./styles/new-design/integration.css";
import "./styles/new-design/shared.css";
import "./styles/new-design/landscape.css";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { captureInitialSeoContent } from "./lib/initialSeoContent";
import { App } from "./app/App";
import { initializeGa4 } from "./lib/ga4";
import { prepareForecastPage } from "./api/weekForecast";
import { ThemeProvider } from "./app/theme";

window.__hawatchPageLoad?.appReady?.();
captureInitialSeoContent();
prepareForecastPage(window.location.pathname);
initializeGa4();

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <ThemeProvider>
      <App />
    </ThemeProvider>
  </StrictMode>,
);
