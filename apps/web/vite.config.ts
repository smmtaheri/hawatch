import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

const apiProxy = {
  target: "http://localhost:8000",
  changeOrigin: true,
};

export default defineConfig({
  envDir: "../../",
  plugins: [react()],
  build: {
    // Django serves the first HTML response for public SEO pages. Keep the
    // entry CSS/JS paths stable so that server-rendered HTML never needs to
    // know Vite's content hash. Lazy chunks remain content-addressed.
    rollupOptions: {
      output: {
        entryFileNames: "assets/hawatch.js",
        chunkFileNames: "assets/chunks/[name]-[hash].js",
        assetFileNames: (assetInfo) =>
          assetInfo.name?.endsWith(".css") ? "assets/hawatch.css" : "assets/[name]-[hash][extname]",
      },
    },
  },
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
