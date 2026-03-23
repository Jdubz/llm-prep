/*
Drill 07 — Tiered Pricing / Shipping Cost Calculator

Build a pricing engine that computes shipping costs. This is the
single most commonly reported Stripe Programming Exercise problem.
Focus on clean design, speed of implementation, and handling edge cases.

Target time: 30 minutes for all 4 levels.

────────────────────────────────────────
Level 1 — Flat Per-Unit Pricing (5 min)

  type FlatConfig = {
    [destination: string]: {
      [product: string]: { unitPrice: number }
    }
  }

  type Order = { destination: string; product: string; quantity: number }

  calculateFlat(config: FlatConfig, order: Order): number
    Returns unitPrice * quantity.
    If the (destination, product) pair is not in config, return -1.

────────────────────────────────────────
Level 2 — Tiered Per-Unit Pricing (10 min)

  type Tier = { upTo: number; unitPrice: number }

  type TieredConfig = {
    [destination: string]: {
      [product: string]: { tiers: Tier[] }
    }
  }

  calculateTiered(config: TieredConfig, order: Order): number
    Each tier's upTo is inclusive. Apply each tier only to items
    in that range (graduated/marginal pricing).

    Tiers are sorted ascending by upTo. The last tier may use Infinity.

    Example: tiers [{upTo: 5, unitPrice: 10}, {upTo: 10, unitPrice: 8}, {upTo: Infinity, unitPrice: 5}]
      quantity=7:  first 5 at $10 = $50, next 2 at $8 = $16 → total $66
      quantity=12: first 5 at $10 = $50, next 5 at $8 = $40, next 2 at $5 = $10 → total $100

    If the (destination, product) pair is not in config, return -1.

────────────────────────────────────────
Level 3 — Flat Base + Tiered Overflow (10 min)

  type BaseFlat = { amount: number; coversUpTo: number }

  type BasePlusTieredConfig = {
    [destination: string]: {
      [product: string]: { baseFlat: BaseFlat; tiers: Tier[] }
    }
  }

  calculateBasePlusTiered(config: BasePlusTieredConfig, order: Order): number
    For quantities <= coversUpTo: charge baseFlat.amount.
    For quantities > coversUpTo: charge baseFlat.amount + tiered pricing
    on (quantity - coversUpTo) using the tiers array.

    If the (destination, product) pair is not in config, return -1.

────────────────────────────────────────
Level 4 — Multi-Product Orders with Discounts (10 min)

  type LineItem = { product: string; quantity: number }

  type MultiOrder = { destination: string; items: LineItem[] }

  type ProductPricing =
    | { type: "flat"; unitPrice: number }
    | { type: "tiered"; tiers: Tier[] }
    | { type: "basePlusTiered"; baseFlat: BaseFlat; tiers: Tier[] }

  type MultiConfig = {
    [destination: string]: {
      [product: string]: ProductPricing
    }
  }

  type Discount = { threshold: number; percentage: number }

  type OrderResult = {
    items: { product: string; subtotal: number }[];
    subtotal: number;
    discount: number;
    total: number;
  }

  calculateMulti(config: MultiConfig, order: MultiOrder, discount?: Discount): OrderResult
    Process each line item using its pricing type (flat, tiered, or basePlusTiered).
    If any product is missing from config, its subtotal is -1 and it is excluded
    from the order subtotal/discount/total (treat as an error line).

    If discount is provided and the subtotal (of valid items) > threshold,
    apply the percentage discount (0-100) to get the discount amount.
    total = subtotal - discount.

    Return itemized breakdown and totals.
*/

// ─── Types ───────────────────────────────────────────────────────

type Tier = { upTo: number; unitPrice: number };
type BaseFlat = { amount: number; coversUpTo: number };

type FlatConfig = {
  [destination: string]: {
    [product: string]: { unitPrice: number };
  };
};

type TieredConfig = {
  [destination: string]: {
    [product: string]: { tiers: Tier[] };
  };
};

type BasePlusTieredConfig = {
  [destination: string]: {
    [product: string]: { baseFlat: BaseFlat; tiers: Tier[] };
  };
};

type LineItem = { product: string; quantity: number };
type Order = { destination: string; product: string; quantity: number };
type MultiOrder = { destination: string; items: LineItem[] };

type ProductPricing =
  | { type: "flat"; unitPrice: number }
  | { type: "tiered"; tiers: Tier[] }
  | { type: "basePlusTiered"; baseFlat: BaseFlat; tiers: Tier[] };

type MultiConfig = {
  [destination: string]: {
    [product: string]: ProductPricing;
  };
};

