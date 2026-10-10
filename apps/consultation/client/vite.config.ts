import { readFileSync } from "node:fs";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig(({ mode }) => ({
  plugins: [react(), tailwindcss()],
  server: {
    host: "0.0.0.0",
    port: mode === "jetson" ? 3443 : 3000,
    ...(mode === "jetson" ? {
      strictPort: true,
      https: {
        cert: readFileSync(new URL("../../../infra/certs/lan-cert.pem", import.meta.url)),
        key: readFileSync(new URL("../../../infra/certs/lan-key.pem", import.meta.url)),
      },
      proxy: {
        "/api/v1": {
          target: "http://127.0.0.1:18080",
          changeOrigin: true,
          ws: true,
        },
      },
    } : {}),
  },
  build: {
    outDir: "dist",
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (!id.includes("node_modules")) {
            return undefined;
          }

          if (id.includes("recharts") || id.includes("\\d3-") || id.includes("/d3-")) {
            return "charts-vendor";
          }

          if (id.includes("motion")) {
            return "motion-vendor";
          }

          if (id.includes("react-router")) {
            return "router-vendor";
          }

          if (id.includes("react") || id.includes("scheduler")) {
            return "react-vendor";
          }

          return undefined;
        },
      },
    },
  },
}));
