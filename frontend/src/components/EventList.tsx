import type { EqEvent } from "../api/client";
import { timeAgo } from "../format";

interface Props {
  events: EqEvent[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}

export function EventList({ events, selectedId, onSelect }: Props) {
  if (events.length === 0) return <p className="muted">No earthquakes match this filter.</p>;
  return (
    <ul className="event-list">
      {events.map((e) => {
        const selected = e.id === selectedId;
        return (
          <li key={e.id}>
            <button type="button" aria-pressed={selected} onClick={() => onSelect(e.id)}>
              <span className="marker" aria-hidden="true">{selected ? "▸" : ""}</span>
              <span className="mag">M{e.magnitude.toFixed(1)}</span>
              <span>{e.place}</span>
              <span className="age">{timeAgo(e.time)}</span>
            </button>
          </li>
        );
      })}
    </ul>
  );
}
