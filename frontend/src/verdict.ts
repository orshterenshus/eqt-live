import type { AnalysisResult } from "./api/client";
import { secondsBetween } from "./format";

export type PickQuality = "close" | "fair" | "far" | "none";

export function pickQuality(pick: string | null, expected: string | null): PickQuality | null {
  if (!expected) return null;
  if (!pick) return "none";
  const d = Math.abs(secondsBetween(expected, pick));
  if (Number.isNaN(d)) return "none";
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

function speedClause(ratio: number | null): string {
  if (ratio !== null && ratio >= 1.05) return ` and ran ${ratio.toFixed(1)}× faster`;
  if (ratio !== null && ratio >= 0.95) return " and ran at a similar speed";
  return "";
}

export function verdictSentence(r: AnalysisResult): string {
  const { teacher: t, student: s } = r;
  const expected = r.theoretical.p_time;

  if (!expected) {
    if (!t.detected && !s.detected) return "Quiet: neither model detected an earthquake in the last two minutes.";
    if (t.detected && s.detected) return "Both models detected seismic activity.";
    if (t.detected) {
      return "The teacher flags activity but the student does not. In our tests on live data, the original model often over-triggers on quiet noise.";
    }
    return "The student flags activity but the teacher does not.";
  }

  if (!t.detected && !s.detected) {
    return "Neither model detected the earthquake at this station. It may be too weak or too far away. Try a closer station.";
  }

  // An undetected model's pick does not count.
  const tp = t.detected ? t.p_time : null;
  const sp = s.detected ? s.p_time : null;

  if (t.detected !== s.detected) {
    const who = t.detected ? "teacher" : "student";
    const pick = t.detected ? tp : sp;
    const d = pick ? secondsBetween(expected, pick) : NaN;
    if (!Number.isNaN(d)) {
      return `Only the ${who} detected the earthquake at this station; its P pick is ${formatDelta(d)} from the expected arrival.`;
    }
    return `Only the ${who} detected the earthquake at this station, but it did not pick an exact P arrival.`;
  }

  const tq = pickQuality(tp, expected);
  const sq = pickQuality(sp, expected);
  if (usable(tq) && usable(sq)) {
    const td = Math.abs(secondsBetween(expected, tp!));
    const sd = Math.abs(secondsBetween(expected, sp!));
    const verb = sd <= td + 0.5 ? "matched" : "came close to";
    return `Both models found the P wave within ${Math.max(td, sd).toFixed(2)} s of the expected arrival. The student ${verb} the teacher${speedClause(speedup(r))}.`;
  }
  if (usable(tq) || usable(sq)) {
    const useTeacher = usable(tq);
    const winnerPick = useTeacher ? tp! : sp!;
    const otherPick = useTeacher ? sp : tp;
    const who = useTeacher ? "teacher" : "student";
    const otherText = otherPick
      ? "picked a different arrival (another event or a mis-pick)"
      : "did not pick it";
    return `Only the ${who} found the P wave near the expected arrival (${formatDelta(secondsBetween(expected, winnerPick))}). The other ${otherText}.`;
  }
  if (tq === "none" && sq === "none") {
    return "Both models detected the earthquake, but neither was confident about the exact P arrival.";
  }
  if (tq === "far" && sq === "none") {
    return `The teacher picked an arrival far from the expected time (${formatDelta(secondsBetween(expected, tp!))}), and the other model did not pick P.`;
  }
  if (tq === "none" && sq === "far") {
    return `The student picked an arrival far from the expected time (${formatDelta(secondsBetween(expected, sp!))}), and the other model did not pick P.`;
  }
  return "Both models detected seismic activity but picked arrivals far from the expected time, possibly a different event in the window.";
}
