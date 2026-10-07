import type { UseQueryResult } from "@tanstack/react-query";
import type { AnalysisResult, ModelsInfo } from "../api/client";
import { formatUtcTime } from "../format";
import { ComparisonCard } from "./ComparisonCard";
import { ErrorBox } from "./ErrorBox";
import { ProbabilityChart } from "./ProbabilityChart";
import { Spinner } from "./Spinner";
import { WaveformChart } from "./WaveformChart";

interface Props {
  query: UseQueryResult<AnalysisResult>;
  models?: ModelsInfo;
}

export function AnalysisView({ query, models }: Props) {
  if (query.isPending) return <Spinner text="Downloading waveform and running both models…" />;
  if (query.isError && !query.data) return <ErrorBox error={query.error} />;
  const result = query.data!;
  return (
    <div>
      {query.isError && <ErrorBox error={query.error} />}
      <p className="muted">
        Station {result.station}
        {result.distance_km != null && ` · ${result.distance_km.toFixed(0)} km from the epicenter`}
        {` · window starts ${formatUtcTime(result.start_time)} UTC`}
      </p>
      <div className="legend">
        <span>Pick lines:</span>
        <span className="teacher">━ Teacher</span>
        <span className="student">╍ Student</span>
        <span className="theoretical">┅ Theoretical (iasp91)</span>
      </div>
      <WaveformChart result={result} />
      <ProbabilityChart result={result} />
      <ComparisonCard result={result} models={models} />
    </div>
  );
}
