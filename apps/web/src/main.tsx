import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "./app/App";
import { ThemeProvider } from "./app/theme";
import "./styles/new-design/base.css";
import "./styles/new-design/route.css";
import "./styles/new-design/site.css";
import "./styles/new-design/integration.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <ThemeProvider>
      <App />
    </ThemeProvider>
  </StrictMode>,
);
