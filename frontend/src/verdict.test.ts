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
