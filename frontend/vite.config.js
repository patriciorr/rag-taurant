import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";


// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    port: 5173,
    proxy: {
      "/api": "http://localhost:8000",
      "/assets/menu": {
        target: "http://localhost:4566",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/assets\/menu/, "/ragtaurant-assets/menu"),
      },
    },
    watch: {
      usePolling: true,
    },
  },
  test: {
    environment: "jsdom",
    setupFiles: "./src/test/setup.js",
    css: false,
  },
});
