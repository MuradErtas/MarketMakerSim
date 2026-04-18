import { useMemo } from "react";
import {
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, CartesianGrid,
} from "recharts";
import type { Book } from "../lib/types";

export function DepthChart({ book, mid }: { book: Book; mid: number }) {
  const data = useMemo(() => {
    // Cumulative depth from mid outward for a classic depth curve
    const bidsSorted = [...book.bids].sort((a, b) => b.price - a.price);
    const asksSorted = [...book.asks].sort((a, b) => a.price - b.price);

    let bidCum = 0;
    const bidCurve = bidsSorted.map((l) => {
      bidCum += l.size;
      return { price: l.price, bid: bidCum, ask: null as number | null };
    }).reverse();

    let askCum = 0;
    const askCurve = asksSorted.map((l) => {
      askCum += l.size;
      return { price: l.price, bid: null as number | null, ask: askCum };
    });

    return [...bidCurve, ...askCurve];
  }, [book]);

  return (
    <div className="card h-72">
      <div className="flex items-center justify-between mb-2">
        <div className="font-semibold">Order book depth</div>
        <div className="text-xs text-muted">mid {mid.toFixed(2)}</div>
      </div>
      <ResponsiveContainer width="100%" height="88%">
        <BarChart data={data} margin={{ top: 4, right: 12, left: 0, bottom: 0 }}>
          <CartesianGrid stroke="#1a2330" />
          <XAxis
            dataKey="price"
            tickFormatter={(v) => v.toFixed(2)}
            tick={{ fontSize: 10, fill: "#8b96a5" }}
          />
          <YAxis tick={{ fontSize: 10, fill: "#8b96a5" }} width={40} />
          <Tooltip
            contentStyle={{ background: "#121821", border: "1px solid #1a2330", fontSize: 12 }}
            formatter={(v: number) => v?.toFixed(2)}
          />
          <Bar dataKey="bid" fill="#6ee7b7" fillOpacity={0.6} />
          <Bar dataKey="ask" fill="#fb7185" fillOpacity={0.6} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
