/*
Stripe Programming Exercise Simulation
───────────────────────────────────────
Subscription Analytics Engine

Time limit: 50 minutes. Set a timer now.

Read the README.md for the full problem spec.
Run with: npx tsx starter.ts
Do NOT open solution.ts until you are done.
*/

// ─── Types ───────────────────────────────────────────────────────

export type SubscriptionEvent = {
  id: string;
  customerId: string;
  plan: string;
  action: "created" | "upgraded" | "downgraded" | "canceled" | "renewed";
  timestamp: number;
  mrr: number;
};

export type MRRMovements = {
  new: number;
  expansion: number;
  contraction: number;
  churn: number;
  net: number;
};

// ─── Analytics Engine ────────────────────────────────────────────

export class SubscriptionAnalytics {
  constructor() {
    throw new Error("TODO: implement constructor");
  }

  // Part 1 — Event Ingestion & Active Counts
  ingest(events: SubscriptionEvent[]): void {
    throw new Error("TODO: implement ingest");
  }

  getActiveCount(): number {
    throw new Error("TODO: implement getActiveCount");
  }

  getActiveByPlan(): Map<string, number> {
    throw new Error("TODO: implement getActiveByPlan");
  }

  getCustomerPlan(customerId: string): string | null {
    throw new Error("TODO: implement getCustomerPlan");
  }

  // Part 2 — MRR Calculations
  getCurrentMRR(): number {
    throw new Error("TODO: implement getCurrentMRR");
  }

  getMRRByPlan(): Map<string, number> {
    throw new Error("TODO: implement getMRRByPlan");
  }

  getMRRMovements(startTs: number, endTs: number): MRRMovements {
    throw new Error("TODO: implement getMRRMovements");
  }

  // Part 3 — Cohort Analysis
  getRetention(cohortMonth: string): number[] {
    throw new Error("TODO: implement getRetention");
  }

  getChurnRate(startTs: number, endTs: number): number {
    throw new Error("TODO: implement getChurnRate");
  }

  // Part 4 — Plan Migration Paths
  getUpgradePaths(): Map<string, Map<string, number>> {
    throw new Error("TODO: implement getUpgradePaths");
  }

  getAverageLifetime(plan: string): number {
    throw new Error("TODO: implement getAverageLifetime");
  }
}

// ─── Self-Checks (do not edit below this line) ──────────────────

let _passed = 0;
let _failed = 0;

function check(label: string, actual: unknown, expected: unknown): void {
  const a = JSON.stringify(actual);
  const e = JSON.stringify(expected);
  if (Object.is(actual, expected) || a === e) {
    _passed++;
    console.log(`  \u2713 ${label}`);
  } else {
    _failed++;
    console.log(`  \u2717 ${label}`);
    console.log(`    expected: ${e}`);
    console.log(`         got: ${a}`);
  }
}

function checkMap(label: string, actual: Map<string, unknown>, expected: Record<string, unknown>): void {
  const actualObj: Record<string, unknown> = {};
  for (const [k, v] of actual) actualObj[k] = v;
  const a = JSON.stringify(actualObj, Object.keys(actualObj).sort());
  const e = JSON.stringify(expected, Object.keys(expected).sort());
  if (a === e) {
    _passed++;
    console.log(`  \u2713 ${label}`);
  } else {
    _failed++;
    console.log(`  \u2717 ${label}`);
    console.log(`    expected: ${e}`);
    console.log(`         got: ${a}`);
  }
}

function checkNestedMap(
  label: string,
  actual: Map<string, Map<string, number>>,
  expected: Record<string, Record<string, number>>,
): void {
  const actualObj: Record<string, Record<string, number>> = {};
  for (const [k, v] of actual) {
    actualObj[k] = {};
    for (const [k2, v2] of v) actualObj[k][k2] = v2;
  }
  const a = JSON.stringify(actualObj, Object.keys(actualObj).sort());
  const e = JSON.stringify(expected, Object.keys(expected).sort());
  if (a === e) {
    _passed++;
    console.log(`  \u2713 ${label}`);
  } else {
    _failed++;
    console.log(`  \u2717 ${label}`);
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
      console.log(`  \u25CB ${msg}`);
    } else {
      _failed++;
      console.log(`  \u2717 ${msg}`);
    }
  }
}

