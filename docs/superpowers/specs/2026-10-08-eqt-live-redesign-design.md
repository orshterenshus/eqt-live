# EQT-Live Visual Redesign: Design

**Date:** 2026-10-08
**Status:** Approved direction (mockups in `.superpowers/brainstorm/4347-1791466559/content/`)

## 1. Goal

Make the site attractive, distinctive and easy to understand for a non-expert visitor (a
recruiter). Two problems to solve:

1. **Look.** The current UI is a generic light dashboard. It should feel like a crafted
   seismology instrument, not an AI-generated template.
2. **Clarity.** A visitor cannot tell whether the result is good. Each analysis needs a
   plain-language verdict and per-pick quality labels.

Out of scope: backend/API changes, new features, page restructuring (no landing page), and the
pick-selection algorithm.

## 2. Visual direction

Two themes that share one layout, with a toggle:

| | Light: "Paper + Instrument" (default) | Dark: "Night Drum" |
|---|---|---|
| Page | Cream seismograph paper `#f3ede1` with faint horizontal ruling (18 px) | Warm charcoal `#15120f` with very faint ruling and vertical grid |
| Ink / text | `#1c1917`, muted `#57534e` | `#ece4d4`, muted `#a1937c` |
| Lines / borders | 1.5 px solid ink, **square corners**, no shadows | 1.5 px `#3a322a`, square corners, no shadows |
| Chart panel ("instrument screen") | Dark inset `#11100e`; trace glows mint `#7ee0c3` | `#0f0d0b`; trace cream `#ece4d4` with a slight glow |
| Accent (student, emphasis) | Vermilion `#b42318` (on paper), `#ff6b4a` (inside the dark scope) | Amber `#e0a458` |
| Teacher | Ink / off-white `#f2f0ea` inside the scope | Cyan `#5ec4d6` |
| Expected (theoretical) | Muted, dotted | Muted, dotted |
| Quality colors | good `#2f6b3a`, warn `#9a5b00`, bad = accent | good `#8fcf8f`, warn `#e0a458`, bad `#ff6b4a` |

Typography (Google Fonts, `display=swap`):
- **Fraunces** (serif, italic for emphasis): headline and verdict sentence.
- **IBM Plex Mono:** wordmark `EQT·LIVE`, labels, station codes, times, numbers, tables.
- **IBM Plex Sans:** body text and controls.

"Not AI-looking" rules: no emoji anywhere (remove the 🌍 logo, ✅, ⚡), no rounded cards or drop
shadows, no gradients except the paper ruling and the subtle trace glow, at most one accent
color per theme, and technical labels (station codes, UTC times, units) in small-caps mono.

All colors are CSS custom properties on `:root` and `:root[data-theme="dark"]`. Charts read the
same tokens (see §5).

## 3. Theme toggle

- A `☾ / ☀` text button in the header. It renders text, not emoji glyph icons; use the plain
  characters `☾`/`☀` styled as mono text.
- Initial theme: `localStorage["eqt-theme"]` if set, otherwise `prefers-color-scheme`. The choice
  is applied to `document.documentElement.dataset.theme` before first paint (inline script in
  `index.html`) to avoid a flash.
- Toggling persists to `localStorage` (wrapped in try/catch).

## 4. Page structure (same tabs as today)

1. **Header bar:** wordmark `EQT·LIVE` (mono, letter-spaced), nav `RECENT · LIVE · METHOD` (the
   current "About" tab renamed "Method"), theme toggle. A 1.5 px ink rule underneath.
2. **Intro (Recent tab):** a mono dateline in the accent color (`● <today> · <UTC time>`), a
   Fraunces headline "A 61K-parameter model, *listening to the earth.*", and one line of
   explanation: "Pick a real earthquake from the last 3 days. We download two minutes of
   recordings from the nearest station and let both models find the P and S waves."
3. **Map + event list:** same function. Map tiles are muted to fit the theme (CSS filter
   `grayscale(.6) sepia(.15)` in light; `invert(1) hue-rotate(180deg) brightness(.85) grayscale(.5)`
   in dark). Markers are square-ish accent dots; the selected one uses the accent color. List rows
   use mono magnitude and age, a hairline divider, and a selected row marked with `▸` in accent.
4. **Analysis:**
   - **Verdict** (new, §6): mono label `VERDICT · <station> · <distance> km from epicenter`, then
     one Fraunces sentence.
   - **Waveform chart** inside the instrument screen, header strip `BHZ/N/E · <rate> HZ` with the
     legend `— teacher  - - student  ··· expected`.
   - **Probability chart** in the same instrument style.
   - **Comparison table** (restyled ComparisonCard, §7).
5. **Live tab:** same structure; the intro is replaced by the existing banner text restyled as a
   bordered note.
6. **Method tab** (former About): same content, typeset as a short article (Fraunces headings,
   max-width ~65ch).

