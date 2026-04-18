import { useSimulation } from "./hooks/useSimulation";
import { StatCard } from "./components/StatCard";
import { PriceChart } from "./components/PriceChart";
import { DepthChart } from "./components/DepthChart";
import { PnLChart } from "./components/PnLChart";
import { InventoryChart } from "./components/InventoryChart";
import { FillHeatmap } from "./components/FillHeatmap";
import { ParamControls } from "./components/ParamControls";
import { SpreadAnalytics } from "./components/SpreadAnalytics";

const WS_URL =
  (import.meta.env.VITE_WS_URL as string | undefined) ??
  (typeof window !== "undefined"
    ? `${window.location.protocol === "https:" ? "wss:" : "ws:"}//${window.location.host}/ws`
    : "ws://localhost:8000/ws");

function fmtUSD(v: number) {
  return v.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

export default function App() {
  const { snapshot, connected, history } = useSimulation(WS_URL);

  if (!snapshot) {
    return (
      <div className="min-h-screen flex items-center justify-center text-muted">
        {connected ? "Waiting for first tick…" : "Connecting to simulator…"}
      </div>
    );
  }

  const m = snapshot.metrics;
  const regimeColor = snapshot.regime === "high" ? "text-danger" : "text-accent";

  return (
    <div className="min-h-screen p-4 lg:p-6 space-y-4">
      {/* Header */}
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold">Market Maker Simulator</h1>
          <p className="text-xs text-muted">
            Avellaneda-Stoikov optimal quoting · regime-switching volatility · live LOB
          </p>
        </div>
        <div className="flex items-center gap-3 text-xs">
          <span className={`pill ${connected ? "bg-accent/10 text-accent" : "bg-danger/10 text-danger"}`}>
            {connected ? "LIVE" : "OFFLINE"}
          </span>
          <span className="pill bg-panel2 text-muted">step {snapshot.step}</span>
          <span className={`pill bg-panel2 ${regimeColor}`}>regime: {snapshot.regime}</span>
          <span className="pill bg-panel2 text-muted">σ = {snapshot.sigma.toFixed(2)}</span>
        </div>
      </header>

      {/* Stat row */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
        <StatCard label="Mid price" value={snapshot.mid.toFixed(2)} />
        <StatCard
          label="Equity (MtM)"
          value={`$${fmtUSD(m.equity)}`}
          tone={m.equity >= 0 ? "good" : "bad"}
          sub={`realized $${fmtUSD(m.realized_pnl)}`}
        />
        <StatCard label="Inventory" value={m.inventory.toFixed(2)} tone={Math.abs(m.inventory) > 20 ? "warn" : "default"} />
        <StatCard label="Sharpe (rolling)" value={m.sharpe.toFixed(2)} tone={m.sharpe >= 0 ? "good" : "bad"} />
        <StatCard label="Max drawdown" value={`$${fmtUSD(m.max_drawdown)}`} tone="bad" />
        <StatCard label="Fills" value={m.num_fills.toString()} />
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2 space-y-4">
          <PriceChart history={history} />
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <PnLChart history={history} />
            <InventoryChart history={history} cap={snapshot.params.max_inventory} />
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <DepthChart book={snapshot.book} mid={snapshot.mid} />
            <SpreadAnalytics snap={snapshot} />
          </div>
          <FillHeatmap fills={snapshot.recent_fills} />
        </div>
        <div className="space-y-4">
          <ParamControls params={snapshot.params} />
          <div className="card">
            <div className="font-semibold mb-2">About</div>
            <p className="text-xs text-muted leading-relaxed">
              The agent implements the Avellaneda-Stoikov optimal market maker. Given the mid <code>s</code>,
              inventory <code>q</code>, vol <code>σ</code>, and horizon <code>T</code>, it quotes around a
              reservation price <code>r = s − q·γ·σ²·(T − t)</code> with an optimal spread of
              <code> γσ²(T − t) + (2/γ)ln(1 + γ/k)</code>. Noise flow is Poisson with intensity
              <code> λ = A·exp(−k·δ)</code>, where <code>δ</code> is distance from mid. Volatility switches
              between low/high regimes via a 2-state Markov chain. Adjust γ (risk aversion) and k (liquidity)
              to see how the quotes adapt.
            </p>
          </div>
        </div>
      </div>

      <footer className="text-xs text-muted pt-2">
        Built as a learning project. Source &amp; math on GitHub.
      </footer>
    </div>
  );
}
