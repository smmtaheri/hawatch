import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

const apiProxy = {
  target: "http://localhost:8000",
  changeOrigin: true,
};

export default defineConfig({
  envDir: "../../",
  plugins: [react()],
  server: {
    host: "0.0.0.0",
    port: 5173,
    strictPort: true,
    proxy: { "/api": apiProxy },
  },
  preview: {
    host: "0.0.0.0",
    port: 5173,
    strictPort: true,
    proxy: { "/api": apiProxy },
  },
  test: {
    environment: "jsdom",
    setupFiles: ["./tests/setup.ts"],
    css: true,
  },
});
