import type { Theme } from "../theme";

export function ThemeToggle({ theme, onToggle }: { theme: Theme; onToggle: () => void }) {
  const target = theme === "dark" ? "light" : "dark";
  return (
    <button type="button" className="theme-toggle" onClick={onToggle} aria-label={`Switch to ${target} theme`}>
      {target === "dark" ? "☾" : "☀"}
    </button>
  );
}