// ─── Test Data ───────────────────────────────────────────────────
//
// Timeline (all timestamps in ms):
//   2024-01-15  c1 created starter $29
//   2024-01-20  c2 created pro $99
//   2024-01-25  c3 created starter $29
//   2024-02-01  c4 created enterprise $249
//   2024-02-10  c1 upgraded to pro $99
//   2024-02-15  c5 created starter $29
//   2024-02-20  c3 canceled starter $29
//   2024-03-01  c2 upgraded to enterprise $249
//   2024-03-05  c6 created pro $99
//   2024-03-10  c1 upgraded to enterprise $249
//   2024-03-15  c5 upgraded to pro $99
//   2024-03-20  c4 downgraded to pro $99
//   2024-04-01  c2 canceled enterprise $249
//   2024-04-10  c6 canceled pro $99
//   2024-04-15  c7 created starter $29
//   2024-04-20  c1 renewed enterprise $249
//   2024-05-01  c5 canceled pro $99
//   2024-05-10  c7 upgraded to pro $99

function ts(dateStr: string): number {
  return new Date(dateStr + "T00:00:00Z").getTime();
}

const EVENTS: SubscriptionEvent[] = [
  { id: "e01", customerId: "c1", plan: "starter",    action: "created",    timestamp: ts("2024-01-15"), mrr: 29  },
  { id: "e02", customerId: "c2", plan: "pro",        action: "created",    timestamp: ts("2024-01-20"), mrr: 99  },
  { id: "e03", customerId: "c3", plan: "starter",    action: "created",    timestamp: ts("2024-01-25"), mrr: 29  },
  { id: "e04", customerId: "c4", plan: "enterprise", action: "created",    timestamp: ts("2024-02-01"), mrr: 249 },
  { id: "e05", customerId: "c1", plan: "pro",        action: "upgraded",   timestamp: ts("2024-02-10"), mrr: 99  },
  { id: "e06", customerId: "c5", plan: "starter",    action: "created",    timestamp: ts("2024-02-15"), mrr: 29  },
  { id: "e07", customerId: "c3", plan: "starter",    action: "canceled",   timestamp: ts("2024-02-20"), mrr: 29  },
  { id: "e08", customerId: "c2", plan: "enterprise", action: "upgraded",   timestamp: ts("2024-03-01"), mrr: 249 },
  { id: "e09", customerId: "c6", plan: "pro",        action: "created",    timestamp: ts("2024-03-05"), mrr: 99  },
  { id: "e10", customerId: "c1", plan: "enterprise", action: "upgraded",   timestamp: ts("2024-03-10"), mrr: 249 },
  { id: "e11", customerId: "c5", plan: "pro",        action: "upgraded",   timestamp: ts("2024-03-15"), mrr: 99  },
  { id: "e12", customerId: "c4", plan: "pro",        action: "downgraded", timestamp: ts("2024-03-20"), mrr: 99  },
  { id: "e13", customerId: "c2", plan: "enterprise", action: "canceled",   timestamp: ts("2024-04-01"), mrr: 249 },
  { id: "e14", customerId: "c6", plan: "pro",        action: "canceled",   timestamp: ts("2024-04-10"), mrr: 99  },
  { id: "e15", customerId: "c7", plan: "starter",    action: "created",    timestamp: ts("2024-04-15"), mrr: 29  },
  { id: "e16", customerId: "c1", plan: "enterprise", action: "renewed",    timestamp: ts("2024-04-20"), mrr: 249 },
  { id: "e17", customerId: "c5", plan: "pro",        action: "canceled",   timestamp: ts("2024-05-01"), mrr: 99  },
  { id: "e18", customerId: "c7", plan: "pro",        action: "upgraded",   timestamp: ts("2024-05-10"), mrr: 99  },
];

