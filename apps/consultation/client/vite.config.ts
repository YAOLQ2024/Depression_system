import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    host: "0.0.0.0",
    port: 3000,
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
});