type Discount = { threshold: number; percentage: number };

type OrderResult = {
  items: { product: string; subtotal: number }[];
  subtotal: number;
  discount: number;
  total: number;
};

// ─── Implementation ──────────────────────────────────────────────

// Level 1
function calculateFlat(config: FlatConfig, order: Order): number {

  // Returns unitPrice * quantity.
  //  If the (destination, product) pair is not in config, return -1.
  const destination = config[order.destination];
  if (!destination) return -1;
  const product = destination[order.product];
  if (!product || !product.unitPrice) return -1;
  return product.unitPrice * order.quantity
}
// REVIEW: Works. Minor: `!product.unitPrice` on line 162 would
// return -1 for a valid unitPrice of 0. Use `product == null` instead.
// Also: the 3-line lookup (config → destination → product → null check)
// will repeat verbatim in every level. Extract a generic lookup helper
// now — you'll thank yourself when Level 3+ arrives:
//   function lookup<T>(cfg: Record<string, Record<string, T>>, dest: string, prod: string): T | null {
//     return cfg[dest]?.[prod] ?? null;
//   }

// Level 2
function calculateTiered(config: TieredConfig, order: Order): number {
  // Each tier's upTo is inclusive. Apply each tier only to items
  //   in that range (graduated/marginal pricing).

  //   Tiers are sorted ascending by upTo. The last tier may use Infinity.

  //   Example: tiers [{upTo: 5, unitPrice: 10}, {upTo: 10, unitPrice: 8}, {upTo: Infinity, unitPrice: 5}]
  //     quantity=7:  first 5 at $10 = $50, next 2 at $8 = $16 → total $66
  //     quantity=12: first 5 at $10 = $50, next 5 at $8 = $40, next 2 at $5 = $10 → total $100

  //   If the (destination, product) pair is not in config, return -1.
  const destination = config[order.destination];
  if (!destination) return -1;
  const product = destination[order.product];
  if (!product || !product.tiers) return -1;

  let total = 0, prev = 0;

  for (const { upTo, unitPrice } of product.tiers) {
    const qty = Math.min(order.quantity, upTo) - prev;
    if (qty <= 0) break;
    total += qty * unitPrice;
    prev = upTo;
  }

  return total;
}
// REVIEW: Correct. The tiered loop (lines 191-198) is pure math — it
// only needs (quantity, tiers), not the config. Extract it now:
//   function priceTiered(qty: number, tiers: Tier[]): number { ... }
// This function becomes: lookup + priceTiered(order.quantity, product.tiers).
// When the next level lands, you'll be able to reuse priceTiered directly
// instead of copy-pasting the loop. This is the single highest-leverage
// extraction in this drill — it saves you in Level 3 AND Level 4.

// Level 3
function calculateBasePlusTiered(config: BasePlusTieredConfig, order: Order): number {
  // For quantities <= coversUpTo: charge baseFlat.amount.
  //   For quantities > coversUpTo: charge baseFlat.amount + tiered pricing
  //   on (quantity - coversUpTo) using the tiers array.

  //   If the (destination, product) pair is not in config, return -1.

  const destination = config[order.destination];
  if (!destination) return -1;
  const product = destination[order.product];
  if (!product || !product.tiers || !product.baseFlat) return -1;

  const { tiers, baseFlat } = product;

  if (order.quantity <= baseFlat.coversUpTo) return baseFlat.amount;

  let total = baseFlat.amount;
  const overflow = order.quantity - baseFlat.coversUpTo;
  let prev = 0;

  for (const { upTo, unitPrice } of tiers) {
    const qty = Math.min(overflow, upTo) - prev;
    if (qty <= 0) break;
    total += qty * unitPrice;
    prev = upTo;
  }

  return total;
}
// REVIEW: Logic is correct now (after the prev fix). But this is a
// copy-paste of the tiered loop from Level 2. If you had extracted
// priceTiered(qty, tiers), this entire function would be:
//
//   const product = lookup(config, order.destination, order.product);
//   if (!product) return -1;
//   if (order.quantity <= product.baseFlat.coversUpTo) return product.baseFlat.amount;
//   return product.baseFlat.amount + priceTiered(order.quantity - product.baseFlat.coversUpTo, product.tiers);
//
// 4 lines, zero chance of the prev bug because priceTiered always starts at 0.

