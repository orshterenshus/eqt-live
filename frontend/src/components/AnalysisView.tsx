import type { UseQueryResult } from "@tanstack/react-query";
import type { AnalysisResult, ModelsInfo } from "../api/client";
import { formatUtcTime } from "../format";
import { verdictSentence } from "../verdict";
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
  if (query.isPending) return <Spinner text="acquiring waveform, running both models" />;
  if (query.isError && !query.data) return <ErrorBox error={query.error} />;
  const result = query.data!;
  const where = result.distance_km != null ? ` · ${result.distance_km.toFixed(0)} km from epicenter` : "";
  return (
    <div>
      {query.isError && <ErrorBox error={query.error} />}
      <div className="verdict">
        <div className="label">{`Verdict · ${result.station}${where}`}</div>
        <p className="verdict-text">{verdictSentence(result)}</p>
      </div>

      <div className="scope">
        <div className="scope-head">
          <span>{`Waveform · Z / N / E · from ${formatUtcTime(result.start_time)} UTC`}</span>
          <span className="scope-legend">
            <span className="teacher">— teacher</span>
            <span className="student">- - student</span>
            <span className="expected">··· expected</span>
          </span>
        </div>
        <div className="scope-body">
          <WaveformChart result={result} />
        </div>
      </div>

      <div className="scope">
        <div className="scope-head">
          <span>Model output · probability · seconds</span>
          <span className="scope-legend scope-legend--neutral">
            <span>— teacher</span>
            <span>- - student</span>
          </span>
        </div>
        <div className="scope-body">
          <ProbabilityChart result={result} />
        </div>
      </div>

      <div className="table-wrap">
        <ComparisonCard result={result} models={models} />
      </div>
    </div>
  );
}
