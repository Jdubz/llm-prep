/*
Drill 13 — Charge API Client

Build a client for a simulated payment charges API. Practices the
same patterns as the API Client drill: pagination, retry with
idempotency, and batch processing with error handling.

Reported Stripe integration exercise pattern.

Target time: 30 minutes for all 3 parts.

────────────────────────────────────
Part 1 — Fetch & Aggregate (10 min)

  The server has 15 seeded charges and exposes:
    GET /charges          → { data: Charge[], has_more: boolean }
      ?limit=5              max per page (default 5)
      ?starting_after=ID    cursor for next page
    GET /charges/:id      → Charge (404 if not found)

  Implement:
    listAllCharges(): Promise<Charge[]>
      Paginate through ALL charges.

    getSummary(): Promise<Summary>
      Return { totalAmount, count, byStatus } where byStatus is
      a Record<string, number> counting charges per status.

  Example:
    await client.listAllCharges()  → [ch_001, ..., ch_015]
    await client.getSummary()
    → { totalAmount: ..., count: 15, byStatus: { succeeded: 12, failed: 3 } }

────────────────────────────────────
Part 2 — Create with Retry (10 min)

  POST /charges          → Charge (body: { amount, currency })
    Server returns 500 on every 3rd POST. Accepts Idempotency-Key header.

  Implement:
    createCharge(amount: number, currency: string, idempotencyKey: string): Promise<Charge>
      POST to /charges. If server returns status 500, retry up to 3
      times with the same idempotency key. Throw on other errors.

  Remember: server.request() does NOT throw on 500 — it returns
  { status: 500, body: {...} }. You must check status yourself.

────────────────────────────────────
Part 3 — Batch Refunds (10 min)

  POST /charges/:id/refund  → Refund (body: { amount? })
    amount is optional (full refund if omitted).
    Returns 400 if charge not found or already refunded.

  type RefundRequest = { chargeId: string; amount?: number }
  type RefundResult = { chargeId: string; success: boolean; refund?: Refund; error?: string }

  processRefunds(requests: RefundRequest[]): Promise<RefundResult[]>
    Process each refund independently — a failure doesn't stop the batch.
    Return one result per request in the same order.
*/

// ─── Simulated Server (do not edit) ────────────────────────────

type Charge = {
  id: string;
  amount: number;
  currency: string;
  status: "succeeded" | "failed" | "refunded";
  created: number;
};

type Refund = {
  id: string;
  chargeId: string;
  amount: number;
  created: number;
};

type Summary = {
  totalAmount: number;
  count: number;
  byStatus: Record<string, number>;
};

type RefundRequest = { chargeId: string; amount?: number };
type RefundResult = { chargeId: string; success: boolean; refund?: Refund; error?: string };

class FakeChargeServer {
  private charges = new Map<string, Charge>();
  private refunds = new Map<string, Refund>();
  private nextChargeId = 16;
  private nextRefundId = 1;
  private postCount = 0;
  private idempotencyCache = new Map<string, { status: number; body: any }>();

  constructor() {
    for (let i = 1; i <= 15; i++) {
      const id = `ch_${String(i).padStart(3, "0")}`;
      this.charges.set(id, {
        id,
        amount: 1000 + i * 500,
        currency: "usd",
        status: i % 5 === 0 ? "failed" : "succeeded",
        created: 1000 + i,
      });
    }
  }

  async request(
    method: string,
    path: string,
    body?: Record<string, unknown>,
    headers?: Record<string, string>,
  ): Promise<{ status: number; body: any }> {
    const pathOnly = path.split("?")[0];

    // Simulate 500 on every 3rd POST
    if (method === "POST") {
      this.postCount++;
      const idemKey = headers?.["Idempotency-Key"];
      if (idemKey && this.idempotencyCache.has(idemKey)) {
        return this.idempotencyCache.get(idemKey)!;
      }
      if (this.postCount % 3 === 0) {
        return { status: 500, body: { error: "Internal Server Error" } };
      }
    }

    // Routes
    const refundMatch = pathOnly.match(/^\/charges\/(.+)\/refund$/);
    const chargeMatch = pathOnly.match(/^\/charges\/(.+)$/);

    let response: { status: number; body: any };

    if (pathOnly === "/charges" && method === "GET") {
      response = this.handleList(path);
    } else if (pathOnly === "/charges" && method === "POST") {
      const id = `ch_${String(this.nextChargeId++).padStart(3, "0")}`;
      const charge: Charge = {
        id,
        amount: Number(body?.amount ?? 0),
        currency: String(body?.currency ?? "usd"),
        status: "succeeded",
        created: Date.now(),
      };
      this.charges.set(id, charge);
      response = { status: 201, body: charge };
    } else if (refundMatch && method === "POST") {
      response = this.handleRefund(refundMatch[1], body);
    } else if (chargeMatch && method === "GET") {
      const charge = this.charges.get(chargeMatch[1]);
      response = charge
        ? { status: 200, body: charge }
        : { status: 404, body: { error: "Not found" } };
    } else {
      response = { status: 404, body: { error: "Not found" } };
    }

    const idemKey = headers?.["Idempotency-Key"];
    if (idemKey && method === "POST") this.idempotencyCache.set(idemKey, response);
    return response;
  }