// Level 4
function calculateMulti(config: MultiConfig, order: MultiOrder, discount?: Discount): OrderResult {

    //   Process each line item using its pricing type (flat, tiered, or basePlusTiered).
    // If any product is missing from config, its subtotal is -1 and it is excluded
    // from the order subtotal/discount/total (treat as an error line).

    // If discount is provided and the subtotal (of valid items) > threshold,
    // apply the percentage discount (0-100) to get the discount amount.
    // total = subtotal - discount.

    // Return itemized breakdown and totals.

  const destination = config[order.destination];

  const itemized: OrderResult = order.items.reduce<OrderResult>((result: OrderResult, { product, quantity }) => {
    const productConfig = destination[product];
    if (!productConfig) {
      result.items.push({ product, subtotal: -1 });
      return result;
    };

    const item = {
      product,
      subtotal: 0,
    }
    switch (productConfig.type) {
      case 'flat':
        item.subtotal = quantity * productConfig.unitPrice
        result.items.push(item);
        result.subtotal += item.subtotal;
        return result;
      case 'tiered':
        
        let total = 0, prev = 0;

        for (const { upTo, unitPrice } of productConfig.tiers) {
          const qty = Math.min(quantity, upTo) - prev;
          if (qty <= 0) break;
          total += qty * unitPrice;
          prev = upTo;
        }

        item.subtotal = total;

        result.items.push(item);
        result.subtotal += total;
        return result;
      case 'basePlusTiered':
        const { tiers, baseFlat } = productConfig;

        if (quantity <= baseFlat.coversUpTo) {
          item.subtotal = baseFlat.amount;
        } else {
          let thisTotal = baseFlat.amount;
          const overflow = quantity - baseFlat.coversUpTo;
          let thisPrev = 0;

          for (const { upTo, unitPrice } of tiers) {
            const qty = Math.min(overflow, upTo) - thisPrev;
            if (qty <= 0) break;
            thisTotal += qty * unitPrice;
            thisPrev = upTo;
          }

          item.subtotal = thisTotal;
        }

        result.items.push(item);
        result.subtotal += item.subtotal;

        return result;
      default:
        result.items.push({ product, subtotal: -1 });
        return result;
    }
  }, { items: [], subtotal: 0, discount: 0, total: 0 });

  //calculate discount

  if (discount && itemized.subtotal > discount.threshold) {
    const discountAmount = Math.round(((itemized.subtotal / 100) * discount.percentage) * 10) / 10;
    itemized.discount = discountAmount;
    itemized.total = itemized.subtotal - discountAmount;
  } else {
    itemized.total = itemized.subtotal;
  }

  return itemized;
}
// REVIEW: This works but it's 70 lines because you re-implemented the
// tiered loop twice (lines 268-273 and 290-295). With priceTiered extracted,
// the entire switch body becomes:
//   case 'flat':    return quantity * productConfig.unitPrice;
//   case 'tiered':  return priceTiered(quantity, productConfig.tiers);
//   case 'basePlusTiered': return quantity <= bf.coversUpTo
//     ? bf.amount : bf.amount + priceTiered(quantity - bf.coversUpTo, productConfig.tiers);
//
// Other notes:
// - Line 239: no null check on `destination`. If order.destination isn't
//   in config, `destination[product]` will throw. Add: if (!destination) ...
// - Line 307: the rounding `Math.round(... * 10) / 10` works for this
//   test case but is fragile. The spec says percentage of subtotal —
//   `subtotal * (percentage / 100)` is simpler and reads clearer.
//   118 * 0.10 = 11.8 — no rounding needed.
// - The reduce is fine but a simple for-of loop would be easier to read
//   and debug under interview pressure. Reduce forces you to return the
//   accumulator in every branch — easy to forget in a case block.

// ─── Self-Checks (do not edit below this line) ──────────────────

let _passed = 0;
let _failed = 0;

function check(label: string, actual: unknown, expected: unknown): void {
  const a = JSON.stringify(actual);
  const e = JSON.stringify(expected);
  if (Object.is(actual, expected) || a === e) {
    _passed++;
    console.log(`  ✓ ${label}`);
  } else {
    _failed++;
    console.log(`  ✗ ${label}`);
    console.log(`    expected: ${e}`);
    console.log(`         got: ${a}`);
  }
}

function level(name: string, fn: () => void): void {
  console.log(name);
  try {
    fn();
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    if (msg.startsWith("TODO:")) {
      console.log(`  ○ ${msg}`);
    } else {
      _failed++;
      console.log(`  ✗ ${msg}`);
    }
  }
}

