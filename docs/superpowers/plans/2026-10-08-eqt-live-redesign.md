# EQT-Live Visual Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restyle the EQT-Live frontend into a light "Paper + Instrument" / dark "Night Drum" design with a theme toggle, and add a plain-language verdict and per-pick quality labels to each analysis.

**Architecture:** CSS custom properties on `:root` and `:root[data-theme="dark"]` drive every color; a tiny `theme.ts` module reads, applies and persists the theme, and a React context lets the Plotly charts re-read the tokens on toggle. Verdict logic is a pure, tested module (`verdict.ts`) consumed by `AnalysisView` and `ComparisonCard`. No backend changes.

**Tech Stack:** React 18 + TypeScript, Vite 5, Vitest + React Testing Library, Plotly (`react-plotly.js`), react-leaflet, Google Fonts (Fraunces, IBM Plex Mono, IBM Plex Sans).

**Spec:** `docs/superpowers/specs/2026-10-08-eqt-live-redesign-design.md`

## Global Constraints

- All work is in `frontend/`; run commands from `eqt-live/frontend`. Do not modify `backend/`.
- No emoji anywhere in the UI (remove 🌍, ✅, ⚡). `☾`/`☀`, `●`, `▸`, `×`, `—`, `·` are plain text glyphs and are allowed.
- Square corners (`border-radius: 0`) and no `box-shadow` on site elements.
- Colors only via CSS custom properties defined in `src/styles.css` (`--bg --ink --muted --rule --hair --line --panel --scope --scope-line --scope-muted --trace --trace-glow --teacher --student --expected --accent --good --warn --bad --map-filter`).
- Fonts: Fraunces (serif: headline, verdict, panel titles), IBM Plex Mono (wordmark, labels, numbers, tables), IBM Plex Sans (body).
- Theme storage key: `eqt-theme`; values `"light"` | `"dark"`; all `localStorage` access wrapped in try/catch.
- Pick quality thresholds: |Δ| ≤ 1 s → `close`; ≤ 3 s → `fair`; > 3 s → `far`; no pick → `none`; no expected arrival → `null`.
- Verification for every task: `npx tsc --noEmit`, `npx vitest run`, `npm run build` all pass.
- Commit trailer, exactly: `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`

## File Map

```
frontend/
├── index.html                       fonts + no-flash theme script (Task 1)
└── src/
    ├── theme.ts / theme.test.tsx    Theme type, initialTheme/applyTheme/saveTheme, useTheme,
    │                                ThemeContext, readThemeColors, useThemeColors (Task 1)
    ├── components/ThemeToggle.tsx   ☾/☀ button (Task 1)
    ├── App.tsx                      header bar, nav (Recent/Live/Method), toggle, context (Task 1)
    ├── styles.css                   full rewrite on tokens (Task 2)
    ├── format.ts / format.test.ts   + formatDateline (Task 2)
    ├── tabs/RecentTab.tsx           intro block (Task 2)
    ├── tabs/LiveTab.tsx             note styling (Task 2)
    ├── components/EventList.tsx     marker/mag/age markup (Task 2)
    ├── components/EventMap.tsx      themed markers + tooltip (Task 2)
    ├── components/Spinner.tsx       mono line + cursor (Task 2)
    ├── components/ErrorBox.tsx      note styling (Task 2)
    ├── components/AboutPanel.tsx    "Method" article (Task 2)
    ├── verdict.ts / verdict.test.ts pickQuality, formatDelta, speedup, verdictSentence (Task 3)
    ├── components/ComparisonCard.tsx (+ test)  quality cells, no emoji (Task 4)
    ├── components/AnalysisView.tsx  verdict + instrument "scope" containers (Task 4)
    └── components/WaveformChart.tsx, ProbabilityChart.tsx  theme colors (Task 5)
```

---

### Task 1: Theme module, toggle, no-flash script and header

**Files:**
- Create: `frontend/src/theme.ts`, `frontend/src/theme.test.tsx`, `frontend/src/components/ThemeToggle.tsx`
- Modify: `frontend/index.html`, `frontend/src/App.tsx`

**Interfaces:**
- Produces:
  - `type Theme = "light" | "dark"`
  - `initialTheme(): Theme`, `applyTheme(t: Theme): void`, `saveTheme(t: Theme): void`
  - `useTheme(): [Theme, () => void]` (the toggle applies to `<html data-theme>` and persists synchronously, before re-render)
  - `ThemeContext: React.Context<Theme>`
  - `interface ThemeColors { trace; teacher; student; expected; muted; hair; good; warn; bad: string }`, `readThemeColors(): ThemeColors`, `useThemeColors(): ThemeColors` (recomputed when the context theme changes)
  - `<ThemeToggle theme={Theme} onToggle={() => void} />`

- [ ] **Step 1: Write the failing tests**

`frontend/src/theme.test.tsx`:
```tsx
import { act, render, renderHook, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ThemeToggle } from "./components/ThemeToggle";
import { initialTheme, readThemeColors, useTheme } from "./theme";

function mockMatchMedia(dark: boolean) {
  window.matchMedia = vi.fn().mockImplementation((q: string) => ({
    matches: dark && q.includes("dark"), media: q, addEventListener: vi.fn(), removeEventListener: vi.fn(),
  })) as unknown as typeof window.matchMedia;
}

describe("theme", () => {
  beforeEach(() => {
    localStorage.clear();
    delete document.documentElement.dataset.theme;
    mockMatchMedia(false);
  });
  afterEach(() => vi.restoreAllMocks());

  it("prefers the stored theme", () => {
    localStorage.setItem("eqt-theme", "dark");
    expect(initialTheme()).toBe("dark");
  });

  it("falls back to the OS preference when nothing is stored", () => {
    mockMatchMedia(true);
    expect(initialTheme()).toBe("dark");
  });

  it("falls back to the OS preference when storage throws", () => {
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
      throw new Error("blocked");
    });
    expect(initialTheme()).toBe("light");
  });

  it("toggle applies data-theme and persists", () => {
    const { result } = renderHook(() => useTheme());
    expect(result.current[0]).toBe("light");
    act(() => result.current[1]());
    expect(result.current[0]).toBe("dark");
    expect(document.documentElement.dataset.theme).toBe("dark");
    expect(localStorage.getItem("eqt-theme")).toBe("dark");
  });

  it("toggle still works when storage throws on write", () => {
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new Error("quota");
    });
    const { result } = renderHook(() => useTheme());
    act(() => result.current[1]());
    expect(document.documentElement.dataset.theme).toBe("dark");
  });

  it("readThemeColors returns fallbacks when CSS variables are absent", () => {
    const c = readThemeColors();
    expect(c.trace).toMatch(/^#/);
    expect(c.student).toMatch(/^#/);
  });

  it("ThemeToggle shows the target theme glyph and calls onToggle", () => {
    const onToggle = vi.fn();
    render(<ThemeToggle theme="light" onToggle={onToggle} />);
    const btn = screen.getByRole("button", { name: "Switch to dark theme" });
    expect(btn).toHaveTextContent("☾");
    act(() => btn.click());
    expect(onToggle).toHaveBeenCalledOnce();
  });
});
```

