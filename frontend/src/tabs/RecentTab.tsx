import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { api, type ModelsInfo } from "../api/client";
import { AnalysisView } from "../components/AnalysisView";
import { ErrorBox } from "../components/ErrorBox";
import { EventList } from "../components/EventList";
import { EventMap } from "../components/EventMap";
import { Spinner } from "../components/Spinner";
import { StationPicker } from "../components/StationPicker";

export function RecentTab({ models }: { models?: ModelsInfo }) {
  const [minMag, setMinMag] = useState(4);
  const [eventId, setEventId] = useState<string | null>(null);
  const [stationId, setStationId] = useState<string | null>(null);

  const eventsQ = useQuery({ queryKey: ["events", minMag], queryFn: () => api.events(3, minMag) });
  const stationsQ = useQuery({
    queryKey: ["stations", eventId],
    queryFn: () => api.stations(eventId!),
    enabled: eventId !== null,
  });
  const stations = stationsQ.data;
  const effectiveStation = stations?.some((s) => s.id === stationId)
    ? stationId
    : stations?.[0]?.id ?? null;
  const analysisQ = useQuery({
    queryKey: ["analyze", eventId, effectiveStation],
    queryFn: () => api.analyze(eventId!, effectiveStation!),
    enabled: eventId !== null && effectiveStation !== null,
  });

  const events = eventsQ.data ?? [];
  const selected = events.find((e) => e.id === eventId);

  return (
    <>
      <section className="panel two-col">
        <EventMap events={events} selectedId={eventId} onSelect={setEventId} />
        <div>
          <label>
            Minimum magnitude
            <select value={minMag} onChange={(e) => setMinMag(Number(e.target.value))}>
              {[3, 4, 5, 6].map((m) => (
                <option key={m} value={m}>
                  {m}+
                </option>
              ))}
            </select>
          </label>
          {eventsQ.isPending ? (
            <Spinner text="Loading recent earthquakes…" />
          ) : eventsQ.isError ? (
            <ErrorBox error={eventsQ.error} />
          ) : (
            <EventList events={events} selectedId={eventId} onSelect={setEventId} />
          )}
        </div>
      </section>

      {selected && (
        <section className="panel">
          <h2>
            M{selected.magnitude.toFixed(1)} · {selected.place}
          </h2>
          {stationsQ.isPending ? (
            <Spinner text="Finding nearby stations…" />
          ) : stationsQ.isError ? (
            <ErrorBox error={stationsQ.error} />
          ) : stationsQ.data.length === 0 ? (
            <p className="muted">
              No seismic stations with 3-component data within ~330 km of this earthquake. Try
              another one.
            </p>
          ) : (
            <>
              <label>
                Station
                <StationPicker
                  stations={stationsQ.data.map((s) => ({
                    id: s.id,
                    label: `${s.network}.${s.station} – ${s.distance_km.toFixed(0)} km`,
                  }))}
                  value={effectiveStation}
                  onChange={setStationId}
                />
              </label>
              {effectiveStation && <AnalysisView query={analysisQ} models={models} />}
            </>
          )}
        </section>
      )}
    </>
  );
}
