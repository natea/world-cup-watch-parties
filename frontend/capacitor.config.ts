import type { CapacitorConfig } from "@capacitor/cli";

const config: CapacitorConfig = {
  appId: "app.stagehopper.worldcup",
  appName: "WorldCup Watcher",
  webDir: "dist",
  // Capacitor serves the bundled web build from a localhost scheme; the app
  // talks to the production API (set via VITE_API_BASE at build time).
  ios: {
    contentInset: "always",
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
