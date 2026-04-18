import type { Snapshot } from "../lib/types";

/**
 * Compact panel: optimal A-S spread vs realized top-of-book spread,
 * half-spread in ticks, adverse selection cost per fill.
 */
export function SpreadAnalytics({ snap }: { snap: Snapshot }) {
  const book = snap.book;
  const bestBid = book.bids[0]?.price;
  const bestAsk = book.asks[0]?.price;
  const realizedSpread = bestBid != null && bestAsk != null ? bestAsk - bestBid : null;
  const optimalSpread = snap.quote.spread;
  const tick = snap.params.tick_size;
  const adv = snap.metrics.adverse_selection;

  const Item = ({ k, v, hint }: { k: string; v: React.ReactNode; hint?: string }) => (
    <div>
      <div className="text-xs text-muted">{k}</div>
      <div className="text-base font-semibold tabular-nums">{v}</div>
      {hint && <div className="text-[11px] text-muted">{hint}</div>}
    </div>
  );

  return (
    <div className="card">
      <div className="font-semibold mb-3">Spread & adverse selection</div>
      <div className="grid grid-cols-2 gap-3">
        <Item
          k="Optimal spread (A-S)"
          v={optimalSpread.toFixed(4)}
          hint={`${(optimalSpread / tick).toFixed(1)} ticks`}
        />
        <Item
          k="Realized top-of-book"
          v={realizedSpread != null ? realizedSpread.toFixed(4) : "—"}
          hint={realizedSpread != null ? `${(realizedSpread / tick).toFixed(1)} ticks` : ""}
        />
        <Item
          k="Adverse selection / fill"
          v={adv.toFixed(4)}
          hint={adv > 0 ? "toxic flow — we're being picked off" : "benign flow"}
        />
        <Item
          k="Reservation offset"
          v={(snap.quote.reservation - snap.mid).toFixed(4)}
          hint="positive = agent wants to buy"
        />
      </div>
    </div>
  );
}
