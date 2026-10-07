import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { AnalysisResult, ModelResult } from "../api/client";
import { ComparisonCard } from "./ComparisonCard";

const curves = { detection: [], p: [], s: [] };
const teacher: ModelResult = {
  detected: true, detection_max: 0.98, p_time: "2026-10-07T12:00:30Z", s_time: "2026-10-07T12:00:41Z",
  p_conf: 0.9, s_conf: 0.8, latency_ms: 10, curves,
};
const student: ModelResult = { ...teacher, p_time: "2026-10-07T12:00:30.07Z", latency_ms: 2 };
const result: AnalysisResult = {
  station: "IU.MAJO.00.BH", distance_km: 120, start_time: "2026-10-07T12:00:00Z", display_dt: 0.04,
  waveform: { z: [], n: [], e: [] }, theoretical: { p_time: null, s_time: null }, teacher, student,
};
const models = {
  teacher: { name: "teacher", params: 373495, size_mb: 4.85 },
  student: { name: "student", params: 60659, size_mb: 0.39 },
  compression: 6.16,
};

describe("ComparisonCard", () => {
  it("shows speed-up, pick difference and model sizes", () => {
    render(<ComparisonCard result={result} models={models} />);
    expect(screen.getByText("⚡ 5.0x faster")).toBeInTheDocument();
    expect(screen.getByText("(Δ 0.07 s)")).toBeInTheDocument();
    expect(screen.getByText("Teacher (373K)")).toBeInTheDocument();
    expect(screen.getByText("Student (61K)")).toBeInTheDocument();
    expect(screen.getByText("6.2x fewer parameters")).toBeInTheDocument();
  });

  it("works without model info", () => {
    render(<ComparisonCard result={result} />);
    expect(screen.getByText("Teacher")).toBeInTheDocument();
    expect(screen.queryByText("Model size")).not.toBeInTheDocument();
  });
});
