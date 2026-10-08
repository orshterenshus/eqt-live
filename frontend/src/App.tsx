import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { api } from "./api/client";
import { AboutPanel } from "./components/AboutPanel";
import { ThemeToggle } from "./components/ThemeToggle";
import { LiveTab } from "./tabs/LiveTab";
import { RecentTab } from "./tabs/RecentTab";
import { ThemeContext, useTheme } from "./theme";

type Tab = "recent" | "live" | "method";

const TABS: [Tab, string][] = [
  ["recent", "Recent"],
  ["live", "Live"],
  ["method", "Method"],
];

export default function App() {
  const [tab, setTab] = useState<Tab>("recent");
  const [theme, toggleTheme] = useTheme();
  const modelsQ = useQuery({ queryKey: ["models"], queryFn: api.models });
  return (
    <ThemeContext.Provider value={theme}>
      <div className="app">
        <header className="topbar">
          <span className="wordmark">EQT·LIVE</span>
          <nav className="nav" aria-label="Sections">
            {TABS.map(([id, label]) => (
              <button
                key={id}
                type="button"
                aria-current={tab === id ? "page" : undefined}
                onClick={() => setTab(id)}
              >
                {label}
              </button>
            ))}
            <ThemeToggle theme={theme} onToggle={toggleTheme} />
          </nav>
        </header>
        <main>
          {tab === "recent" && <RecentTab models={modelsQ.data} />}
          {tab === "live" && <LiveTab models={modelsQ.data} />}
          {tab === "method" && <AboutPanel models={modelsQ.data} />}
        </main>
      </div>
    </ThemeContext.Provider>
  );
}
