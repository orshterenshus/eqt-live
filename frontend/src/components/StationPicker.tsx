interface Props {
  stations: { id: string; label: string }[];
  value: string | null;
  onChange: (id: string) => void;
}

export function StationPicker({ stations, value, onChange }: Props) {
  return (
    <select value={value ?? ""} onChange={(e) => onChange(e.target.value)}>
      {stations.map((s) => (
        <option key={s.id} value={s.id}>
          {s.label}
        </option>
      ))}
    </select>
  );
}
