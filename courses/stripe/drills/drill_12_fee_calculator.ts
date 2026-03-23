/*
Drill 12 — Payment Fee Calculator

Calculate payment processing fees using graduated percentage tiers.
Same abstraction pattern as the shipping cost calculator (extract
the tiered math from the config lookup), but with percentage-based
fees — core Stripe domain.

Target time: 30 minutes for all 3 parts.

────────────────────────────────────
Part 1 — Flat Fee (8 min)

  calculateFlatFee(amountCents: number, percent: number, flatCents: number): number

  Fee = ceil(amountCents * percent / 100) + flatCents.
  Always round UP (Stripe convention — never undercharge the fee).
  If amountCents <= 0, return 0.

  Example (Stripe's standard US pricing):
    calculateFlatFee(10000, 2.9, 30)  → ceil(290) + 30 = 320
    calculateFlatFee(4999, 2.9, 30)   → ceil(144.971) + 30 = 175
    calculateFlatFee(1, 2.9, 30)      → ceil(0.029) + 30 = 31

────────────────────────────────────
Part 2 — Graduated Percentage Tiers (10 min)

  calculateTieredFee(amountCents: number, tiers: FeeTier[]): number

  Apply each tier's percentage only to the portion of the amount
  in that tier's range (graduated/marginal — same pattern as
  tiered pricing). Round UP the total.

  Tiers are sorted ascending by upTo. Last tier may use Infinity.

  Example:
    tiers: [{upTo: 10000, percent: 2.9}, {upTo: 100000, percent: 2.5}, {upTo: Infinity, percent: 2.0}]

    amountCents=15000:
      first 10000 at 2.9% = 290.0
      next 5000 at 2.5%   = 125.0
      total = ceil(415.0)  = 415

    amountCents=150000:
      first 10000 at 2.9%  = 290.0
      next 90000 at 2.5%   = 2250.0
      next 50000 at 2.0%   = 1000.0
      total = ceil(3540.0)  = 3540

  If amountCents <= 0, return 0.

────────────────────────────────────
Part 3 — Multi-Currency Batch (12 min)

  type CurrencyConfig = { tiers: FeeTier[]; flatCents: number; minimumCents: number }
  type FeeSchedule = Record<string, CurrencyConfig>
  type Charge = { id: string; amount: number; currency: string }
  type ChargeResult = { id: string; amount: number; fee: number; currency: string }

  processCharges(charges: Charge[], schedule: FeeSchedule): {
    results: ChargeResult[];
    totalFees: number;
  }

  For each charge:
    fee = max(calculateTieredFee(amount, tiers) + flatCents, minimumCents)
    If currency not in schedule, fee = -1 (excluded from totalFees).

  The key: if you extracted calculateTieredFee as a helper in Part 2,
  this is just a loop with a lookup + max().
*/

type FeeTier = { upTo: number; percent: number };

type CurrencyConfig = {
  tiers: FeeTier[];
  flatCents: number;
  minimumCents: number;
};

type FeeSchedule = Record<string, CurrencyConfig>;
type Charge = { id: string; amount: number; currency: string };
type ChargeResult = { id: string; amount: number; fee: number; currency: string };

// Part 1
function calculateFlatFee(amountCents: number, percent: number, flatCents: number): number {
  throw new Error("TODO");
}

// Part 2
function calculateTieredFee(amountCents: number, tiers: FeeTier[]): number {
  throw new Error("TODO");
}

// Part 3
function processCharges(charges: Charge[], schedule: FeeSchedule): {
  results: ChargeResult[];
  totalFees: number;
} {
  throw new Error("TODO");
}

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

function part(name: string, fn: () => void): void {
  console.log(name);
  try {
    fn();
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    if (msg.startsWith("TODO") || msg.includes("is not a function")) {
      console.log(`  ○ not yet implemented`);
    } else {
      _failed++;
      console.log(`  ✗ ${msg}`);
    }
  }
}

function runSelfChecks(): void {
  part("Part 1 — Flat Fee", () => {
    // Stripe standard: 2.9% + $0.30
    check("standard $100", calculateFlatFee(10000, 2.9, 30), 320);
    check("$49.99", calculateFlatFee(4999, 2.9, 30), 175);
    check("$0.01", calculateFlatFee(1, 2.9, 30), 31);
    check("round up", calculateFlatFee(1000, 1.5, 0), 15);
    check("round up fractional", calculateFlatFee(1001, 1.5, 0), 16);
    check("zero amount", calculateFlatFee(0, 2.9, 30), 0);
    check("negative amount", calculateFlatFee(-500, 2.9, 30), 0);
  });

  const tiers: FeeTier[] = [
    { upTo: 10000, percent: 2.9 },
    { upTo: 100000, percent: 2.5 },
    { upTo: Infinity, percent: 2.0 },
  ];

  part("Part 2 — Graduated Percentage Tiers", () => {
    // All in first tier
    check("within first tier", calculateTieredFee(5000, tiers), 145);
    // Exactly at first tier boundary
    check("at boundary", calculateTieredFee(10000, tiers), 290);
    // Spans two tiers: 10000*2.9% + 5000*2.5% = 290 + 125 = 415
    check("two tiers", calculateTieredFee(15000, tiers), 415);
    // Spans all three: 10000*2.9% + 90000*2.5% + 50000*2.0% = 290 + 2250 + 1000 = 3540
    check("all tiers", calculateTieredFee(150000, tiers), 3540);
    // Rounding: 777 * 2.9% = 22.533 → ceil = 23
    check("rounds up", calculateTieredFee(777, tiers), 23);
    check("zero", calculateTieredFee(0, tiers), 0);
  });

  part("Part 3 — Multi-Currency Batch", () => {
    const schedule: FeeSchedule = {
      usd: {
        tiers: [{ upTo: 10000, percent: 2.9 }, { upTo: Infinity, percent: 2.5 }],
        flatCents: 30,
        minimumCents: 50,
      },
      eur: {
        tiers: [{ upTo: Infinity, percent: 1.8 }],
        flatCents: 25,
        minimumCents: 50,
      },
    };

    const charges: Charge[] = [
      { id: "ch_1", amount: 10000, currency: "usd" }, // tiered:290 + flat:30 = 320, min:50 → 320
      { id: "ch_2", amount: 100, currency: "usd" },   // tiered:ceil(2.9)=3 + flat:30 = 33, min:50 → 50
      { id: "ch_3", amount: 5000, currency: "eur" },   // tiered:90 + flat:25 = 115, min:50 → 115
      { id: "ch_4", amount: 1000, currency: "gbp" },   // unknown → -1
    ];

    const result = processCharges(charges, schedule);
    check("ch_1 fee", result.results[0].fee, 320);
    check("ch_2 minimum applied", result.results[1].fee, 50);
    check("ch_3 eur fee", result.results[2].fee, 115);
    check("ch_4 unknown currency", result.results[3].fee, -1);
    check("total excludes unknown", result.totalFees, 485);
    check("result count", result.results.length, 4);
  });
}

function main(): void {
  console.log("\nPayment Fee Calculator\n");
  runSelfChecks();
  const total = _passed + _failed;
  console.log(`\n${_passed}/${total} passed`);
  if (_failed === 0 && total > 0) console.log("All tests passed.");
}

main();
