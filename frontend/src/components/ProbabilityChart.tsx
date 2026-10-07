import type { AnalysisResult } from "../api/client";
import { Plot } from "./Plot";

const CURVES = [
  ["detection", "Detection", "#16a34a"],
  ["p", "P", "#2563eb"],
  ["s", "S", "#dc2626"],
] as const;

export function ProbabilityChart({ result }: { result: AnalysisResult }) {
  const x = result.teacher.curves.p.map((_, i) => i * result.display_dt);
  const data = (["teacher", "student"] as const).flatMap((model) =>
    CURVES.map(([key, label, color]) => ({
      x, y: result[model].curves[key],
      name: `${model === "teacher" ? "Teacher" : "Student"} ${label}`,
      type: "scattergl", mode: "lines",
      line: { color, width: 1.5, dash: model === "teacher" ? "solid" : "dash" },
    })),
  );
  return (
    <Plot
      data={data}
      layout={{
        height: 260, margin: { l: 40, r: 10, t: 10, b: 40 },
        yaxis: { range: [0, 1.05], title: { text: "probability" } },
        xaxis: { title: { text: "seconds" } },
        legend: { orientation: "h" },
      }}
      config={{ displaylogo: false, responsive: true }}
      style={{ width: "100%" }}
    />
  );
}
