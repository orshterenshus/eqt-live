export function Spinner({ text }: { text: string }) {
  return (
    <div className="spinner" role="status">
      {text}
      <span className="cursor" aria-hidden="true" />
    </div>
  );
}
