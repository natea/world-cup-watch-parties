import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import { initAnalytics } from './analytics.ts'
import { applyTheme, initialTheme } from './useTheme.ts'
import { installExternalLinkHandler, lockViewportOnNative, markPlatform } from './native.ts'

// Tag the platform (ios/android/web) before paint so native-only chrome applies.
markPlatform()
// On native, pin the viewport scale so pinch-zoom drives the map, not the page.
lockViewportOnNative()
// Set the theme before first paint to avoid a flash of the wrong palette.
applyTheme(initialTheme())
initAnalytics()
// On native (Capacitor), open external links in the system browser.
installExternalLinkHandler()

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
