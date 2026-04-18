import { useMemo } from "react";
import {
  ResponsiveContainer, LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid, ReferenceLine,
} from "recharts";
import type { SimHistory } from "../hooks/useSimulation";

export function InventoryChart({ history, cap }: { history: SimHistory; cap: number }) {
  const data = useMemo(
    () => history.t.map((t, i) => ({ t: t.toFixed(1), inventory: history.inventory[i] })),
    [history],
  );

  return (
    <div className="card h-64">
      <div className="flex items-center justify-between mb-2">
        <div className="font-semibold">Inventory</div>
        <div className="text-xs text-muted">cap &plusmn;{cap}</div>
      </div>
      <ResponsiveContainer width="100%" height="85%">
        <LineChart data={data} margin={{ top: 4, right: 12, left: 0, bottom: 0 }}>
          <CartesianGrid stroke="#1a2330" />
          <XAxis dataKey="t" tick={{ fontSize: 10, fill: "#8b96a5" }} />
          <YAxis domain={[-cap, cap]} tick={{ fontSize: 10, fill: "#8b96a5" }} width={40} />
          <Tooltip contentStyle={{ background: "#121821", border: "1px solid #1a2330", fontSize: 12 }} />
          <ReferenceLine y={0} stroke="#2b3646" />
          <ReferenceLine y={cap} stroke="#fb7185" strokeDasharray="2 4" />
          <ReferenceLine y={-cap} stroke="#fb7185" strokeDasharray="2 4" />
          <Line type="monotone" dataKey="inventory" stroke="#fbbf24" dot={false} strokeWidth={1.5} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
