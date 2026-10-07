import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { api } from "../api/client";
import { RecentTab } from "./RecentTab";

vi.mock("../api/client", () => ({
  api: { events: vi.fn(), stations: vi.fn(), analyze: vi.fn() },
}));
vi.mock("../components/EventMap", () => ({
  EventMap: ({ events, onSelect }: { events: { id: string }[]; onSelect: (id: string) => void }) => (
    <div>
      {events.map((e) => (
        <button key={e.id} onClick={() => onSelect(e.id)}>
          pick-{e.id}
        </button>
      ))}
    </div>
  ),
}));
vi.mock("../components/AnalysisView", () => ({ AnalysisView: () => <div>analysis</div> }));

const ev = (id: string) => ({ id, time: "", magnitude: 5, lat: 0, lon: 0, depth_km: 1, place: `place-${id}` });
const st = (id: string) => ({
  id, network: "N", station: id, location: "", band: "BH", lat: 0, lon: 0, distance_km: 10,
});

describe("RecentTab", () => {
  it("does not analyze new event with the previous event's station", async () => {
    vi.mocked(api.events).mockResolvedValue([ev("A"), ev("B")]);
    vi.mocked(api.stations).mockImplementation(async (id: string) => [st(id === "A" ? "A1" : "B1")]);
    vi.mocked(api.analyze).mockResolvedValue({} as never);

    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <QueryClientProvider client={qc}>
        <RecentTab />
      </QueryClientProvider>,
    );

    fireEvent.click(await screen.findByText("pick-A"));
    await waitFor(() => expect(api.analyze).toHaveBeenCalledWith("A", "A1"));
    fireEvent.click(screen.getByText("pick-B"));
    await waitFor(() => expect(api.analyze).toHaveBeenCalledWith("B", "B1"));
    expect(api.analyze).not.toHaveBeenCalledWith("B", "A1");
  });
});
