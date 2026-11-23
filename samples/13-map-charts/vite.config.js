import { defineConfig } from "vite";

export default defineConfig({
  build: {
    // Calcite's colors use the CSS light-dark() function. With an older CSS target the build
    // rewrites light-dark() into a fallback that ignores color-scheme set from JavaScript,
    // so the theme switch would do nothing. These browsers support light-dark() natively.
    cssTarget: ["chrome123", "edge123", "firefox120", "safari17.5"],
  },
});
