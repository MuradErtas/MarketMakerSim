// Shapes returned by the backend WebSocket / REST.

export interface DepthLevel { price: number; size: number; }
export interface Book { bids: DepthLevel[]; asks: DepthLevel[]; }

export interface Fill {
  t: number;
  side: "buy" | "sell";
  price: number;
  size: number;
  mid: number;
}

export interface Metrics {
  cash: number;
  inventory: number;
  equity: number;
  realized_pnl: number;
  max_drawdown: number;
  sharpe: number;
  adverse_selection: number;
  num_fills: number;
}

export interface Params {
  dt: number;
  T: number;
  s0: number;
  tick_size: number;
  gamma: number;
  k: number;
  A: number;
  sigma_low: number;
  sigma_high: number;
  p_low_to_high: number;
  p_high_to_low: number;
  quote_size: number;
  max_inventory: number;
  seed: number | null;
}

export interface Snapshot {
  t: number;
  step: number;
  mid: number;
  regime: "low" | "high";
  sigma: number;
  quote: {
    bid: number | null;
    ask: number | null;
    reservation: number;
    spread: number;
  };
  book: Book;
  metrics: Metrics;
  recent_fills: Fill[];
  params: Params;
}
