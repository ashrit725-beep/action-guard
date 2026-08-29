import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

import { localStore } from "@/lib/storage";

const STORAGE_KEY = "vexen.theme";

/** Vexen is light-first. Dark mode is available, but light is the default. */
const DEFAULT_THEME = "light";

const ThemeContext = createContext({
  theme: DEFAULT_THEME,
  toggle: () => {},
  setTheme: () => {},
});

function applyTheme(theme) {
  const root = document.documentElement;
  if (!root) return;
  if (theme === "dark") root.classList.add("dark");
  else root.classList.remove("dark");
  root.style.colorScheme = theme;

  const meta = document.querySelector('meta[name="theme-color"]');
  if (meta) meta.setAttribute("content", theme === "dark" ? "#1a2028" : "#f7fafc");
}

export const ThemeProvider = ({ children }) => {
  const [theme, setThemeState] = useState(() => {
    if (typeof window === "undefined") return DEFAULT_THEME;
    const stored = localStore.get(STORAGE_KEY);
    return stored === "dark" || stored === "light" ? stored : DEFAULT_THEME;
  });

  useEffect(() => {
    applyTheme(theme);
    localStore.set(STORAGE_KEY, theme);
  }, [theme]);

  const setTheme = useCallback((next) => setThemeState(next === "dark" ? "dark" : "light"), []);
  const toggle = useCallback(() => setThemeState((t) => (t === "dark" ? "light" : "dark")), []);

  const value = useMemo(() => ({ theme, setTheme, toggle }), [theme, setTheme, toggle]);
  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
};

export const useTheme = () => useContext(ThemeContext);
