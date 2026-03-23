type Tier = { upTo: number; unitPrice: number };

function lookup<T>(config: Record<string, Record<string, T>>, dest: string, product: string): T | null {
  return config[dest]?.[product] ?? null;
}

function priceTiered(qty: number, tiers: Tier[]): number {
  let total = 0, prev = 0;
  for (const { upTo, unitPrice } of tiers) {
    const n = Math.min(qty, upTo) - prev;
    if (n <= 0) break;
    total += n * unitPrice;
    prev = upTo;
  }
  return total;
}

function calculateTiered(config: Record<string, Record<string, { tiers: Tier[] }>>, dest: string, product: string, qty: number): number {
  const entry = lookup(config, dest, product);
  if (!entry) return -1;
  return priceTiered(qty, entry.tiers);
}

function calculateBasePlusTiered(config: Record<string, Record<string, { base: number; coversUpTo: number; tiers: Tier[] }>>, dest: string, product: string, qty: number): number {
  const entry = lookup(config, dest, product);
  if (!entry) return -1;
  if (qty <= entry.coversUpTo) return entry.base;
  return entry.base + priceTiered(qty - entry.coversUpTo, entry.tiers);
}
