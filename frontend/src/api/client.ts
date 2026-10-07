export interface EqEvent {
  id: string;
  time: string;
  magnitude: number;
  lat: number;
  lon: number;
  depth_km: number;
  place: string;
}

export interface Station {
  id: string;
  network: string;
  station: string;
  location: string;
  band: string;
  lat: number;
  lon: number;
  distance_km: number;
}

export interface Curves {
  detection: number[];
  p: number[];
  s: number[];
}

export interface ModelResult {
  detected: boolean;
  detection_max: number;
  p_time: string | null;
  s_time: string | null;
  p_conf: number | null;
  s_conf: number | null;
  latency_ms: number;
  curves: Curves;
}

export interface AnalysisResult {
  station: string;
  distance_km: number | null;
  start_time: string;
  display_dt: number;
  waveform: { z: number[]; n: number[]; e: number[] };
  theoretical: { p_time: string | null; s_time: string | null };
  teacher: ModelResult;
  student: ModelResult;
}

export interface ModelInfo {
  name: string;
  params: number;
  size_mb: number;
}

export interface ModelsInfo {
  teacher: ModelInfo;
  student: ModelInfo;
  compression: number;
}

export interface LiveStation {
  id: string;
  label: string;
}

export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
  ) {
    super(message);
  }
}

async function get<T>(path: string): Promise<T> {
  const res = await fetch(path);
  if (!res.ok) {
    let code = "unknown";
    let message = res.statusText;
    try {
      const body = await res.json();
      code = body.error ?? code;
      message = body.message ?? message;
    } catch {
      // body was not JSON; keep defaults
    }
    throw new ApiError(res.status, code, message);
  }
  return res.json() as Promise<T>;
}

const q = encodeURIComponent;

export const api = {
  events: (days = 3, minMag = 4) => get<EqEvent[]>(`/api/events?days=${days}&min_mag=${minMag}`),
  stations: (eventId: string) => get<Station[]>(`/api/events/${q(eventId)}/stations`),
  analyze: (eventId: string, station: string) =>
    get<AnalysisResult>(`/api/analyze?event_id=${q(eventId)}&station=${q(station)}`),
  live: (station: string) => get<AnalysisResult>(`/api/live?station=${q(station)}`),
  liveStations: () => get<LiveStation[]>("/api/live/stations"),
  models: () => get<ModelsInfo>("/api/models"),
};
