import { useMemo } from "react";
import {
  ResponsiveContainer, AreaChart, Area, XAxis, YAxis, Tooltip, CartesianGrid, ReferenceLine,
} from "recharts";
import type { SimHistory } from "../hooks/useSimulation";

export function PnLChart({ history }: { history: SimHistory }) {
  const data = useMemo(
    () => history.t.map((t, i) => ({
      t: t.toFixed(1),
      equity: history.equity[i],
      realized: history.realized[i],
    })),
    [history],
  );

  return (
    <div className="card h-64">
      <div className="flex items-center justify-between mb-2">
        <div className="font-semibold">PnL</div>
        <div className="text-xs text-muted">equity (mtm) • realized (cash)</div>
      </div>
      <ResponsiveContainer width="100%" height="85%">
        <AreaChart data={data} margin={{ top: 4, right: 12, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id="gEq" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#6ee7b7" stopOpacity={0.4} />
              <stop offset="100%" stopColor="#6ee7b7" stopOpacity={0.02} />
            </linearGradient>
          </defs>
          <CartesianGrid stroke="#1a2330" />
          <XAxis dataKey="t" tick={{ fontSize: 10, fill: "#8b96a5" }} />
          <YAxis tick={{ fontSize: 10, fill: "#8b96a5" }} width={60} />
          <Tooltip contentStyle={{ background: "#121821", border: "1px solid #1a2330", fontSize: 12 }} />
          <ReferenceLine y={0} stroke="#2b3646" />
          <Area type="monotone" dataKey="equity" stroke="#6ee7b7" fill="url(#gEq)" strokeWidth={1.5} />
          <Area type="monotone" dataKey="realized" stroke="#8b96a5" fill="transparent" strokeWidth={1} strokeDasharray="3 3" />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
