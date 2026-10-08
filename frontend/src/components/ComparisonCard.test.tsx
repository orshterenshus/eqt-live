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

  it("omits the speed annotation when latencies are equal", () => {
    const same = { ...base, student: { ...student, latency_ms: 10 } };
    render(<ComparisonCard result={same} models={models} />);
    expect(screen.queryByText(/faster/)).not.toBeInTheDocument();
  });

  it("shows absolute times in live mode (no expected arrival)", () => {
    const live = { ...base, theoretical: { p_time: null, s_time: null } };
    const { container } = render(<ComparisonCard result={live} />);
    expect(screen.getByText("P arrival (UTC)")).toBeInTheDocument();
    expect(screen.getByText("12:00:30.00")).toBeInTheDocument();
    expect(screen.getByText("Teacher")).toBeInTheDocument();
    expect(screen.queryByText("Model size")).not.toBeInTheDocument();
    expect(container.textContent).not.toMatch(/●/);
  });

  it("does not grade the pick of an undetected model", () => {
    const r = { ...base, teacher: { ...teacher, detected: false } };
    render(<ComparisonCard result={r} models={models} />);
    expect(screen.queryByText("● +0.27 s close")).not.toBeInTheDocument();
    expect(screen.getAllByText("— not picked").length).toBeGreaterThanOrEqual(2);
  });

  it("grades a distant pick as far", () => {
    const r = { ...base, student: { ...student, p_time: "2026-10-07T12:00:34.73Z" } };
    render(<ComparisonCard result={r} models={models} />);
    expect(screen.getByText("● +5.00 s far")).toBeInTheDocument();
  });
});