// ─── Checks ──────────────────────────────────────────────────────

function runSelfChecks(): void {
  // ── Part 1 ──────────────────────────────────────────────────────
  level("Part 1 \u2014 Event Ingestion & Active Counts", () => {
    const sa = new SubscriptionAnalytics();
    sa.ingest(EVENTS);

    // After all events:
    //   c1: enterprise (active)  — created starter, upgraded pro, upgraded enterprise, renewed
    //   c2: canceled             — created pro, upgraded enterprise, canceled
    //   c3: canceled             — created starter, canceled
    //   c4: pro (active)         — created enterprise, downgraded pro
    //   c5: canceled             — created starter, upgraded pro, canceled
    //   c6: canceled             — created pro, canceled
    //   c7: pro (active)         — created starter, upgraded pro
    // Active: c1 (enterprise), c4 (pro), c7 (pro) => 3

    check("active count", sa.getActiveCount(), 3);
    checkMap("active by plan", sa.getActiveByPlan(), { enterprise: 1, pro: 2 });
    check("c1 plan", sa.getCustomerPlan("c1"), "enterprise");
    check("c2 plan (canceled)", sa.getCustomerPlan("c2"), null);
    check("c3 plan (canceled)", sa.getCustomerPlan("c3"), null);
    check("c4 plan", sa.getCustomerPlan("c4"), "pro");
    check("c5 plan (canceled)", sa.getCustomerPlan("c5"), null);
    check("c6 plan (canceled)", sa.getCustomerPlan("c6"), null);
    check("c7 plan", sa.getCustomerPlan("c7"), "pro");
    check("unknown customer", sa.getCustomerPlan("c99"), null);

    // Test incremental ingest
    const sa2 = new SubscriptionAnalytics();
    sa2.ingest(EVENTS.slice(0, 3));
    check("partial active count", sa2.getActiveCount(), 3);
    sa2.ingest(EVENTS.slice(3));
    check("full active count after two ingests", sa2.getActiveCount(), 3);
  });

  // ── Part 2 ──────────────────────────────────────────────────────
  level("Part 2 \u2014 MRR Calculations", () => {
    const sa = new SubscriptionAnalytics();
    sa.ingest(EVENTS);

    // Active: c1 enterprise $249, c4 pro $99, c7 pro $99
    // Total MRR = 249 + 99 + 99 = 447
    check("current MRR", sa.getCurrentMRR(), 447);
    checkMap("MRR by plan", sa.getMRRByPlan(), { enterprise: 249, pro: 198 });

    // MRR movements for all time
    // new: c1(29) + c2(99) + c3(29) + c4(249) + c5(29) + c6(99) + c7(29) = 563
    // expansion: c1 starter->pro (99-29=70) + c2 pro->enterprise (249-99=150)
    //          + c1 pro->enterprise (249-99=150) + c5 starter->pro (99-29=70)
    //          + c7 starter->pro (99-29=70) = 510
    // contraction: c4 enterprise->pro (249-99=150) = 150
    // churn: c3(29) + c2(249) + c6(99) + c5(99) = 476
    // net: 563 + 510 - 150 - 476 = 447
    const allTime = sa.getMRRMovements(0, ts("2025-01-01"));
    check("all-time new", allTime.new, 563);
    check("all-time expansion", allTime.expansion, 510);
    check("all-time contraction", allTime.contraction, 150);
    check("all-time churn", allTime.churn, 476);
    check("all-time net", allTime.net, 447);

    // MRR movements for January 2024 only
    // new: c1(29) + c2(99) + c3(29) = 157
    // expansion: 0
    // contraction: 0
    // churn: 0
    // net: 157
    const jan = sa.getMRRMovements(ts("2024-01-01"), ts("2024-01-31"));
    check("jan new", jan.new, 157);
    check("jan expansion", jan.expansion, 0);
    check("jan contraction", jan.contraction, 0);
    check("jan churn", jan.churn, 0);
    check("jan net", jan.net, 157);

    // MRR movements for March 2024
    // new: c6(99) = 99
    // expansion: c2 pro->enterprise (150) + c1 pro->enterprise (150) + c5 starter->pro (70) = 370
    // contraction: c4 enterprise->pro (150) = 150
    // churn: 0
    // net: 99 + 370 - 150 - 0 = 319
    const mar = sa.getMRRMovements(ts("2024-03-01"), ts("2024-03-31"));
    check("mar new", mar.new, 99);
    check("mar expansion", mar.expansion, 370);
    check("mar contraction", mar.contraction, 150);
    check("mar churn", mar.churn, 0);
    check("mar net", mar.net, 319);
  });

  // ── Part 3 ──────────────────────────────────────────────────────
  level("Part 3 \u2014 Cohort Analysis", () => {
    const sa = new SubscriptionAnalytics();
    sa.ingest(EVENTS);

    // January 2024 cohort: c1, c2, c3
    // Jan (month 0): all 3 active => 100%
    // Feb: c3 canceled on Feb 20 => c1, c2 active at start of Feb => 3 active at start, but
    //   actually "start of Feb" means before Feb events. At start of Feb all 3 still active.
    //   c3 canceled during Feb so at start of Mar: c1, c2 active = 2/3 => 67%
    //   Wait, let me re-read: "active at start of month N" = not canceled before start of month N.
    //
    //   Start of Jan: all created during Jan, so at start of Jan they haven't been created yet...
    //   Actually, index 0 is the cohort month itself and is always 100.
    //
    //   Let me think about this more carefully:
    //   Index 0 = Jan 2024 = 100 (by definition)
    //   Index 1 = Feb 2024: c3 canceled Feb 20. At start of Feb (Feb 1), c3 is still active. 3/3 = 100
    //   Index 2 = Mar 2024: c3 canceled Feb 20 (before Mar 1). So c1,c2 active at start of Mar. 2/3 = 67
    //   Index 3 = Apr 2024: c2 canceled Apr 1. At start of Apr, c2 still active? Apr 1 is start of Apr.
    //     c2 canceled ON Apr 1. "canceled before start of month" - if canceled at ts("2024-04-01") and
    //     start of Apr is ts("2024-04-01"), the cancellation is AT the start, not before. So c1,c2 active. 2/3 = 67
    //   Index 4 = May 2024: c2 canceled Apr 1 which is before May 1. c1 active. 1/3 = 33
    //   Last event is May 10, so last month with events is May 2024.
    //
    const janCohort = sa.getRetention("2024-01");
    check("jan cohort length", janCohort.length, 5);
    check("jan cohort[0]", janCohort[0], 100);
    check("jan cohort[1] (feb)", janCohort[1], 100);
    check("jan cohort[2] (mar)", janCohort[2], 67);
    check("jan cohort[3] (apr)", janCohort[3], 67);
    check("jan cohort[4] (may)", janCohort[4], 33);

    // February 2024 cohort: c4, c5
    // Index 0 = Feb = 100
    // Index 1 = Mar: c4,c5 both active at start of Mar => 100
    // Index 2 = Apr: c4,c5 both active at start of Apr => 100
    // Index 3 = May: c5 canceled May 1, at start of May c5 still active? Same logic: canceled AT start = still active. 2/2 = 100
    //   Actually let me reconsider. c5 canceled on May 1. Start of May is May 1.
    //   "not canceled before start of month N" - "before" means strictly before. Canceled ON May 1 is not before May 1. So active. 100.
    //   But wait, the last month with events is May. So we go through May.
    const febCohort = sa.getRetention("2024-02");
    check("feb cohort length", febCohort.length, 4);
    check("feb cohort[0]", febCohort[0], 100);
    check("feb cohort[1] (mar)", febCohort[1], 100);
    check("feb cohort[2] (apr)", febCohort[2], 100);
    check("feb cohort[3] (may)", febCohort[3], 100);

    // Empty cohort
    check("empty cohort", sa.getRetention("2023-06"), []);

    // Churn rate: April 2024
    // Active at start of Apr (before Apr events): c1, c2, c4, c5, c6 = wait let me recount
    // At start of Apr (ts 2024-04-01), who is active?
    //   c1: active (enterprise) - yes
    //   c2: upgraded to enterprise in Mar, not yet canceled - yes
    //   c3: canceled Feb 20 - no
    //   c4: downgraded to pro in Mar - yes
    //   c5: upgraded to pro in Mar - yes
    //   c6: created pro Mar 5 - yes
    // Active at start of Apr: c1, c2, c4, c5, c6 = 5
    // Canceled in Apr: c2 (Apr 1), c6 (Apr 10) = 2
    // Churn rate = round(2/5 * 100) = 40
    check("churn rate apr", sa.getChurnRate(ts("2024-04-01"), ts("2024-04-30")), 40);

    // Churn rate: January 2024 (no cancellations)
    // Active at start of Jan (before Jan events): 0 customers
    // Return 0 if no active subscriptions at startTs
    check("churn rate jan (no active)", sa.getChurnRate(ts("2024-01-01"), ts("2024-01-31")), 0);

    // Churn rate: Feb 2024
    // Active at start of Feb: c1, c2, c3 = 3
    // Canceled in Feb: c3 = 1
    // Churn rate = round(1/3 * 100) = 33
    check("churn rate feb", sa.getChurnRate(ts("2024-02-01"), ts("2024-02-28")), 33);
  });

  // ── Part 4 ──────────────────────────────────────────────────────
  level("Part 4 \u2014 Plan Migration Paths", () => {
    const sa = new SubscriptionAnalytics();
    sa.ingest(EVENTS);

    // Upgrades:
    //   c1: starter -> pro (e05)
    //   c2: pro -> enterprise (e08)
    //   c1: pro -> enterprise (e10)
    //   c5: starter -> pro (e11)
    //   c7: starter -> pro (e18)
    const paths = sa.getUpgradePaths();
    checkNestedMap("upgrade paths", paths, {
      starter: { pro: 3 },
      pro: { enterprise: 2 },
    });

    // Average lifetime for canceled customers by plan at cancellation:
    //   c3: canceled starter, created Jan 25, canceled Feb 20
    //       lifetime = ts("2024-02-20") - ts("2024-01-25") = 26 days
    //   c2: canceled enterprise, created Jan 20, canceled Apr 1
    //       lifetime = ts("2024-04-01") - ts("2024-01-20") = 72 days
    //   c6: canceled pro, created Mar 5, canceled Apr 10
    //       lifetime = ts("2024-04-10") - ts("2024-03-05") = 36 days
    //   c5: canceled pro, created Feb 15, canceled May 1
    //       lifetime = ts("2024-05-01") - ts("2024-02-15") = 76 days

    const starterLifetime = ts("2024-02-20") - ts("2024-01-25");
    check("avg lifetime starter", sa.getAverageLifetime("starter"), starterLifetime);

    const proLifetime = Math.round(((ts("2024-04-10") - ts("2024-03-05")) + (ts("2024-05-01") - ts("2024-02-15"))) / 2);
    check("avg lifetime pro", sa.getAverageLifetime("pro"), proLifetime);

    const enterpriseLifetime = ts("2024-04-01") - ts("2024-01-20");
    check("avg lifetime enterprise", sa.getAverageLifetime("enterprise"), enterpriseLifetime);

    // No cancellations on a plan that doesn't exist
    check("avg lifetime unknown", sa.getAverageLifetime("basic"), 0);
  });
}

function main(): void {
  console.log("\nSubscription Analytics Engine\n");
  runSelfChecks();
  const total = _passed + _failed;
  console.log(`\n${_passed}/${total} passed`);
  if (_failed === 0 && total > 0) console.log("All tests passed.");
}

main();