- [ ] **Step 2: Run to verify failure**

Run: `npx vitest run src/theme.test.tsx`
Expected: FAIL — cannot resolve `./theme` / `./components/ThemeToggle`.

- [ ] **Step 3: Implement `src/theme.ts`**

```ts
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
  trace: "#7ee0c3", teacher: "#f2f0ea", student: "#ff6b4a", expected: "#9b917f",
  muted: "#9b917f", hair: "#2a2622", good: "#2f6b3a", warn: "#9a5b00", bad: "#b42318",
};

export function readThemeColors(): ThemeColors {
  const style = getComputedStyle(document.documentElement);
  const read = (name: string, fallback: string) => style.getPropertyValue(name).trim() || fallback;
  return {
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
```

`frontend/src/components/ThemeToggle.tsx`:
```tsx
import type { Theme } from "../theme";

export function ThemeToggle({ theme, onToggle }: { theme: Theme; onToggle: () => void }) {
  const target = theme === "dark" ? "light" : "dark";
  return (
    <button type="button" className="theme-toggle" onClick={onToggle} aria-label={`Switch to ${target} theme`}>
      {target === "dark" ? "☾" : "☀"}
    </button>
  );
}
```

- [ ] **Step 4: Run tests**

Run: `npx vitest run src/theme.test.tsx`
Expected: 7 passed. (If eslint-style "react-hooks/exhaustive-deps" complaints appear, ignore: no linter runs in CI for the frontend; `[theme]` is the intended dependency.)

- [ ] **Step 5: `index.html` (fonts + no-flash theme)**

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>EQT-Live · Earthquake detection with a distilled model</title>
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link
      href="https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,400;0,9..144,600;1,9..144,400&family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@400;500;600&display=swap"
      rel="stylesheet"
    />
    <script>
      (function () {
        var t;
        try { t = localStorage.getItem("eqt-theme"); } catch (e) {}
        if (t !== "light" && t !== "dark") {
          t = window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
        }
        document.documentElement.dataset.theme = t;
      })();
    </script>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

- [ ] **Step 6: `App.tsx` header, nav, toggle and context**

```tsx
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { api } from "./api/client";
import { AboutPanel } from "./components/AboutPanel";
import { ThemeToggle } from "./components/ThemeToggle";
import { LiveTab } from "./tabs/LiveTab";
import { RecentTab } from "./tabs/RecentTab";
import { ThemeContext, useTheme } from "./theme";

type Tab = "recent" | "live" | "method";

const TABS: [Tab, string][] = [
  ["recent", "Recent"],
  ["live", "Live"],
  ["method", "Method"],
];

export default function App() {
  const [tab, setTab] = useState<Tab>("recent");
  const [theme, toggleTheme] = useTheme();
  const modelsQ = useQuery({ queryKey: ["models"], queryFn: api.models });
  return (
    <ThemeContext.Provider value={theme}>
      <div className="app">
        <header className="topbar">
          <span className="wordmark">EQT·LIVE</span>
          <nav className="nav" aria-label="Sections">
            {TABS.map(([id, label]) => (
              <button
                key={id}
                type="button"
                aria-current={tab === id ? "page" : undefined}
                onClick={() => setTab(id)}
              >
                {label}
              </button>
            ))}
            <ThemeToggle theme={theme} onToggle={toggleTheme} />
          </nav>
        </header>
        <main>
          {tab === "recent" && <RecentTab models={modelsQ.data} />}
          {tab === "live" && <LiveTab models={modelsQ.data} />}
          {tab === "method" && <AboutPanel models={modelsQ.data} />}
        </main>
      </div>
    </ThemeContext.Provider>
  );
}
```

- [ ] **Step 7: Verify and commit**

Run: `npx tsc --noEmit && npx vitest run && npm run build`
Expected: all pass.

```bash
git add frontend/index.html frontend/src/theme.ts frontend/src/theme.test.tsx frontend/src/components/ThemeToggle.tsx frontend/src/App.tsx
git commit -m "feat(frontend): theme module, toggle, no-flash script and new header"
```

---

### Task 2: Stylesheet, intro, lists, map, notes and Method page

**Files:**
- Modify: `frontend/src/styles.css` (full rewrite), `frontend/src/format.ts`, `frontend/src/format.test.ts`, `frontend/src/tabs/RecentTab.tsx`, `frontend/src/tabs/LiveTab.tsx`, `frontend/src/components/EventList.tsx`, `frontend/src/components/EventMap.tsx`, `frontend/src/components/Spinner.tsx`, `frontend/src/components/ErrorBox.tsx`, `frontend/src/components/AboutPanel.tsx`

**Interfaces:**
- Consumes: class names used by Task 1's header (`topbar`, `wordmark`, `nav`, `theme-toggle`).
- Produces: `formatDateline(now?: Date): string` → e.g. `"08 OCT 2026 · 14:21 UTC"`. CSS classes used by later tasks: `verdict`, `verdict-text`, `label`, `scope`, `scope-head`, `scope-legend`, `scope-body`, `comparison`, `q-close`, `q-fair`, `q-far`, `q-none`, `accent`, `table-wrap`.

