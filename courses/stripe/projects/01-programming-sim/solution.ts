/*
╔══════════════════════════════════════════════════════════════════╗
║                                                                  ║
║   REFERENCE SOLUTION — Do not open until you've completed        ║
║   your attempt. Seriously. Close this file now.                  ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝
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

type CustomerState = {
  plan: string | null;
  mrr: number;
  active: boolean;
  createdTimestamp: number;
};

// ─── Analytics Engine ────────────────────────────────────────────

export class SubscriptionAnalytics {
  private customers: Map<string, CustomerState> = new Map();
  private events: SubscriptionEvent[] = [];

  constructor() {
    // nothing needed — fields initialized inline
  }

  // ── Part 1 ──────────────────────────────────────────────────────

  ingest(events: SubscriptionEvent[]): void {
    for (const event of events) {
      this.events.push(event);
      this.processEvent(event);
    }
  }

  private processEvent(event: SubscriptionEvent): void {
    const { customerId, plan, action, mrr, timestamp } = event;

    switch (action) {
      case "created": {
        this.customers.set(customerId, {
          plan,
          mrr,
          active: true,
          createdTimestamp: timestamp,
        });
        break;
      }
      case "upgraded":
      case "downgraded":
      case "renewed": {
        const state = this.customers.get(customerId);
        if (state) {
          state.plan = plan;
          state.mrr = mrr;
          state.active = true;
        }
        break;
      }
      case "canceled": {
        const state = this.customers.get(customerId);
        if (state) {
          state.active = false;
          // keep plan set so we know what they were on when canceled
          // but getCustomerPlan returns null for canceled customers
        }
        break;
      }
    }
  }

  getActiveCount(): number {
    let count = 0;
    for (const state of this.customers.values()) {
      if (state.active) count++;
    }
    return count;
  }

  getActiveByPlan(): Map<string, number> {
    const counts = new Map<string, number>();
    for (const state of this.customers.values()) {
      if (state.active && state.plan) {
        counts.set(state.plan, (counts.get(state.plan) ?? 0) + 1);
      }
    }
    return counts;
  }

  getCustomerPlan(customerId: string): string | null {
    const state = this.customers.get(customerId);
    if (!state || !state.active) return null;
    return state.plan;
  }

  // ── Part 2 ──────────────────────────────────────────────────────

  getCurrentMRR(): number {
    let total = 0;
    for (const state of this.customers.values()) {
      if (state.active) total += state.mrr;
    }
    return total;
  }

  getMRRByPlan(): Map<string, number> {
    const mrrByPlan = new Map<string, number>();
    for (const state of this.customers.values()) {
      if (state.active && state.plan) {
        mrrByPlan.set(state.plan, (mrrByPlan.get(state.plan) ?? 0) + state.mrr);
      }
    }
    return mrrByPlan;
  }

  getMRRMovements(startTs: number, endTs: number): MRRMovements {
    // We need to know the MRR before each event to compute expansion/contraction.
    // Replay all events, tracking per-customer MRR, and accumulate movements for
    // events in the window.
    const customerMrr = new Map<string, number>();
    const result: MRRMovements = { new: 0, expansion: 0, contraction: 0, churn: 0, net: 0 };

    for (const event of this.events) {
      const prevMrr = customerMrr.get(event.customerId) ?? 0;

      // Update tracking regardless of window (we need accurate state)
      switch (event.action) {
        case "created":
          customerMrr.set(event.customerId, event.mrr);
          break;
        case "upgraded":
        case "downgraded":
        case "renewed":
          customerMrr.set(event.customerId, event.mrr);
          break;
        case "canceled":
          customerMrr.set(event.customerId, 0);
          break;
      }

      // Only accumulate movements for events in the window
      if (event.timestamp >= startTs && event.timestamp <= endTs) {
        switch (event.action) {
          case "created":
            result.new += event.mrr;
            break;
          case "upgraded":
            result.expansion += event.mrr - prevMrr;
            break;
          case "downgraded":
            result.contraction += prevMrr - event.mrr;
            break;
          case "canceled":
            result.churn += event.mrr;
            break;
          case "renewed":
            // No MRR movement for renewals (unless MRR changed, which we ignore)
            break;
        }
      }
    }

    result.net = result.new + result.expansion - result.contraction - result.churn;
    return result;
  }

  // ── Part 3 ──────────────────────────────────────────────────────

  getRetention(cohortMonth: string): number[] {
    // Find all customers created in the cohort month
    const [yearStr, monthStr] = cohortMonth.split("-");
    const cohortYear = parseInt(yearStr, 10);
    const cohortMonthNum = parseInt(monthStr, 10); // 1-indexed

    const cohortStart = Date.UTC(cohortYear, cohortMonthNum - 1, 1);
    const cohortEnd = Date.UTC(cohortYear, cohortMonthNum, 1); // exclusive: first day of next month

    const cohortCustomers: string[] = [];
    for (const event of this.events) {
      if (
        event.action === "created" &&
        event.timestamp >= cohortStart &&
        event.timestamp < cohortEnd
      ) {
        cohortCustomers.push(event.customerId);
      }
    }

    if (cohortCustomers.length === 0) return [];

    // Find the last month that contains any event
    let maxTimestamp = 0;
    for (const event of this.events) {
      if (event.timestamp > maxTimestamp) maxTimestamp = event.timestamp;
    }
    const maxDate = new Date(maxTimestamp);
    const lastYear = maxDate.getUTCFullYear();
    const lastMonth = maxDate.getUTCMonth(); // 0-indexed

    // Build cancellation times for cohort customers
    const cancelTimestamps = new Map<string, number>();
    for (const event of this.events) {
      if (event.action === "canceled" && cohortCustomers.includes(event.customerId)) {
        cancelTimestamps.set(event.customerId, event.timestamp);
      }
    }

    // Generate retention rates for each month from cohort month through last event month
    const retention: number[] = [];
    let currentYear = cohortYear;
    let currentMonth = cohortMonthNum - 1; // 0-indexed

    while (
      currentYear < lastYear ||
      (currentYear === lastYear && currentMonth <= lastMonth)
    ) {
      const monthStart = Date.UTC(currentYear, currentMonth, 1);
      let activeCount = 0;
      for (const customerId of cohortCustomers) {
        const cancelTs = cancelTimestamps.get(customerId);
        // Active at start of month = not canceled before the start of this month
        if (cancelTs === undefined || cancelTs >= monthStart) {
          activeCount++;
        }
      }
      retention.push(Math.round((activeCount / cohortCustomers.length) * 100));

      // Advance to next month
      currentMonth++;
      if (currentMonth > 11) {
        currentMonth = 0;
        currentYear++;
      }
    }

    return retention;
  }

  getChurnRate(startTs: number, endTs: number): number {
    // Count active subscriptions at startTs (replay events up to but not including startTs)
    const activeAtStart = new Set<string>();
    for (const event of this.events) {
      if (event.timestamp >= startTs) break;
      switch (event.action) {
        case "created":
        case "upgraded":
        case "downgraded":
        case "renewed":
          activeAtStart.add(event.customerId);
          break;
        case "canceled":
          activeAtStart.delete(event.customerId);
          break;
      }
    }

    if (activeAtStart.size === 0) return 0;

    // Count cancellations in the window
    let canceledCount = 0;
    for (const event of this.events) {
      if (event.timestamp < startTs) continue;
      if (event.timestamp > endTs) break;
      if (event.action === "canceled") canceledCount++;
    }

    return Math.round((canceledCount / activeAtStart.size) * 100);
  }

  // ── Part 4 ──────────────────────────────────────────────────────

  getUpgradePaths(): Map<string, Map<string, number>> {
    // We need to track each customer's plan before upgrade
    const customerPlan = new Map<string, string>();
    const paths = new Map<string, Map<string, number>>();

    for (const event of this.events) {
      if (event.action === "created") {
        customerPlan.set(event.customerId, event.plan);
      } else if (event.action === "upgraded") {
        const fromPlan = customerPlan.get(event.customerId);
        if (fromPlan) {
          if (!paths.has(fromPlan)) {
            paths.set(fromPlan, new Map<string, number>());
          }
          const toPlanMap = paths.get(fromPlan)!;
          toPlanMap.set(event.plan, (toPlanMap.get(event.plan) ?? 0) + 1);
        }
        customerPlan.set(event.customerId, event.plan);
      } else if (event.action === "downgraded" || event.action === "renewed") {
        customerPlan.set(event.customerId, event.plan);
      }
      // canceled: don't update plan tracking (they might resubscribe)
    }

    return paths;
  }

  getAverageLifetime(plan: string): number {
    // Find customers who canceled while on the given plan.
    // Lifetime = cancellation timestamp - creation timestamp.
    const creationTime = new Map<string, number>();
    const lifetimes: number[] = [];
    const customerPlanAtCancel = new Map<string, string>();

    // Track creation times and current plan for each customer
    const currentPlan = new Map<string, string>();

    for (const event of this.events) {
      switch (event.action) {
        case "created":
          creationTime.set(event.customerId, event.timestamp);
          currentPlan.set(event.customerId, event.plan);
          break;
        case "upgraded":
        case "downgraded":
        case "renewed":
          currentPlan.set(event.customerId, event.plan);
          break;
        case "canceled": {
          const custPlan = currentPlan.get(event.customerId);
          if (custPlan === plan) {
            const created = creationTime.get(event.customerId);
            if (created !== undefined) {
              lifetimes.push(event.timestamp - created);
            }
          }
          break;
        }
      }
    }

    if (lifetimes.length === 0) return 0;
    const sum = lifetimes.reduce((a, b) => a + b, 0);
    return Math.round(sum / lifetimes.length);
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
  level("Part 1 \u2014 Event Ingestion & Active Counts", () => {
    const sa = new SubscriptionAnalytics();
    sa.ingest(EVENTS);

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

    const sa2 = new SubscriptionAnalytics();
    sa2.ingest(EVENTS.slice(0, 3));
    check("partial active count", sa2.getActiveCount(), 3);
    sa2.ingest(EVENTS.slice(3));
    check("full active count after two ingests", sa2.getActiveCount(), 3);
  });

  level("Part 2 \u2014 MRR Calculations", () => {
    const sa = new SubscriptionAnalytics();
    sa.ingest(EVENTS);

    check("current MRR", sa.getCurrentMRR(), 447);
    checkMap("MRR by plan", sa.getMRRByPlan(), { enterprise: 249, pro: 198 });

    const allTime = sa.getMRRMovements(0, ts("2025-01-01"));
    check("all-time new", allTime.new, 563);
    check("all-time expansion", allTime.expansion, 510);
    check("all-time contraction", allTime.contraction, 150);
    check("all-time churn", allTime.churn, 476);
    check("all-time net", allTime.net, 447);

    const jan = sa.getMRRMovements(ts("2024-01-01"), ts("2024-01-31"));
    check("jan new", jan.new, 157);
    check("jan expansion", jan.expansion, 0);
    check("jan contraction", jan.contraction, 0);
    check("jan churn", jan.churn, 0);
    check("jan net", jan.net, 157);

    const mar = sa.getMRRMovements(ts("2024-03-01"), ts("2024-03-31"));
    check("mar new", mar.new, 99);
    check("mar expansion", mar.expansion, 370);
    check("mar contraction", mar.contraction, 150);
    check("mar churn", mar.churn, 0);
    check("mar net", mar.net, 319);
  });

  level("Part 3 \u2014 Cohort Analysis", () => {
    const sa = new SubscriptionAnalytics();
    sa.ingest(EVENTS);

    const janCohort = sa.getRetention("2024-01");
    check("jan cohort length", janCohort.length, 5);
    check("jan cohort[0]", janCohort[0], 100);
    check("jan cohort[1] (feb)", janCohort[1], 100);
    check("jan cohort[2] (mar)", janCohort[2], 67);
    check("jan cohort[3] (apr)", janCohort[3], 67);
    check("jan cohort[4] (may)", janCohort[4], 33);

    const febCohort = sa.getRetention("2024-02");
    check("feb cohort length", febCohort.length, 4);
    check("feb cohort[0]", febCohort[0], 100);
    check("feb cohort[1] (mar)", febCohort[1], 100);
    check("feb cohort[2] (apr)", febCohort[2], 100);
    check("feb cohort[3] (may)", febCohort[3], 100);

    check("empty cohort", sa.getRetention("2023-06"), []);

    check("churn rate apr", sa.getChurnRate(ts("2024-04-01"), ts("2024-04-30")), 40);
    check("churn rate jan (no active)", sa.getChurnRate(ts("2024-01-01"), ts("2024-01-31")), 0);
    check("churn rate feb", sa.getChurnRate(ts("2024-02-01"), ts("2024-02-28")), 33);
  });

  level("Part 4 \u2014 Plan Migration Paths", () => {
    const sa = new SubscriptionAnalytics();
    sa.ingest(EVENTS);

    const paths = sa.getUpgradePaths();
    checkNestedMap("upgrade paths", paths, {
      starter: { pro: 3 },
      pro: { enterprise: 2 },
    });

    const starterLifetime = ts("2024-02-20") - ts("2024-01-25");
    check("avg lifetime starter", sa.getAverageLifetime("starter"), starterLifetime);

    const proLifetime = Math.round(((ts("2024-04-10") - ts("2024-03-05")) + (ts("2024-05-01") - ts("2024-02-15"))) / 2);
    check("avg lifetime pro", sa.getAverageLifetime("pro"), proLifetime);

    const enterpriseLifetime = ts("2024-04-01") - ts("2024-01-20");
    check("avg lifetime enterprise", sa.getAverageLifetime("enterprise"), enterpriseLifetime);

    check("avg lifetime unknown", sa.getAverageLifetime("basic"), 0);
  });
}

function main(): void {
  console.log("\nSubscription Analytics Engine (Solution)\n");
  runSelfChecks();
  const total = _passed + _failed;
  console.log(`\n${_passed}/${total} passed`);
  if (_failed === 0 && total > 0) console.log("All tests passed.");
}

main();
