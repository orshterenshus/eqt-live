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
