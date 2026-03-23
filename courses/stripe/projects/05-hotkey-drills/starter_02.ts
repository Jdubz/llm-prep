// DRILL 2 — Extract Helper
// Transform this into target_02.ts using hotkeys.
//
// Tasks:
//   1. The tiered pricing loop appears in BOTH functions — extract it
//      into a standalone "priceTiered(qty, tiers)" function above them
//   2. Replace both loop bodies with calls to priceTiered()
//   3. The lookup "config[dest]?.[product]" appears twice — extract to
//      a "lookup" function
//
// Key hotkeys: Ctrl+Shift+L (select all occurrences), copy line down,
// multi-cursor typing, Ctrl+D progressive select

type Tier = { upTo: number; unitPrice: number };

function calculateTiered(config: Record<string, Record<string, { tiers: Tier[] }>>, dest: string, product: string, qty: number): number {
  const entry = config[dest]?.[product];
  if (!entry) return -1;

  let total = 0, prev = 0;
  for (const { upTo, unitPrice } of entry.tiers) {
    const n = Math.min(qty, upTo) - prev;
    if (n <= 0) break;
    total += n * unitPrice;
    prev = upTo;
  }
  return total;
}

function calculateBasePlusTiered(config: Record<string, Record<string, { base: number; coversUpTo: number; tiers: Tier[] }>>, dest: string, product: string, qty: number): number {
  const entry = config[dest]?.[product];
  if (!entry) return -1;

  if (qty <= entry.coversUpTo) return entry.base;

  const overflow = qty - entry.coversUpTo;
  let total = entry.base, prev = 0;
  for (const { upTo, unitPrice } of entry.tiers) {
    const n = Math.min(overflow, upTo) - prev;
    if (n <= 0) break;
    total += n * unitPrice;
    prev = upTo;
  }
  return total;
}
