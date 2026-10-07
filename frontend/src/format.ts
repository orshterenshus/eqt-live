export function formatUtcTime(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toISOString().slice(11, 22);
}

export function secondsBetween(fromIso: string, toIso: string): number {
  return (new Date(toIso).getTime() - new Date(fromIso).getTime()) / 1000;
}

export function timeAgo(iso: string, now: number = Date.now()): string {
  const minutes = Math.round((now - new Date(iso).getTime()) / 60000);
  if (minutes < 60) return `${minutes} min ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 48) return `${hours} h ago`;
  return `${Math.round(hours / 24)} d ago`;
}
