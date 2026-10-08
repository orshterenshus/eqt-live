import { CircleMarker, MapContainer, TileLayer, Tooltip } from "react-leaflet";
import type { EqEvent } from "../api/client";

interface Props {
  events: EqEvent[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}

export function EventMap({ events, selectedId, onSelect }: Props) {
  return (
    <MapContainer center={[20, 0]} zoom={2} className="map" worldCopyJump>
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      {events.map((e) => (
        <CircleMarker
          // Leaflet applies className only when a path is created, so selection changes remount the marker.
          key={`${e.id}:${e.id === selectedId ? 1 : 0}`}
          center={[e.lat, e.lon]}
          radius={Math.max(3, e.magnitude * 2)}
          pathOptions={{ className: e.id === selectedId ? "quake quake-selected" : "quake" }}
          eventHandlers={{ click: () => onSelect(e.id) }}
        >
          <Tooltip>
            M{e.magnitude.toFixed(1)} · {e.place}
          </Tooltip>
        </CircleMarker>
      ))}
    </MapContainer>
  );
}
