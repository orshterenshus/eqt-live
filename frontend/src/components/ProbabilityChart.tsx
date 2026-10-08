import type { AnalysisResult } from "../api/client";
import { useThemeColors } from "../theme";
import { Plot } from "./Plot";

const HEIGHT = 270;
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
        height: HEIGHT, margin: { l: 44, r: 12, t: 10, b: 50 },
        paper_bgcolor: "rgba(0,0,0,0)", plot_bgcolor: "rgba(0,0,0,0)", font: { ...FONT, color: c.muted },
        hoverlabel: { bgcolor: "#11100e", bordercolor: c.hair, font: { ...FONT, color: c.trace } },
        modebar: { bgcolor: "rgba(0,0,0,0)", color: c.muted, activecolor: c.trace },
        yaxis: { ...axis, range: [0, 1.05], title: { text: "probability", font: FONT } },
        xaxis: { ...axis },
        legend: { orientation: "h", x: 0, y: -0.14, yanchor: "top", font: { ...FONT, color: c.muted } },
      }}
      config={{ displaylogo: false, responsive: true }}
      style={{ width: "100%", height: HEIGHT }}
    />
  );
}
