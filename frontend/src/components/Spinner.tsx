export function Spinner({ text }: { text: string }) {
  return (
    <div className="spinner" role="status">
      <span className="spinner-dot" /> {text}
    </div>
  );
}
