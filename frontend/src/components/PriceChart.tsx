import { useMemo } from "react";
import {
  ResponsiveContainer, LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid, ReferenceLine,
} from "recharts";
import type { SimHistory } from "../hooks/useSimulation";

/**
 * Mid, MM bid, MM ask, and reservation price overlaid.
 * Good intuition for students: watch how reservation drifts when
 * inventory moves, and how the quotes widen in high-vol regimes.
 */
export function PriceChart({ history }: { history: SimHistory }) {
  const data = useMemo(
    () =>
      history.t.map((t, i) => ({
        t: t.toFixed(1),
        mid: history.mid[i],
        bid: history.bid[i] ?? null,
        ask: history.ask[i] ?? null,
        reservation: history.reservation[i],
      })),
    [history],
  );

  return (
    <div className="card h-72">
      <div className="flex items-center justify-between mb-2">
        <div className="font-semibold">Price & quotes</div>
        <div className="text-xs text-muted">mid (white), bid (green), ask (red), reservation (amber)</div>
      </div>
      <ResponsiveContainer width="100%" height="88%">
        <LineChart data={data} margin={{ top: 4, right: 12, left: 0, bottom: 0 }}>
          <CartesianGrid stroke="#1a2330" />
          <XAxis dataKey="t" tick={{ fontSize: 10, fill: "#8b96a5" }} />
          <YAxis domain={["auto", "auto"]} tick={{ fontSize: 10, fill: "#8b96a5" }} width={60} />
          <Tooltip
            contentStyle={{ background: "#121821", border: "1px solid #1a2330", fontSize: 12 }}
            labelStyle={{ color: "#8b96a5" }}
          />
          <Line type="monotone" dataKey="mid" stroke="#e6edf3" dot={false} strokeWidth={1.5} />
          <Line type="monotone" dataKey="bid" stroke="#6ee7b7" dot={false} strokeWidth={1} />
          <Line type="monotone" dataKey="ask" stroke="#fb7185" dot={false} strokeWidth={1} />
          <Line type="monotone" dataKey="reservation" stroke="#fbbf24" dot={false} strokeWidth={1} strokeDasharray="4 2" />
          {data.length > 0 && <ReferenceLine y={data[0].mid} stroke="#2b3646" strokeDasharray="2 4" />}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