function runSelfChecks(): void {
  const flatConfig: FlatConfig = {
    US: { widget: { unitPrice: 5 }, gadget: { unitPrice: 12 } },
    CA: { widget: { unitPrice: 7 } },
  };

  const tieredConfig: TieredConfig = {
    US: {
      widget: {
        tiers: [
          { upTo: 5, unitPrice: 10 },
          { upTo: 10, unitPrice: 8 },
          { upTo: Infinity, unitPrice: 5 },
        ],
      },
    },
    CA: {
      widget: {
        tiers: [
          { upTo: 3, unitPrice: 15 },
          { upTo: Infinity, unitPrice: 10 },
        ],
      },
    },
  };

  const baseTieredConfig: BasePlusTieredConfig = {
    US: {
      widget: {
        baseFlat: { amount: 20, coversUpTo: 3 },
        tiers: [
          { upTo: 5, unitPrice: 8 },
          { upTo: Infinity, unitPrice: 5 },
        ],
      },
    },
  };

  const multiConfig: MultiConfig = {
    US: {
      widget: { type: "flat", unitPrice: 5 },
      gadget: {
        type: "tiered",
        tiers: [
          { upTo: 5, unitPrice: 10 },
          { upTo: Infinity, unitPrice: 6 },
        ],
      },
      gizmo: {
        type: "basePlusTiered",
        baseFlat: { amount: 15, coversUpTo: 2 },
        tiers: [
          { upTo: 3, unitPrice: 7 },
          { upTo: Infinity, unitPrice: 4 },
        ],
      },
    },
  };

  level("Level 1 — Flat Per-Unit Pricing", () => {
    check("flat basic", calculateFlat(flatConfig, { destination: "US", product: "widget", quantity: 4 }), 20);
    check("flat different product", calculateFlat(flatConfig, { destination: "US", product: "gadget", quantity: 3 }), 36);
    check("flat missing product", calculateFlat(flatConfig, { destination: "US", product: "unknown", quantity: 1 }), -1);
    check("flat missing destination", calculateFlat(flatConfig, { destination: "MX", product: "widget", quantity: 1 }), -1);
  });

  level("Level 2 — Tiered Per-Unit Pricing", () => {
    check("tiered within first tier", calculateTiered(tieredConfig, { destination: "US", product: "widget", quantity: 3 }), 30);
    check("tiered spanning two tiers", calculateTiered(tieredConfig, { destination: "US", product: "widget", quantity: 7 }), 66);
    // 5 at $10 = $50, 5 at $8 = $40, 2 at $5 = $10, total = $100
    check("tiered spanning all tiers", calculateTiered(tieredConfig, { destination: "US", product: "widget", quantity: 12 }), 100);
    check("tiered missing config", calculateTiered(tieredConfig, { destination: "US", product: "unknown", quantity: 1 }), -1);
  });

  level("Level 3 — Flat Base + Tiered Overflow", () => {
    check("base covers all", calculateBasePlusTiered(baseTieredConfig, { destination: "US", product: "widget", quantity: 2 }), 20);
    check("base exactly at limit", calculateBasePlusTiered(baseTieredConfig, { destination: "US", product: "widget", quantity: 3 }), 20);
    // overflow = 7-3 = 4, tiers: [{upTo:5, unitPrice:8}, ...], 4 at $8 = $32, total = 20+32 = 52
    check("base + overflow", calculateBasePlusTiered(baseTieredConfig, { destination: "US", product: "widget", quantity: 7 }), 52);
  });

  level("Level 4 — Multi-Product Orders with Discounts", () => {
    const order: MultiOrder = {
      destination: "US",
      items: [
        { product: "widget", quantity: 4 },  // flat: 4*5 = 20
        { product: "gadget", quantity: 7 },   // tiered: 5*10 + 2*6 = 62
        { product: "gizmo", quantity: 5 },    // base+tiered: 15 + (3*7) = 15+21 = 36
      ],
    };
    const result = calculateMulti(multiConfig, order);
    check("multi itemized widget", result.items[0], { product: "widget", subtotal: 20 });
    check("multi itemized gadget", result.items[1], { product: "gadget", subtotal: 62 });
    check("multi itemized gizmo", result.items[2], { product: "gizmo", subtotal: 36 });
    check("multi subtotal", result.subtotal, 118);
    check("multi no discount", result.discount, 0);
    check("multi total", result.total, 118);

    const discountedResult = calculateMulti(multiConfig, order, { threshold: 100, percentage: 10 });
    check("multi discount applied", discountedResult.discount, 11.8);
    check("multi discounted total", discountedResult.total, 106.2);
  });
}

function main(): void {
  console.log("\nTiered Pricing / Shipping Cost Calculator\n");
  runSelfChecks();
  const total = _passed + _failed;
  console.log(`\n${_passed}/${total} passed`);
  if (_failed === 0 && total > 0) console.log("All tests passed.");
}

main();
