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
        attribution="&copy; OpenStreetMap contributors"
        url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      {events.map((e) => (
        <CircleMarker
          key={e.id}
          center={[e.lat, e.lon]}
          radius={Math.max(3, e.magnitude * 2)}
          pathOptions={{
            color: e.id === selectedId ? "#dc2626" : "#2563eb",
            weight: e.id === selectedId ? 3 : 1,
            fillOpacity: 0.5,
          }}
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