  private handleList(path: string): { status: number; body: any } {
    let charges = [...this.charges.values()].sort((a, b) => a.id.localeCompare(b.id));
    const url = new URL(`http://localhost${path}`);
    const limit = parseInt(url.searchParams.get("limit") ?? "5");
    const after = url.searchParams.get("starting_after");
    if (after) {
      const idx = charges.findIndex((c) => c.id === after);
      if (idx >= 0) charges = charges.slice(idx + 1);
    }
    const page = charges.slice(0, limit);
    return { status: 200, body: { data: page, has_more: charges.length > limit } };
  }

  private handleRefund(chargeId: string, body?: Record<string, unknown>): { status: number; body: any } {
    const charge = this.charges.get(chargeId);
    if (!charge) return { status: 400, body: { error: "Charge not found" } };
    if (charge.status === "refunded") return { status: 400, body: { error: "Already refunded" } };
    if (charge.status === "failed") return { status: 400, body: { error: "Cannot refund failed charge" } };
    const amount = body?.amount ? Number(body.amount) : charge.amount;
    charge.status = "refunded";
    const refund: Refund = {
      id: `re_${String(this.nextRefundId++).padStart(3, "0")}`,
      chargeId: charge.id,
      amount,
      created: Date.now(),
    };
    this.refunds.set(refund.id, refund);
    return { status: 201, body: refund };
  }
}

// ─── Your Implementation ───────────────────────────────────────

export class ChargeClient {
  constructor(private server: FakeChargeServer) {}

  // Part 1
  async listAllCharges(): Promise<Charge[]> { throw new Error("TODO"); }
  async getSummary(): Promise<Summary> { throw new Error("TODO"); }

  // Part 2
  async createCharge(amount: number, currency: string, idempotencyKey: string): Promise<Charge> { throw new Error("TODO"); }

  // Part 3
  async processRefunds(requests: RefundRequest[]): Promise<RefundResult[]> { throw new Error("TODO"); }
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

function part(name: string, fn: () => Promise<void>): Promise<void> {
  return new Promise((resolve) => {
    console.log(name);
    fn()
      .then(resolve)
      .catch((e) => {
        const msg = e instanceof Error ? e.message : String(e);
        if (msg.startsWith("TODO") || msg.includes("is not a function")) {
          console.log(`  ○ not yet implemented`);
        } else {
          _failed++;
          console.log(`  ✗ ${msg}`);
        }
        resolve();
      });
  });
}

async function runSelfChecks(): Promise<void> {
  await part("Part 1 — Fetch & Aggregate", async () => {
    const server = new FakeChargeServer();
    const client = new ChargeClient(server);

    const all = await client.listAllCharges();
    check("all charges count", all.length, 15);
    check("first id", all[0].id, "ch_001");
    check("last id", all[14].id, "ch_015");

    const summary = await client.getSummary();
    check("summary count", summary.count, 15);
    // Charges 5,10,15 are failed (3), rest succeeded (12)
    check("succeeded count", summary.byStatus["succeeded"], 12);
    check("failed count", summary.byStatus["failed"], 3);
    // Amounts: 1500,2000,2500,...,8500 = sum of 1000+i*500 for i=1..15
    // = 15*1000 + 500*(1+2+...+15) = 15000 + 500*120 = 15000 + 60000 = 75000
    check("total amount", summary.totalAmount, 75000);
  });

  await part("Part 2 — Create with Retry", async () => {
    const server = new FakeChargeServer();
    const client = new ChargeClient(server);

    // Should succeed despite intermittent 500s
    const charge = await client.createCharge(5000, "usd", "idem_001");
    check("created amount", charge.amount, 5000);
    check("created currency", charge.currency, "usd");
    check("has id", charge.id.startsWith("ch_"), true);

    // Same idempotency key returns same charge
    const duplicate = await client.createCharge(5000, "usd", "idem_001");
    check("idempotent same id", charge.id, duplicate.id);

    // Different key creates new charge
    const other = await client.createCharge(3000, "eur", "idem_002");
    check("different charge", other.id !== charge.id, true);
    check("different amount", other.amount, 3000);
  });

  await part("Part 3 — Batch Refunds", async () => {
    const server = new FakeChargeServer();
    const client = new ChargeClient(server);

    const results = await client.processRefunds([
      { chargeId: "ch_001" },                    // full refund → success
      { chargeId: "ch_002", amount: 500 },       // partial refund → success
      { chargeId: "ch_999" },                    // not found → error
      { chargeId: "ch_005" },                    // failed charge → error
    ]);

    check("result count", results.length, 4);
    check("refund 1 success", results[0].success, true);
    check("refund 1 amount", results[0].refund?.amount, 1500);
    check("refund 2 success", results[1].success, true);
    check("refund 2 partial", results[1].refund?.amount, 500);
    check("refund 3 not found", results[2].success, false);
    check("refund 3 error", results[2].error, "Charge not found");
    check("refund 4 failed charge", results[3].success, false);

    // Refunding already-refunded charge
    const results2 = await client.processRefunds([{ chargeId: "ch_001" }]);
    check("already refunded", results2[0].success, false);
    check("already refunded error", results2[0].error, "Already refunded");
  });
}

async function main(): Promise<void> {
  console.log("\nCharge API Client\n");
  await runSelfChecks();
  const total = _passed + _failed;
  console.log(`\n${_passed}/${total} passed`);
  if (_failed === 0 && total > 0) console.log("All tests passed.");
}

main();
