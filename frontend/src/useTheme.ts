import { useCallback, useEffect, useState } from "react";
import { applyNativeStatusBar } from "./native";

export type Theme = "light" | "dark";
const KEY = "theme";

/** The startup theme: a saved choice, else the OS preference, else dark. */
export function initialTheme(): Theme {
  const saved = localStorage.getItem(KEY);
  if (saved === "light" || saved === "dark") return saved;
  return window.matchMedia?.("(prefers-color-scheme: light)").matches ? "light" : "dark";
}

export function applyTheme(theme: Theme): void {
  document.documentElement.setAttribute("data-theme", theme);
}

export function useTheme() {
  const [theme, setTheme] = useState<Theme>(() => initialTheme());

  useEffect(() => {
    applyTheme(theme);
    localStorage.setItem(KEY, theme);
    applyNativeStatusBar(theme);
  }, [theme]);

  const toggle = useCallback(() => setTheme((t) => (t === "dark" ? "light" : "dark")), []);

  return { theme, toggle };
}
