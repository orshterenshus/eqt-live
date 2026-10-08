import { createContext, useContext, useMemo, useState } from "react";

export type Theme = "light" | "dark";

const STORAGE_KEY = "eqt-theme";

export function initialTheme(): Theme {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored === "light" || stored === "dark") return stored;
  } catch {
    // storage unavailable (private mode, blocked): fall through to the OS preference
  }
  return window.matchMedia?.("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

export function applyTheme(theme: Theme): void {
  document.documentElement.dataset.theme = theme;
}

export function saveTheme(theme: Theme): void {
  try {
    localStorage.setItem(STORAGE_KEY, theme);
  } catch {
    // not persisted; the toggle still works for this visit
  }
}

export function useTheme(): [Theme, () => void] {
  const [theme, setTheme] = useState<Theme>(() => {
    const current = document.documentElement.dataset.theme;
    return current === "light" || current === "dark" ? current : initialTheme();
  });
  const toggle = () => {
    const next: Theme = theme === "dark" ? "light" : "dark";
    applyTheme(next); // before re-render, so charts read the new CSS variables
    saveTheme(next);
    setTheme(next);
  };
  return [theme, toggle];
}

export const ThemeContext = createContext<Theme>("light");

export interface ThemeColors {
  scope: string;
  trace: string;
  teacher: string;
  student: string;
  expected: string;
  muted: string;
  hair: string;
  good: string;
  warn: string;
  bad: string;
}

const FALLBACK: ThemeColors = {
  scope: "#11100e", trace: "#7ee0c3", teacher: "#f2f0ea", student: "#ff6b4a", expected: "#9b917f",
  muted: "#9b917f", hair: "#2a2622", good: "#2f6b3a", warn: "#9a5b00", bad: "#b42318",
};

export function readThemeColors(): ThemeColors {
  const style = getComputedStyle(document.documentElement);
  const read = (name: string, fallback: string) => style.getPropertyValue(name).trim() || fallback;
  return {
    scope: read("--scope", FALLBACK.scope),
    trace: read("--trace", FALLBACK.trace),
    teacher: read("--teacher", FALLBACK.teacher),
    student: read("--student", FALLBACK.student),
    expected: read("--expected", FALLBACK.expected),
    muted: read("--scope-muted", FALLBACK.muted),
    hair: read("--scope-line", FALLBACK.hair),
    good: read("--good", FALLBACK.good),
    warn: read("--warn", FALLBACK.warn),
    bad: read("--bad", FALLBACK.bad),
  };
}

export function useThemeColors(): ThemeColors {
  const theme = useContext(ThemeContext);
  return useMemo(() => readThemeColors(), [theme]);
}
