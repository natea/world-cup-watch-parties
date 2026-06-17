// Privacy-first visitor analytics via Umami (cookieless, no consent banner).
//
// Loads the Umami script only when a website ID is configured at build time,
// so local dev and any un-configured build send zero analytics traffic.
// Set in the Render static site (and .env for local testing):
//   VITE_UMAMI_WEBSITE_ID=<your umami website id>
//   VITE_UMAMI_SRC=https://cloud.umami.is/script.js   (optional; this is the default)

export function initAnalytics(): void {
  const websiteId = import.meta.env.VITE_UMAMI_WEBSITE_ID;
  if (!websiteId) return;

  const src = import.meta.env.VITE_UMAMI_SRC ?? "https://cloud.umami.is/script.js";
  const script = document.createElement("script");
  script.async = true;
  script.defer = true;
  script.src = src;
  script.setAttribute("data-website-id", websiteId);
  document.head.appendChild(script);
}
