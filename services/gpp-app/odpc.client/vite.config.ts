import { fileURLToPath, URL } from "node:url";

import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

const proxyCalls = ["/api", "/signin-oidc", "/signout-callback-oidc", "/healthz", "/health"];

// API target: Use VITE_API_TARGET env var or default to Caddy (8080)
// For direct FastAPI BFF access, set VITE_API_TARGET=http://localhost:8005
const apiTarget = process.env.VITE_API_TARGET || "http://localhost:8080";

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url))
    }
  },
  server: {
    host: "0.0.0.0",  // Allow external access (for Docker)
    port: 5173,
    proxy: Object.fromEntries(
      proxyCalls.map((key) => [
        key,
        {
          target: apiTarget,
          secure: false,
          changeOrigin: true
        }
      ])
    )
  },
  build: {
    assetsInlineLimit: 0
  }
});