- [ ] **Step 1: Failing test for `formatDateline`**

Append to `frontend/src/format.test.ts` (keep existing tests):
```ts
import { formatDateline } from "./format";

describe("formatDateline", () => {
  it("formats a UTC dateline", () => {
    expect(formatDateline(new Date("2026-10-08T14:21:07Z"))).toBe("08 OCT 2026 · 14:21 UTC");
  });
});
```
(If `describe`/`expect`/`it` are already imported at the top of the file, do not duplicate the import; add `formatDateline` to the existing `./format` import instead.)

Run: `npx vitest run src/format.test.ts` → FAIL (`formatDateline` is not exported).

- [ ] **Step 2: Implement in `format.ts`**

```ts
const MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"];

export function formatDateline(now: Date = new Date()): string {
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${pad(now.getUTCDate())} ${MONTHS[now.getUTCMonth()]} ${now.getUTCFullYear()} · ${pad(now.getUTCHours())}:${pad(now.getUTCMinutes())} UTC`;
}
```
Run: `npx vitest run src/format.test.ts` → PASS.

- [ ] **Step 3: Rewrite `src/styles.css`**

```css
:root {
  --bg: #f3ede1;
  --ink: #1c1917;
  --muted: #57534e;
  --rule: #d9cdb6;
  --hair: #d9cdb6;
  --line: #1c1917;
  --panel: #fbf8f2;
  --scope: #11100e;
  --scope-line: #2a2622;
  --scope-muted: #9b917f;
  --trace: #7ee0c3;
  --trace-glow: #7ee0c399;
  --teacher: #f2f0ea;
  --student: #ff6b4a;
  --expected: #9b917f;
  --accent: #b42318;
  --good: #2f6b3a;
  --warn: #9a5b00;
  --bad: #b42318;
  --map-filter: grayscale(0.6) sepia(0.15);
  --serif: "Fraunces", Georgia, serif;
  --mono: "IBM Plex Mono", Consolas, monospace;
  --sans: "IBM Plex Sans", "Segoe UI", sans-serif;
  color-scheme: light;
}

:root[data-theme="dark"] {
  --bg: #15120f;
  --ink: #ece4d4;
  --muted: #a1937c;
  --rule: #ffffff0a;
  --hair: #2a241e;
  --line: #3a322a;
  --panel: #0f0d0b;
  --scope: #0f0d0b;
  --scope-line: #2a241e;
  --scope-muted: #a1937c;
  --trace: #ece4d4;
  --trace-glow: #ece4d466;
  --teacher: #5ec4d6;
  --student: #e0a458;
  --expected: #a1937c;
  --accent: #e0a458;
  --good: #8fcf8f;
  --warn: #e0a458;
  --bad: #ff6b4a;
  --map-filter: invert(1) hue-rotate(180deg) brightness(0.85) grayscale(0.5);
  color-scheme: dark;
}