Responsive: under 800 px, map and list stack. The verdict sentence wraps naturally, and the table
scrolls horizontally if needed.

## 5. Charts (Plotly)

- Transparent `paper_bgcolor`/`plot_bgcolor`; the instrument-screen container provides the
  background and a vertical grid via CSS.
- Colors come from the current theme's tokens (read with `getComputedStyle` at render time,
  with a hook that re-renders on theme change).
- Trace: theme trace color, width 1.2. The glow is a CSS `filter: drop-shadow` on the plot's SVG
  trace layer (light: mint glow; dark: subtle cream glow).
- Picks: teacher solid, student dashed (accent), expected dotted (muted). Phase letters P/S in mono.
- Axis text in IBM Plex Mono 10 px, muted; gridlines hairline.

## 6. Verdict (new pure logic, tested)

`src/verdict.ts` exports:

```ts
type PickQuality = "close" | "fair" | "far" | "none";
function pickQuality(pick: string | null, expected: string | null): PickQuality | null;
// null when expected is null (live mode); "none" when pick is null;
// |Δ| <= 1 s → close; <= 3 s → fair; > 3 s → far.
function verdictSentence(r: AnalysisResult): string;
```

Sentence rules, first match wins. The source of truth is `src/verdict.ts` and its tests.

Event mode (theoretical P available; an undetected model's pick counts as absent):
1. Neither detected → "Neither model detected the earthquake at this station. It may be too weak or
   too far away. Try a closer station."
2. Exactly one detected → "Only the {model} detected the earthquake at this station; its P pick is
   {Δ} from the expected arrival." (or "…, but it did not pick an exact P arrival.")
3. Both P picks close or fair → "Both models found the P wave within {max|Δ|} s of the expected
   arrival. The student {matched|came close to} the teacher{speed}." Here "matched" means the
   student's |Δ| ≤ the teacher's + 0.5 s. {speed} is " and ran {r}× faster" if r ≥ 1.05, " and ran at
   a similar speed" if 0.95 ≤ r < 1.05, and nothing otherwise.
4. Exactly one usable → "Only the {model} found the P wave near the expected arrival ({Δ}). The other
   {did not pick it | picked a different arrival (another event or a mis-pick)}."
5. Neither picked → "Both models detected the earthquake, but neither was confident about the exact
   P arrival."
6. One far, the other not picked → "The {model} picked an arrival far from the expected time ({Δ}),
   and the other model did not pick P."
7. Both far → "Both models detected seismic activity but picked arrivals far from the expected time,
   possibly a different event in the window."

Live mode (no theoretical): "Quiet: neither model detected an earthquake in the last two minutes." /
"Both models detected seismic activity." / "The teacher flags activity but the student does not. In
our tests on live data, the original model often over-triggers on quiet noise." / "The student flags
activity but the teacher does not."

The speedup is formatted with 1 decimal place. Δ values use 2 significant decimals with an explicit
sign. Vitest covers every branch.

## 7. Comparison table

Rows: Detected (yes/no + max prob), P vs expected, S vs expected, Inference, Model size. Cells
for P and S show `● +0.27 s close` colored by quality. Live mode shows the absolute UTC time
instead of Δ (no expected arrival). Columns: `TEACHER 373K` and `STUDENT 61K` (accent). Square
borders and mono text. The speedup is shown in accent.

## 8. Error, loading, empty states

Restyle only: the spinner becomes a small mono "acquiring waveform…" line with a blinking
cursor block; ErrorBox becomes a bordered note with an accent left rule. The existing copy is
unchanged.

## 9. Testing & verification

- New Vitest: `verdict.test.ts` (all branches), a ComparisonCard update (quality labels), and a
  theme-toggle test (sets `data-theme`, persists, survives a `localStorage` throw).
- Existing tests are updated for the changed copy and labels; tsc, vitest and build must pass.
- A browser check of both themes at 1280 px and 375 px, Recent and Live, with screenshots.
- No backend changes; the backend suite stays at 88.

## 10. Files

- Modify: `index.html` (fonts preload + no-flash theme script), `styles.css` (rewrite to tokens),
  `App.tsx` (header, toggle, Method tab), `RecentTab.tsx`/`LiveTab.tsx` (intro/banner markup),
  `AnalysisView.tsx` (verdict, instrument containers), `WaveformChart.tsx`, `ProbabilityChart.tsx`
  (theme colors), `ComparisonCard.tsx`, `EventList.tsx`, `EventMap.tsx`, `ErrorBox.tsx`,
  `Spinner.tsx`, `AboutPanel.tsx` (Method typesetting).
- Create: `src/verdict.ts` + test, `src/theme.ts` (read/apply/persist + `useThemeColors` hook)
  + test, `src/components/ThemeToggle.tsx`.
