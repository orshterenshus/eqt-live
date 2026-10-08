import type { AnalysisResult, ModelResult, ModelsInfo } from "../api/client";
import { formatUtcTime, secondsBetween } from "../format";
import { formatDelta, pickQuality, speedup } from "../verdict";

function header(label: string, params?: number): string {
  return params ? `${label} ${Math.round(params / 1000)}K` : label;
}

function detected(r: ModelResult): string {
  return `${r.detected ? "yes" : "no"} · ${r.detection_max.toFixed(2)}`;
}

function PickCell({ pick, expected }: { pick: string | null; expected: string | null }) {
  const quality = pickQuality(pick, expected);
  if (quality === null) return <td>{formatUtcTime(pick)}</td>;
  if (quality === "none") return <td className="q-none">— not picked</td>;
  return <td className={`q-${quality}`}>{`● ${formatDelta(secondsBetween(expected!, pick!))} ${quality}`}</td>;
}

export function ComparisonCard({ result, models }: { result: AnalysisResult; models?: ModelsInfo }) {
  const { teacher, student, theoretical } = result;
  const event = theoretical.p_time !== null;
  const ratio = speedup(result);
  return (
    <table className="comparison">
      <thead>
        <tr>
          <th />
          <th>{header("Teacher", models?.teacher.params)}</th>
          <th className="student">{header("Student", models?.student.params)}</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td>Detected</td>
          <td>{detected(teacher)}</td>
          <td>{detected(student)}</td>
        </tr>
        <tr>
          <td>{event ? "P vs expected" : "P arrival (UTC)"}</td>
          <PickCell pick={teacher.p_time} expected={theoretical.p_time} />
          <PickCell pick={student.p_time} expected={theoretical.p_time} />
        </tr>
        <tr>
          <td>{event ? "S vs expected" : "S arrival (UTC)"}</td>
          <PickCell pick={teacher.s_time} expected={theoretical.s_time} />
          <PickCell pick={student.s_time} expected={theoretical.s_time} />
        </tr>
        <tr>
          <td>Inference / window</td>
          <td>{teacher.latency_ms.toFixed(1)} ms</td>
          <td>
            {student.latency_ms.toFixed(1)} ms
            {ratio !== null && ratio >= 1.05 ? <span className="accent">{` · ${ratio.toFixed(1)}× faster`}</span> : null}
          </td>
        </tr>
        {models && (
          <tr>
            <td>Model size</td>
            <td>{models.teacher.size_mb.toFixed(2)} MB</td>
            <td>
              {models.student.size_mb.toFixed(2)} MB
              <span className="accent">{` · ${models.compression.toFixed(1)}× fewer parameters`}</span>
            </td>
          </tr>
        )}
      </tbody>
    </table>
  );
}