* { box-sizing: border-box; }
html, body { margin: 0; background: var(--bg); }
body {
  color: var(--ink);
  font-family: var(--sans);
  font-size: 15px;
  line-height: 1.5;
  background-image: linear-gradient(var(--rule) 1px, transparent 1px);
  background-size: 100% 18px;
}
:root[data-theme="dark"] body {
  background-image: linear-gradient(var(--rule) 1px, transparent 1px),
    linear-gradient(90deg, #ffffff06 1px, transparent 1px);
  background-size: 100% 18px, 36px 100%;
}
a { color: var(--accent); }
:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
.muted { color: var(--muted); }
.accent { color: var(--accent); }

/* Layout */
.app { max-width: 1180px; margin: 0 auto; padding: 0 20px 48px; }
.topbar {
  display: flex; justify-content: space-between; align-items: center; gap: 16px; flex-wrap: wrap;
  padding: 14px 0; border-bottom: 1.5px solid var(--line);
}
.wordmark { font-family: var(--mono); font-weight: 500; font-size: 14px; letter-spacing: 0.3em; }
.nav { display: flex; align-items: center; gap: 4px; }
.nav button, .theme-toggle {
  font-family: var(--mono); font-size: 12px; letter-spacing: 0.12em; text-transform: uppercase;
  background: none; color: var(--muted); border: 1.5px solid transparent; border-radius: 0;
  padding: 6px 10px; cursor: pointer;
}
.nav button:hover { color: var(--ink); }
.nav button[aria-current="page"] { color: var(--ink); border-color: var(--line); }
.theme-toggle { margin-left: 8px; color: var(--ink); border-color: var(--line); font-size: 14px; text-transform: none; }

/* Intro */
.intro { padding: 28px 0 4px; }
.dateline { font-family: var(--mono); font-size: 12px; letter-spacing: 0.08em; color: var(--accent); }
.headline {
  font-family: var(--serif); font-weight: 400; font-size: clamp(32px, 5vw, 52px);
  line-height: 1.05; margin: 10px 0 12px; letter-spacing: -0.01em;
}
.headline em { color: var(--accent); }
.lede { color: var(--muted); max-width: 62ch; margin: 0; }

/* Panels */
.panel { border: 1.5px solid var(--line); background: var(--panel); padding: 16px; margin: 20px 0; }
.panel h2 { font-family: var(--serif); font-weight: 400; font-size: 26px; margin: 0 0 12px; }
.label, label {
  font-family: var(--mono); font-size: 11px; letter-spacing: 0.14em; text-transform: uppercase; color: var(--muted);
}
select {
  font-family: var(--mono); font-size: 13px; color: var(--ink); background: var(--panel);
  border: 1.5px solid var(--line); border-radius: 0; padding: 4px 6px; margin-left: 8px;
}
.two-col { display: grid; grid-template-columns: 3fr 2fr; gap: 16px; }
@media (max-width: 800px) { .two-col { grid-template-columns: 1fr; } }

/* Map */
.map { height: 380px; border: 1.5px solid var(--line); }
.map .leaflet-tile-pane { filter: var(--map-filter); }
.leaflet-container { background: var(--panel); font-family: var(--sans); }
.quake { stroke: var(--ink); stroke-width: 1px; fill: var(--accent); fill-opacity: 0.35; }
.quake-selected { stroke: var(--accent); stroke-width: 3px; fill-opacity: 0.7; }
.leaflet-tooltip {
  font-family: var(--mono); font-size: 12px; color: var(--ink); background: var(--panel);
  border: 1.5px solid var(--line); border-radius: 0; box-shadow: none;
}

/* Event list */
.event-list {
  list-style: none; padding: 0; margin: 10px 0 0; max-height: 340px; overflow-y: auto;
  border-top: 1.5px solid var(--line);
}
.event-list button {
  width: 100%; display: grid; grid-template-columns: 14px 52px 1fr auto; gap: 8px; align-items: baseline;
  text-align: left; padding: 8px 4px; border: none; border-bottom: 1px solid var(--hair);
  background: none; color: var(--ink); font: inherit; cursor: pointer;
}
.event-list button:hover { background: color-mix(in srgb, var(--accent) 7%, transparent); }
.event-list .marker { color: var(--accent); }
.event-list .mag { font-family: var(--mono); font-weight: 500; }
.event-list .age { font-family: var(--mono); font-size: 12px; color: var(--muted); }

/* Notes, errors, loading */
.note, .error {
  border: 1.5px solid var(--line); border-left: 4px solid var(--accent); background: var(--panel);
  color: var(--ink); padding: 10px 14px; margin: 0 0 16px;
}
.spinner { font-family: var(--mono); font-size: 13px; color: var(--muted); padding: 14px 0; }
.spinner .cursor {
  display: inline-block; width: 0.6em; height: 1em; margin-left: 4px; vertical-align: -2px;
  background: var(--accent); animation: blink 1s steps(1) infinite;
}
@keyframes blink { 50% { opacity: 0; } }
@media (prefers-reduced-motion: reduce) { .spinner .cursor { animation: none; } }

/* Analysis */
.verdict { margin: 20px 0 10px; }
.verdict-text {
  font-family: var(--serif); font-size: clamp(20px, 2.4vw, 26px); line-height: 1.3; margin: 6px 0 0; max-width: 60ch;
}
.scope { background: var(--scope); border: 1.5px solid var(--line); margin: 12px 0; }
.scope-head {
  display: flex; justify-content: space-between; gap: 12px; flex-wrap: wrap; padding: 6px 10px;
  border-bottom: 1px solid var(--scope-line); color: var(--scope-muted);
  font-family: var(--mono); font-size: 11px; letter-spacing: 0.08em; text-transform: uppercase;
}
.scope-legend { display: flex; gap: 12px; }
.scope-legend .teacher { color: var(--teacher); }
.scope-legend .student { color: var(--student); }
.scope-legend .expected { color: var(--expected); }
.scope-body {
  background-image: linear-gradient(90deg, #ffffff08 1px, transparent 1px);
  background-size: 48px 100%;
}
.scope-body .gl-container canvas { filter: drop-shadow(0 0 2px var(--trace-glow)); }

/* Comparison table */
.table-wrap { overflow-x: auto; }
.comparison {
  width: 100%; border-collapse: collapse; border: 1.5px solid var(--line); background: var(--panel);
  font-family: var(--mono); font-size: 13px;
}
.comparison th, .comparison td { padding: 7px 10px; text-align: left; font-weight: 400; border-top: 1px solid var(--hair); }
.comparison thead th { border-top: none; font-size: 11px; letter-spacing: 0.12em; text-transform: uppercase; color: var(--muted); }
.comparison thead th.student { color: var(--accent); }
.q-close { color: var(--good); }
.q-fair { color: var(--warn); }
.q-far { color: var(--bad); }
.q-none { color: var(--muted); }

/* Method article */
.method { max-width: 68ch; }
.method p { margin: 0 0 14px; }
```

- [ ] **Step 4: Markup updates**

`frontend/src/components/Spinner.tsx`:
```tsx
export function Spinner({ text }: { text: string }) {
  return (
    <div className="spinner" role="status">
      {text}
      <span className="cursor" aria-hidden="true" />
    </div>
  );
}
```

`frontend/src/components/ErrorBox.tsx`: keep `describeError` unchanged; the `ErrorBox` component keeps `className="error"` and `role="alert"` (styling comes from CSS). No change needed unless the file differs; leave it.

`frontend/src/components/EventList.tsx`:
```tsx
import type { EqEvent } from "../api/client";
import { timeAgo } from "../format";

interface Props {
  events: EqEvent[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}

export function EventList({ events, selectedId, onSelect }: Props) {
  if (events.length === 0) return <p className="muted">No earthquakes match this filter.</p>;
  return (
    <ul className="event-list">
      {events.map((e) => {
        const selected = e.id === selectedId;
        return (
          <li key={e.id}>
            <button type="button" aria-pressed={selected} onClick={() => onSelect(e.id)}>
              <span className="marker" aria-hidden="true">{selected ? "▸" : ""}</span>
              <span className="mag">M{e.magnitude.toFixed(1)}</span>
              <span>{e.place}</span>
              <span className="age">{timeAgo(e.time)}</span>
            </button>
          </li>
        );
      })}
    </ul>
  );
}
```

`frontend/src/components/EventMap.tsx`: replace the `pathOptions` object with class names so CSS variables apply (Leaflet SVG attributes cannot read `var()`):
```tsx
          pathOptions={{ className: e.id === selectedId ? "quake quake-selected" : "quake" }}
```
(Keep everything else in the file unchanged.)

`frontend/src/tabs/RecentTab.tsx`: add the import `import { formatDateline } from "../format";` and render this intro as the first child of the returned fragment (before the map/list `<section>`):
```tsx
      <section className="intro">
        <div className="dateline">● {formatDateline()}</div>
        <h1 className="headline">
          A 61K-parameter model,
          <br />
          <em>listening to the earth.</em>
        </h1>
        <p className="lede">
          Pick a real earthquake from the last 3 days. We download two minutes of recordings from
          the nearest station and let both models find the P and S waves.
        </p>
      </section>
```
Also change the two loading texts to lowercase mono style: `"loading recent earthquakes"` and `"finding nearby stations"`.

`frontend/src/tabs/LiveTab.tsx`: change `<p className="banner">` to `<p className="note">` (text unchanged) and the spinner text to `"loading stations"`.

`frontend/src/components/AboutPanel.tsx`: change the wrapper to `<section className="panel method">` and the heading text from `About` to `Method`. Text otherwise unchanged.

- [ ] **Step 5: Verify and commit**

Run: `npx tsc --noEmit && npx vitest run && npm run build`
Expected: all pass (existing RecentTab test still passes; it mocks the map and the analysis view).

```bash
git add frontend/src
git commit -m "feat(frontend): paper/instrument stylesheet, intro, themed list, map and notes"
```

---

### Task 3: Verdict logic

**Files:**
- Create: `frontend/src/verdict.ts`, `frontend/src/verdict.test.ts`

**Interfaces:**
- Consumes: `AnalysisResult`, `ModelResult` from `src/api/client.ts`; `secondsBetween(fromIso, toIso)` from `src/format.ts`.
- Produces:
  - `type PickQuality = "close" | "fair" | "far" | "none"`
  - `pickQuality(pick: string | null, expected: string | null): PickQuality | null`
  - `formatDelta(seconds: number): string` → `"+0.27 s"`, `"-0.50 s"`
  - `speedup(r: AnalysisResult): number | null`
  - `verdictSentence(r: AnalysisResult): string`

- [ ] **Step 1: Write the failing tests**

`frontend/src/verdict.test.ts`:
```ts
import { describe, expect, it } from "vitest";
import type { AnalysisResult, ModelResult } from "./api/client";
import { formatDelta, pickQuality, speedup, verdictSentence } from "./verdict";

const T0 = "2026-10-08T12:00:00Z";
const at = (s: number) => new Date(Date.parse(T0) + s * 1000).toISOString();
const curves = { detection: [], p: [], s: [] };

function model(detected: boolean, p: number | null, latency: number): ModelResult {
  return {
    detected, detection_max: detected ? 0.95 : 0.2, p_time: p === null ? null : at(p), s_time: null,
    p_conf: p === null ? null : 0.8, s_conf: null, latency_ms: latency, curves,
  };
}

function result(t: ModelResult, s: ModelResult, expectedP: number | null): AnalysisResult {
  return {
    station: "C.GO01..BH", distance_km: 15, start_time: T0, display_dt: 0.04,
    waveform: { z: [], n: [], e: [] },
    theoretical: { p_time: expectedP === null ? null : at(expectedP), s_time: null },
    teacher: t, student: s,
  };
}

describe("pickQuality", () => {
  it("grades by distance from the expected arrival", () => {
    expect(pickQuality(at(31), at(30))).toBe("close");
    expect(pickQuality(at(31.01), at(30))).toBe("fair");
    expect(pickQuality(at(27), at(30))).toBe("fair");
    expect(pickQuality(at(33.01), at(30))).toBe("far");
    expect(pickQuality(null, at(30))).toBe("none");
    expect(pickQuality(at(31), null)).toBeNull();
  });
});

describe("formatDelta and speedup", () => {
  it("formats signed seconds", () => {
    expect(formatDelta(0.27)).toBe("+0.27 s");
    expect(formatDelta(-0.5)).toBe("-0.50 s");
  });
  it("computes teacher/student latency ratio", () => {
    expect(speedup(result(model(true, 30, 58), model(true, 30, 38), 30))).toBeCloseTo(1.526, 2);
    expect(speedup(result(model(true, 30, 58), model(true, 30, 0), 30))).toBeNull();
  });
});

describe("verdictSentence: event mode", () => {
  it("neither detected", () => {
    expect(verdictSentence(result(model(false, null, 10), model(false, null, 5), 30))).toBe(
      "Neither model detected the earthquake at this station. It may be too weak or too far away. Try a closer station.",
    );
  });
  it("both close, student matched", () => {
    expect(verdictSentence(result(model(true, 30.27, 10), model(true, 30.34, 2), 30))).toBe(
      "Both models found the P wave within 0.34 s of the expected arrival. The student matched the teacher and ran 5.0× faster.",
    );
  });
  it("both fair, student clearly worse", () => {
    expect(verdictSentence(result(model(true, 30.2, 10), model(true, 32.5, 5), 30))).toBe(
      "Both models found the P wave within 2.50 s of the expected arrival. The student came close to the teacher and ran 2.0× faster.",
    );
  });
  it("only the teacher, student did not pick", () => {
    expect(verdictSentence(result(model(true, 30.27, 10), model(true, null, 5), 30))).toBe(
      "Only the teacher found the P wave near the expected arrival (+0.27 s). The other did not pick it.",
    );
  });
  it("only the student, teacher picked something else", () => {
    expect(verdictSentence(result(model(true, 42, 10), model(true, 29.5, 5), 30))).toBe(
      "Only the student found the P wave near the expected arrival (-0.50 s). The other picked a different arrival, probably another event.",
    );
  });
  it("both detected but neither picked", () => {
    expect(verdictSentence(result(model(true, null, 10), model(true, null, 5), 30))).toBe(
      "Both models detected the earthquake, but neither was confident about the exact P arrival.",
    );
  });
  it("both far", () => {
    expect(verdictSentence(result(model(true, 40, 10), model(true, 45, 5), 30))).toBe(
      "The models detected seismic activity but picked arrivals far from the expected time, likely a different event in the window.",
    );
  });
});

describe("verdictSentence: live mode", () => {
  it("quiet", () => {
    expect(verdictSentence(result(model(false, null, 10), model(false, null, 5), null))).toBe(
      "Quiet: neither model detected an earthquake in the last two minutes.",
    );
  });
  it("both", () => {
    expect(verdictSentence(result(model(true, 30, 10), model(true, 30, 5), null))).toBe(
      "Both models detected seismic activity.",
    );
  });
  it("teacher only", () => {
    expect(verdictSentence(result(model(true, 30, 10), model(false, null, 5), null))).toBe(
      "The teacher flags activity but the student does not. The original model often over-triggers on quiet live noise.",
    );
  });
  it("student only", () => {
    expect(verdictSentence(result(model(false, null, 10), model(true, 30, 5), null))).toBe(
      "The student flags activity but the teacher does not.",
    );
  });
});
```

- [ ] **Step 2: Run to verify failure**

Run: `npx vitest run src/verdict.test.ts`
Expected: FAIL — cannot resolve `./verdict`.

- [ ] **Step 3: Implement `src/verdict.ts`**

```ts
import type { AnalysisResult } from "./api/client";
import { secondsBetween } from "./format";

export type PickQuality = "close" | "fair" | "far" | "none";

export function pickQuality(pick: string | null, expected: string | null): PickQuality | null {
  if (!expected) return null;
  if (!pick) return "none";
  const d = Math.abs(secondsBetween(expected, pick));
  if (d <= 1) return "close";
  if (d <= 3) return "fair";
  return "far";
}

export function formatDelta(seconds: number): string {
  return `${seconds >= 0 ? "+" : "-"}${Math.abs(seconds).toFixed(2)} s`;
}

export function speedup(r: AnalysisResult): number | null {
  return r.student.latency_ms > 0 ? r.teacher.latency_ms / r.student.latency_ms : null;
}

const usable = (q: PickQuality | null) => q === "close" || q === "fair";

export function verdictSentence(r: AnalysisResult): string {
  const { teacher: t, student: s } = r;
  const expected = r.theoretical.p_time;

  if (!expected) {
    if (!t.detected && !s.detected) return "Quiet: neither model detected an earthquake in the last two minutes.";
    if (t.detected && s.detected) return "Both models detected seismic activity.";
    if (t.detected) {
      return "The teacher flags activity but the student does not. The original model often over-triggers on quiet live noise.";
    }
    return "The student flags activity but the teacher does not.";
  }

  if (!t.detected && !s.detected) {
    return "Neither model detected the earthquake at this station. It may be too weak or too far away. Try a closer station.";
  }
  const tq = pickQuality(t.p_time, expected);
  const sq = pickQuality(s.p_time, expected);
  if (usable(tq) && usable(sq)) {
    const td = Math.abs(secondsBetween(expected, t.p_time!));
    const sd = Math.abs(secondsBetween(expected, s.p_time!));
    const verb = sd <= td + 0.5 ? "matched" : "came close to";
    const ratio = speedup(r);
    const speed = ratio ? ` and ran ${ratio.toFixed(1)}× faster` : "";
    return `Both models found the P wave within ${Math.max(td, sd).toFixed(2)} s of the expected arrival. The student ${verb} the teacher${speed}.`;
  }
  if (usable(tq) || usable(sq)) {
    const winner = usable(tq) ? t : s;
    const other = usable(tq) ? s : t;
    const who = usable(tq) ? "teacher" : "student";
    const otherText = other.p_time ? "picked a different arrival, probably another event" : "did not pick it";
    return `Only the ${who} found the P wave near the expected arrival (${formatDelta(secondsBetween(expected, winner.p_time!))}). The other ${otherText}.`;
  }
  if (tq === "none" && sq === "none") {
    return "Both models detected the earthquake, but neither was confident about the exact P arrival.";
  }
  return "The models detected seismic activity but picked arrivals far from the expected time, likely a different event in the window.";
}
```

- [ ] **Step 4: Run tests**

Run: `npx vitest run src/verdict.test.ts`
Expected: 14 passed.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/verdict.ts frontend/src/verdict.test.ts
git commit -m "feat(frontend): plain-language verdict and pick-quality grading"
```

---

### Task 4: Comparison table and analysis view

**Files:**
- Modify: `frontend/src/components/ComparisonCard.tsx`, `frontend/src/components/ComparisonCard.test.tsx`, `frontend/src/components/AnalysisView.tsx`

**Interfaces:**
- Consumes: `pickQuality`, `formatDelta`, `speedup`, `verdictSentence` (Task 3); `formatUtcTime`, `secondsBetween` (format.ts); CSS classes from Task 2.
- Produces: `<ComparisonCard result models? />` (same props as before), `<AnalysisView query models? />` (same props).

- [ ] **Step 1: Replace the ComparisonCard tests**

`frontend/src/components/ComparisonCard.test.tsx`:
```tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { AnalysisResult, ModelResult } from "../api/client";
import { ComparisonCard } from "./ComparisonCard";

const curves = { detection: [], p: [], s: [] };
const teacher: ModelResult = {
  detected: true, detection_max: 0.98, p_time: "2026-10-07T12:00:30Z", s_time: "2026-10-07T12:00:41Z",
  p_conf: 0.9, s_conf: 0.8, latency_ms: 10, curves,
};
const student: ModelResult = { ...teacher, p_time: "2026-10-07T12:00:30.07Z", s_time: null, latency_ms: 2 };
const base: AnalysisResult = {
  station: "IU.MAJO.00.BH", distance_km: 120, start_time: "2026-10-07T12:00:00Z", display_dt: 0.04,
  waveform: { z: [], n: [], e: [] },
  theoretical: { p_time: "2026-10-07T12:00:29.73Z", s_time: "2026-10-07T12:00:38.90Z" },
  teacher, student,
};
const models = {
  teacher: { name: "teacher", params: 373495, size_mb: 4.85 },
  student: { name: "student", params: 60659, size_mb: 0.39 },
  compression: 6.16,
};

describe("ComparisonCard", () => {
  it("grades picks against the expected arrival", () => {
    render(<ComparisonCard result={base} models={models} />);
    expect(screen.getByText("● +0.27 s close")).toBeInTheDocument();
    expect(screen.getByText("● +0.34 s close")).toBeInTheDocument();
    expect(screen.getByText("● +2.10 s fair")).toBeInTheDocument();
    expect(screen.getByText("— not picked")).toBeInTheDocument();
  });

  it("shows speed-up, model sizes and no emoji", () => {
    const { container } = render(<ComparisonCard result={base} models={models} />);
    expect(screen.getByText("Teacher 373K")).toBeInTheDocument();
    expect(screen.getByText("Student 61K")).toBeInTheDocument();
    expect(screen.getByText(/5\.0× faster/)).toBeInTheDocument();
    expect(screen.getByText(/6\.2× fewer parameters/)).toBeInTheDocument();
    expect(container.textContent).not.toMatch(/[✅⚡]/u);
  });

  it("shows absolute times in live mode (no expected arrival)", () => {
    const live = { ...base, theoretical: { p_time: null, s_time: null } };
    render(<ComparisonCard result={live} />);
    expect(screen.getByText("P arrival (UTC)")).toBeInTheDocument();
    expect(screen.getByText("12:00:30.00")).toBeInTheDocument();
    expect(screen.getByText("Teacher")).toBeInTheDocument();
    expect(screen.queryByText("Model size")).not.toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run to verify failure**

Run: `npx vitest run src/components/ComparisonCard.test.tsx`
Expected: FAIL (old markup: "Teacher (373K)", "⚡ 5.0x faster", no quality cells).

- [ ] **Step 3: Implement `ComparisonCard.tsx`**

```tsx
import type { AnalysisResult, ModelResult, ModelsInfo } from "../api/client";
import { formatUtcTime, secondsBetween } from "../format";
import { formatDelta, pickQuality, speedup } from "../verdict";

function header(label: string, params?: number): string {
  return params ? `${label} ${Math.round(params / 1000)}K` : label;
}

function detected(r: ModelResult): string {
  return `${r.detected ? "yes" : "no"} · ${r.detection_max.toFixed(2)}`;
}

function PickCell({ pick, expected }: { pick: string | null; expected: string | null }) {
  const quality = pickQuality(pick, expected);
  if (quality === null) return <td>{formatUtcTime(pick)}</td>;
  if (quality === "none") return <td className="q-none">— not picked</td>;
  return <td className={`q-${quality}`}>{`● ${formatDelta(secondsBetween(expected!, pick!))} ${quality}`}</td>;
}

export function ComparisonCard({ result, models }: { result: AnalysisResult; models?: ModelsInfo }) {
  const { teacher, student, theoretical } = result;
  const event = theoretical.p_time !== null;
  const ratio = speedup(result);
  return (
    <table className="comparison">
      <thead>
        <tr>
          <th />
          <th>{header("Teacher", models?.teacher.params)}</th>
          <th className="student">{header("Student", models?.student.params)}</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td>Detected</td>
          <td>{detected(teacher)}</td>
          <td>{detected(student)}</td>
        </tr>
        <tr>
          <td>{event ? "P vs expected" : "P arrival (UTC)"}</td>
          <PickCell pick={teacher.p_time} expected={theoretical.p_time} />
          <PickCell pick={student.p_time} expected={theoretical.p_time} />
        </tr>
        <tr>
          <td>{event ? "S vs expected" : "S arrival (UTC)"}</td>
          <PickCell pick={teacher.s_time} expected={theoretical.s_time} />
          <PickCell pick={student.s_time} expected={theoretical.s_time} />
        </tr>
        <tr>
          <td>Inference / window</td>
          <td>{teacher.latency_ms.toFixed(1)} ms</td>
          <td>
            {student.latency_ms.toFixed(1)} ms
            {ratio ? <span className="accent">{` · ${ratio.toFixed(1)}× faster`}</span> : null}
          </td>
        </tr>
        {models && (
          <tr>
            <td>Model size</td>
            <td>{models.teacher.size_mb.toFixed(2)} MB</td>
            <td>
              {models.student.size_mb.toFixed(2)} MB
              <span className="accent">{` · ${models.compression.toFixed(1)}× fewer parameters`}</span>
            </td>
          </tr>
        )}
      </tbody>
    </table>
  );
}
```

- [ ] **Step 4: Run tests**

Run: `npx vitest run src/components/ComparisonCard.test.tsx`
Expected: 3 passed.

- [ ] **Step 5: Implement `AnalysisView.tsx`**

```tsx
import type { UseQueryResult } from "@tanstack/react-query";
import type { AnalysisResult, ModelsInfo } from "../api/client";
import { formatUtcTime } from "../format";
import { verdictSentence } from "../verdict";
import { ComparisonCard } from "./ComparisonCard";
import { ErrorBox } from "./ErrorBox";
import { ProbabilityChart } from "./ProbabilityChart";
import { Spinner } from "./Spinner";
import { WaveformChart } from "./WaveformChart";

interface Props {
  query: UseQueryResult<AnalysisResult>;
  models?: ModelsInfo;
}

export function AnalysisView({ query, models }: Props) {
  if (query.isPending) return <Spinner text="acquiring waveform, running both models" />;
  if (query.isError && !query.data) return <ErrorBox error={query.error} />;
  const result = query.data!;
  const where = result.distance_km != null ? ` · ${result.distance_km.toFixed(0)} km from epicenter` : "";
  return (
    <div>
      {query.isError && <ErrorBox error={query.error} />}
      <div className="verdict">
        <div className="label">{`Verdict · ${result.station}${where}`}</div>
        <p className="verdict-text">{verdictSentence(result)}</p>
      </div>

      <div className="scope">
        <div className="scope-head">
          <span>{`Waveform · Z / N / E · from ${formatUtcTime(result.start_time)} UTC`}</span>
          <span className="scope-legend">
            <span className="teacher">— teacher</span>
            <span className="student">- - student</span>
            <span className="expected">··· expected</span>
          </span>
        </div>
        <div className="scope-body">
          <WaveformChart result={result} />
        </div>
      </div>

      <div className="scope">
        <div className="scope-head">
          <span>Model output · probability</span>
          <span className="scope-legend">
            <span className="teacher">— teacher</span>
            <span className="student">- - student</span>
          </span>
        </div>
        <div className="scope-body">
          <ProbabilityChart result={result} />
        </div>
      </div>

      <div className="table-wrap">
        <ComparisonCard result={result} models={models} />
      </div>
    </div>
  );
}
```

- [ ] **Step 6: Verify and commit**

Run: `npx tsc --noEmit && npx vitest run && npm run build`
Expected: all pass.

```bash
git add frontend/src/components/ComparisonCard.tsx frontend/src/components/ComparisonCard.test.tsx frontend/src/components/AnalysisView.tsx
git commit -m "feat(frontend): verdict line, instrument panels and graded comparison table"
```

---

### Task 5: Themed charts

**Files:**
- Modify: `frontend/src/components/WaveformChart.tsx`, `frontend/src/components/ProbabilityChart.tsx`

**Interfaces:**
- Consumes: `useThemeColors(): ThemeColors` (Task 1).

- [ ] **Step 1: `WaveformChart.tsx`**

```tsx
import type { AnalysisResult } from "../api/client";
import { secondsBetween } from "../format";
import { useThemeColors, type ThemeColors } from "../theme";
import { Plot } from "./Plot";

const HEIGHT = 360;
const FONT = { family: "IBM Plex Mono, Consolas, monospace", size: 10 };

function pickLines(result: AnalysisResult, c: ThemeColors) {
  const sources = [
    { times: result.teacher, color: c.teacher, dash: "solid" },
    { times: result.student, color: c.student, dash: "dash" },
    { times: result.theoretical, color: c.expected, dash: "dot" },
  ];
  const shapes: object[] = [];
  const annotations: object[] = [];
  for (const source of sources) {
    for (const [phase, time] of [["P", source.times.p_time], ["S", source.times.s_time]] as const) {
      if (!time) continue;
      const x = secondsBetween(result.start_time, time);
      shapes.push({ type: "line", xref: "x", yref: "paper", x0: x, x1: x, y0: 0, y1: 1,
                    line: { color: source.color, dash: source.dash, width: 1.5 } });
      annotations.push({ x, y: 1, xref: "x", yref: "paper", text: phase, showarrow: false,
                         yanchor: "bottom", font: { ...FONT, color: source.color } });
    }
  }
  return { shapes, annotations };
}

export function WaveformChart({ result }: { result: AnalysisResult }) {
  const c = useThemeColors();
  const x = result.waveform.z.map((_, i) => i * result.display_dt);
  const channels = [
    ["Z", result.waveform.z, "y"],
    ["N", result.waveform.n, "y2"],
    ["E", result.waveform.e, "y3"],
  ] as const;
  const { shapes, annotations } = pickLines(result, c);
  const axis = { gridcolor: c.hair, zeroline: false, linecolor: c.hair, tickfont: FONT, color: c.muted };
  return (
    <Plot
      data={channels.map(([name, y, yaxis]) => ({
        x, y, name, yaxis, type: "scattergl", mode: "lines",
        line: { width: 1.2, color: c.trace }, showlegend: false,
      }))}
      layout={{
        height: HEIGHT, margin: { l: 44, r: 12, t: 22, b: 36 },
        paper_bgcolor: "rgba(0,0,0,0)", plot_bgcolor: "rgba(0,0,0,0)", font: { ...FONT, color: c.muted },
        grid: { rows: 3, columns: 1, pattern: "coupled" },
        xaxis: { ...axis, title: { text: "seconds", font: FONT } },
        yaxis: { ...axis, title: { text: "Z", font: FONT } },
        yaxis2: { ...axis, title: { text: "N", font: FONT } },
        yaxis3: { ...axis, title: { text: "E", font: FONT } },
        shapes, annotations,
      }}
      config={{ displaylogo: false, responsive: true }}
      style={{ width: "100%", height: HEIGHT }}
    />
  );
}
```

- [ ] **Step 2: `ProbabilityChart.tsx`**

```tsx
import type { AnalysisResult } from "../api/client";
import { useThemeColors } from "../theme";
import { Plot } from "./Plot";

const HEIGHT = 260;
const FONT = { family: "IBM Plex Mono, Consolas, monospace", size: 10 };

export function ProbabilityChart({ result }: { result: AnalysisResult }) {
  const c = useThemeColors();
  const curves = [
    ["detection", "detection", c.expected],
    ["p", "P", c.trace],
    ["s", "S", c.student],
  ] as const;
  const x = result.teacher.curves.p.map((_, i) => i * result.display_dt);
  const data = (["teacher", "student"] as const).flatMap((model) =>
    curves.map(([key, label, color]) => ({
      x, y: result[model].curves[key], name: `${model} ${label}`,
      type: "scattergl", mode: "lines",
      line: { color, width: 1.4, dash: model === "teacher" ? "solid" : "dash" },
    })),
  );
  const axis = { gridcolor: c.hair, zeroline: false, linecolor: c.hair, tickfont: FONT, color: c.muted };
  return (
    <Plot
      data={data}
      layout={{
        height: HEIGHT, margin: { l: 44, r: 12, t: 10, b: 36 },
        paper_bgcolor: "rgba(0,0,0,0)", plot_bgcolor: "rgba(0,0,0,0)", font: { ...FONT, color: c.muted },
        yaxis: { ...axis, range: [0, 1.05], title: { text: "probability", font: FONT } },
        xaxis: { ...axis, title: { text: "seconds", font: FONT } },
        legend: { orientation: "h", font: { ...FONT, color: c.muted } },
      }}
      config={{ displaylogo: false, responsive: true }}
      style={{ width: "100%", height: HEIGHT }}
    />
  );
}
```

- [ ] **Step 3: Verify and commit**

Run: `npx tsc --noEmit && npx vitest run && npm run build`
Expected: all pass.

```bash
git add frontend/src/components/WaveformChart.tsx frontend/src/components/ProbabilityChart.tsx
git commit -m "feat(frontend): charts follow the active theme"
```

---

### Task 6: Browser verification and deploy (controller)

- [ ] **Step 1:** Start the `eqt-backend` and `eqt-frontend` preview configs (Desktop `.claude/launch.json`). At 1280×900 and 375×812, in both themes, check:
  - Recent: intro, map + list, then select a Chilean event → verdict, both scopes and the table render.
  - Live tab: note + analysis.
  - Method tab.
  - Toggle persists across a reload.
  - No layout overflow at 375 px except the table's own horizontal scroll.
- [ ] **Step 2:** Screenshots of light and dark go to the user. Fix any defects found by dispatching a fix task (do not hand-edit).
- [ ] **Step 3:** `git push` (main) → CI deploys to Cloud Run. Verify the live URL and refresh `docs/screenshot.jpg` with a new light-theme screenshot.
