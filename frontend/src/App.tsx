import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { api } from "./api/client";
import { AboutPanel } from "./components/AboutPanel";
import { LiveTab } from "./tabs/LiveTab";
import { RecentTab } from "./tabs/RecentTab";

type Tab = "recent" | "live" | "about";

const TABS: [Tab, string][] = [
  ["recent", "Recent Earthquakes"],
  ["live", "Live Station"],
  ["about", "About"],
];

export default function App() {
  const [tab, setTab] = useState<Tab>("recent");
  const modelsQ = useQuery({ queryKey: ["models"], queryFn: api.models });
  return (
    <div className="app">
      <header>
        <h1>🌍 EQT-Live</h1>
        <p className="muted">
          Earthquake detection on live seismic data: the original EQTransformer vs. a 6x smaller
          distilled model
        </p>
        <nav>
          {TABS.map(([id, label]) => (
            <button key={id} className={tab === id ? "active" : ""} onClick={() => setTab(id)}>
              {label}
            </button>
          ))}
        </nav>
      </header>
      <main>
        {tab === "recent" && <RecentTab models={modelsQ.data} />}
        {tab === "live" && <LiveTab models={modelsQ.data} />}
        {tab === "about" && <AboutPanel models={modelsQ.data} />}
      </main>
    </div>
  );
}
