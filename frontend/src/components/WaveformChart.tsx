import type { AnalysisResult } from "../api/client";
import { secondsBetween } from "../format";
import { useThemeColors, type ThemeColors } from "../theme";
import { Plot } from "./Plot";

const HEIGHT = 360;
const FONT = { family: "IBM Plex Mono, Consolas, monospace", size: 10 };

function pickLines(result: AnalysisResult, c: ThemeColors) {
  const sources = [
    { times: result.teacher, color: c.teacher, dash: "solid" },
    { times: result.student, color: c.student, dash: "dash" },
    { times: result.theoretical, color: c.expected, dash: "dot" },
  ];
  const shapes: object[] = [];
  const annotations: object[] = [];
  for (const source of sources) {
    for (const [phase, time] of [["P", source.times.p_time], ["S", source.times.s_time]] as const) {
      if (!time) continue;
      const x = secondsBetween(result.start_time, time);
      shapes.push({ type: "line", xref: "x", yref: "paper", x0: x, x1: x, y0: 0, y1: 1,
                    line: { color: source.color, dash: source.dash, width: 1.5 } });
      annotations.push({ x, y: 1, xref: "x", yref: "paper", text: phase, showarrow: false,
                         yanchor: "bottom", font: { ...FONT, color: source.color } });
    }
  }
  return { shapes, annotations };
}

export function WaveformChart({ result }: { result: AnalysisResult }) {
  const c = useThemeColors();
  const x = result.waveform.z.map((_, i) => i * result.display_dt);
  const channels = [
    ["Z", result.waveform.z, "y"],
    ["N", result.waveform.n, "y2"],
    ["E", result.waveform.e, "y3"],
  ] as const;
  const { shapes, annotations } = pickLines(result, c);
  const axis = { gridcolor: c.hair, zeroline: false, linecolor: c.hair, tickfont: FONT, color: c.muted };
  return (
    <Plot
      data={channels.map(([name, y, yaxis]) => ({
        x, y, name, yaxis, type: "scattergl", mode: "lines",
        line: { width: 1.2, color: c.trace }, showlegend: false,
      }))}
      layout={{
        height: HEIGHT, margin: { l: 44, r: 12, t: 22, b: 36 },
        paper_bgcolor: "rgba(0,0,0,0)", plot_bgcolor: "rgba(0,0,0,0)", font: { ...FONT, color: c.muted },
        grid: { rows: 3, columns: 1, pattern: "coupled" },
        xaxis: { ...axis, title: { text: "seconds", font: FONT } },
        yaxis: { ...axis, title: { text: "Z", font: FONT } },
        yaxis2: { ...axis, title: { text: "N", font: FONT } },
        yaxis3: { ...axis, title: { text: "E", font: FONT } },
        shapes, annotations,
      }}
      config={{ displaylogo: false, responsive: true }}
      style={{ width: "100%", height: HEIGHT }}
    />
  );
}
