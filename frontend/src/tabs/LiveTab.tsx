import { useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { api, type ModelsInfo } from "../api/client";
import { AnalysisView } from "../components/AnalysisView";
import { ErrorBox } from "../components/ErrorBox";
import { Spinner } from "../components/Spinner";
import { StationPicker } from "../components/StationPicker";

export function LiveTab({ models }: { models?: ModelsInfo }) {
  const stationsQ = useQuery({ queryKey: ["liveStations"], queryFn: api.liveStations });
  const [stationId, setStationId] = useState<string | null>(null);

  useEffect(() => {
    if (stationId === null && stationsQ.data?.length) setStationId(stationsQ.data[0].id);
  }, [stationsQ.data, stationId]);

  const liveQ = useQuery({
    queryKey: ["live", stationId],
    queryFn: () => api.live(stationId!),
    enabled: stationId !== null,
    refetchInterval: 60_000,
    staleTime: 0,
  });

  return (
    <section className="panel">
      <p className="banner">
        This view analyzes the latest ~2 minutes from a live station and refreshes every minute.
        Most of the time there is no earthquake, so "no" is the normal result. To see detections,
        use the Recent Earthquakes tab.
      </p>
      {stationsQ.isPending ? (
        <Spinner text="Loading stations…" />
      ) : stationsQ.isError ? (
        <ErrorBox error={stationsQ.error} />
      ) : (
        <label>
          Station
          <StationPicker stations={stationsQ.data} value={stationId} onChange={setStationId} />
        </label>
      )}
      {stationId && <AnalysisView query={liveQ} models={models} />}
    </section>
  );
}
