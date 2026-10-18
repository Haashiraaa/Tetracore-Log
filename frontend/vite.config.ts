import react from "@vitejs/plugin-react";
import { fileURLToPath, URL } from "node:url";
import { defineConfig, loadEnv } from "vite";

// The browser only ever talks to its own origin ("/api/..."). In development the
// Vite server forwards those calls to FastAPI, so there is no CORS to configure
// and the app also works when opened from a phone on the same Wi-Fi.
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const target = env.API_PROXY_TARGET || "http://127.0.0.1:8000";
  const proxy = { "/api": { target, changeOrigin: true } };

  return {
    plugins: [react()],
    resolve: {
      alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) },
    },
    server: { port: 5173, strictPort: true, proxy },
    preview: { port: 4173, strictPort: true, proxy },
  };
});
