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
          // Leaflet reads className only when the path is created (pathOptions go through setStyle,
          // which ignores it), so pass it as a constructor option and remount on selection change.
          key={`${e.id}:${e.id === selectedId ? 1 : 0}`}
          className={e.id === selectedId ? "quake quake-selected" : "quake"}
          center={[e.lat, e.lon]}
          radius={Math.max(3, e.magnitude * 2)}
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
