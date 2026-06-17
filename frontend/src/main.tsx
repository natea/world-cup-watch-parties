import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import { initAnalytics } from './analytics.ts'
import { applyTheme, initialTheme } from './useTheme.ts'
import { installExternalLinkHandler } from './native.ts'

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
