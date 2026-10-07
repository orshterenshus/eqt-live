import type { AnalysisResult, ModelResult, ModelsInfo } from "../api/client";
import { formatUtcTime, secondsBetween } from "../format";

function delta(a: string | null, b: string | null): string {
  if (!a || !b) return "";
  return `(Δ ${Math.abs(secondsBetween(a, b)).toFixed(2)} s)`;
}

function detectedLabel(r: ModelResult): string {
  return `${r.detected ? "✅ yes" : "— no"} (${r.detection_max.toFixed(2)})`;
}

function header(label: string, params?: number): string {
  return params ? `${label} (${Math.round(params / 1000)}K)` : label;
}

export function ComparisonCard({ result, models }: { result: AnalysisResult; models?: ModelsInfo }) {
  const { teacher, student } = result;
  const speedup = student.latency_ms > 0 ? teacher.latency_ms / student.latency_ms : 0;
  return (
    <table className="comparison">
      <thead>
        <tr>
          <th />
          <th>{header("Teacher", models?.teacher.params)}</th>
          <th>{header("Student", models?.student.params)}</th>
          <th />
        </tr>
      </thead>
      <tbody>
        <tr>
          <td>Detected</td>
          <td>{detectedLabel(teacher)}</td>
          <td>{detectedLabel(student)}</td>
          <td />
        </tr>
        <tr>
          <td>P arrival (UTC)</td>
          <td>{formatUtcTime(teacher.p_time)}</td>
          <td>{formatUtcTime(student.p_time)}</td>
          <td>{delta(teacher.p_time, student.p_time)}</td>
        </tr>
        <tr>
          <td>S arrival (UTC)</td>
          <td>{formatUtcTime(teacher.s_time)}</td>
          <td>{formatUtcTime(student.s_time)}</td>
          <td>{delta(teacher.s_time, student.s_time)}</td>
        </tr>
        <tr>
          <td>Inference / window</td>
          <td>{teacher.latency_ms.toFixed(1)} ms</td>
          <td>{student.latency_ms.toFixed(1)} ms</td>
          <td className="highlight">{`⚡ ${speedup.toFixed(1)}x faster`}</td>
        </tr>
        {models && (
          <tr>
            <td>Model size</td>
            <td>{models.teacher.size_mb.toFixed(2)} MB</td>
            <td>{models.student.size_mb.toFixed(2)} MB</td>
            <td>{`${models.compression.toFixed(1)}x fewer parameters`}</td>
          </tr>
        )}
      </tbody>
    </table>
  );
}
