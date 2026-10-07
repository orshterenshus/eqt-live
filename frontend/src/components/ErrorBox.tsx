import { ApiError } from "../api/client";

export function describeError(err: unknown): string {
  if (err instanceof ApiError) {
    switch (err.code) {
      case "insufficient_data":
        return "This station has no usable data for this time. Try another station.";
      case "upstream_unavailable":
        return `A data provider is not responding right now (${err.message}). Please try again in a minute.`;
      case "models_not_loaded":
        return "The models are still loading. Please refresh in a moment.";
      case "not_found":
        return "Not found. It may have been removed from the catalog.";
      default:
        return err.message;
    }
  }
  if (err instanceof TypeError) return "Network error: could not reach the server.";
  if (err instanceof Error && err.message) return err.message;
  return "Something went wrong.";
}

export function ErrorBox({ error }: { error: unknown }) {
  return (
    <div className="error" role="alert">
      {describeError(error)}
    </div>
  );
}
