/**
 * Native-vs-web seam for Capacitor. Each helper uses the native plugin when the
 * app runs inside Capacitor (iOS/Android) and falls back to the web API
 * otherwise, so the same SPA behaves identically on the web.
 */
import { Capacitor } from "@capacitor/core";

export const isNative = (): boolean => Capacitor.isNativePlatform();

/** Tag <html> with the platform ("ios" | "android" | "web") so CSS can target
 *  native-only chrome (e.g. the iOS bottom tab bar) without touching the web. */
export function markPlatform(): void {
  document.documentElement.setAttribute("data-platform", Capacitor.getPlatform());
}

/**
 * Lock the viewport scale on native only.
 *
 * The webview otherwise lets a pinch gesture zoom the whole page, which fights
 * the Leaflet map's own pinch-to-zoom (the map appears to "misbehave" when you
 * pinch). Pinning maximum-scale=1 / user-scalable=no hands the gesture to the
 * map and also stops WKWebView's focus auto-zoom on form fields.
 *
 * Native-only so the website keeps pinch-zoom for accessibility — the same
 * index.html serves both, so we can't bake this into the static meta tag.
 */
export function lockViewportOnNative(): void {
  if (!isNative()) return;
  const meta = document.querySelector('meta[name="viewport"]');
  if (!meta) return;
  meta.setAttribute(
    "content",
    "width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover",
  );
}

/** Geolocation: native plugin (proper permission flow) or browser API. */
export async function getCurrentPosition(): Promise<{ lat: number; lng: number }> {
  if (isNative()) {
    const { Geolocation } = await import("@capacitor/geolocation");
    const perm = await Geolocation.requestPermissions();
    if (perm.location === "denied") throw new Error("denied");
    const pos = await Geolocation.getCurrentPosition({ enableHighAccuracy: false, timeout: 8000 });
    return { lat: pos.coords.latitude, lng: pos.coords.longitude };
  }
  return new Promise((resolve, reject) => {
    if (!("geolocation" in navigator)) return reject(new Error("unsupported"));
    navigator.geolocation.getCurrentPosition(
      (p) => resolve({ lat: p.coords.latitude, lng: p.coords.longitude }),
      (e) => reject(e),
      { enableHighAccuracy: false, timeout: 8000 },
    );
  });
}

/** Share a link via the OS share sheet (native) or the Web Share API / clipboard. */
export async function shareLink(opts: { title: string; text?: string; url: string }): Promise<void> {
  if (isNative()) {
    const { Share } = await import("@capacitor/share");
    await Share.share({ title: opts.title, text: opts.text, url: opts.url });
    return;
  }
  if (navigator.share) {
    await navigator.share({ title: opts.title, text: opts.text, url: opts.url });
    return;
  }
  await navigator.clipboard?.writeText(opts.url);
}

export const canShare = (): boolean => isNative() || typeof navigator.share === "function";

/**
 * On native, route outbound http(s) links (maps, venue sites, partner links)
 * through the system browser instead of letting them dead-end in the webview.
 * One delegated click listener covers every <a target="_blank"> in the app.
 */
export function installExternalLinkHandler(): void {
  if (!isNative()) return;
  document.addEventListener(
    "click",
    (e) => {
      const a = (e.target as HTMLElement)?.closest?.("a[href]") as HTMLAnchorElement | null;
      if (!a) return;
      const href = a.getAttribute("href") || "";
      if (/^https?:\/\//i.test(href) && a.target === "_blank") {
        e.preventDefault();
        import("@capacitor/browser").then(({ Browser }) => Browser.open({ url: href }));
      }
    },
    true,
  );
}

/** Match the native status bar to the active theme. */
export async function applyNativeStatusBar(theme: "light" | "dark"): Promise<void> {
  if (!isNative()) return;
  const { StatusBar, Style } = await import("@capacitor/status-bar");
  try {
    await StatusBar.setStyle({ style: theme === "dark" ? Style.Dark : Style.Light });
  } catch {
    /* status bar not available (e.g. Android edge cases) — ignore */
  }
}
