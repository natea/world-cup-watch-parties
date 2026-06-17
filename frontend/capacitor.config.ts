import type { CapacitorConfig } from "@capacitor/cli";

const config: CapacitorConfig = {
  appId: "app.stagehopper.worldcup",
  appName: "WorldCup Watcher",
  webDir: "dist",
  // Capacitor serves the bundled web build from a localhost scheme; the app
  // talks to the production API (set via VITE_API_BASE at build time).
  ios: {
    // The webview fills the screen; CSS env(safe-area-inset-*) handles the notch
    // and home-indicator insets (a single source of truth — "always" would
    // double-inset on top of the CSS padding).
    contentInset: "never",
  },
  plugins: {
    SplashScreen: {
      launchShowDuration: 800,
      backgroundColor: "#0f1115",
      showSpinner: false,
    },
  },
};

export default config;
