import type { AnalysisResult } from "../api/client";
import { secondsBetween } from "../format";
import { Plot } from "./Plot";

const HEIGHT = 360;

const PICK_SOURCES = [
  { key: "teacher", color: "#2563eb", dash: "solid" },
  { key: "student", color: "#dc2626", dash: "dash" },
  { key: "theoretical", color: "#6b7280", dash: "dot" },
] as const;

function pickLines(result: AnalysisResult) {
  const shapes: object[] = [];
  const annotations: object[] = [];
  for (const source of PICK_SOURCES) {
    const times = source.key === "theoretical" ? result.theoretical : result[source.key];
    for (const [phase, time] of [["P", times.p_time], ["S", times.s_time]] as const) {
      if (!time) continue;
      const x = secondsBetween(result.start_time, time);
      shapes.push({ type: "line", xref: "x", yref: "paper", x0: x, x1: x, y0: 0, y1: 1,
                    line: { color: source.color, dash: source.dash, width: 1.5 } });
      annotations.push({ x, y: 1, xref: "x", yref: "paper", text: phase, showarrow: false,
                         yanchor: "bottom", font: { color: source.color } });
    }
  }
  return { shapes, annotations };
}

export function WaveformChart({ result }: { result: AnalysisResult }) {
  const x = result.waveform.z.map((_, i) => i * result.display_dt);
  const channels = [
    ["Z", result.waveform.z, "y"],
    ["N", result.waveform.n, "y2"],
    ["E", result.waveform.e, "y3"],
  ] as const;
  const { shapes, annotations } = pickLines(result);
  return (
    <Plot
      data={channels.map(([name, y, axis]) => ({
        x, y, name, yaxis: axis, type: "scattergl", mode: "lines",
        line: { width: 1, color: "#0f172a" }, showlegend: false,
      }))}
      layout={{
        height: HEIGHT, margin: { l: 40, r: 10, t: 24, b: 40 },
        grid: { rows: 3, columns: 1, pattern: "coupled" },
        xaxis: { title: { text: "seconds" } },
        yaxis: { title: { text: "Z" } }, yaxis2: { title: { text: "N" } }, yaxis3: { title: { text: "E" } },
        shapes, annotations,
      }}
      config={{ displaylogo: false, responsive: true }}
      style={{ width: "100%", height: HEIGHT }}
    />
  );
}
