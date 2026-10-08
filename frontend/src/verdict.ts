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
