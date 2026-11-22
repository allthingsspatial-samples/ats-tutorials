import { defineConfig } from "vite";

export default defineConfig({
  // Fixed ports that match the localhost referrers on your API key.
  // strictPort stops Vite from moving to another port that the key does not allow.
  server: { port: 5173, strictPort: true },
  preview: { port: 4173, strictPort: true },
  build: {
    // Calcite's colors use the CSS light-dark() function; keep it native in the build.
    cssTarget: ["chrome123", "edge123", "firefox120", "safari17.5"],
  },
});
