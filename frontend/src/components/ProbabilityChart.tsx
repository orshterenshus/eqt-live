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
