/*
Drill 06 — Express API + Testing (Integration Exercise Prep)

Build and test an Express API server with routes, middleware, and
external API integration. This is the closest simulation to the
actual Integration Exercise format: you're given an existing
server and spec, and need to add functionality + tests.

Run: npx tsx drill_06_express_api.ts
Requires: npm install express stripe

If express/stripe aren't installed, the drill installs them
automatically (see bottom of file).

Target time: 40 minutes for all 4 levels.

────────────────────────────────────────
Level 1 — CRUD Routes

  Given the provided Express app skeleton, implement:

  POST   /users          → Create user { name, email }
                           Returns 201 + { id, name, email, created_at }
                           Returns 400 if name or email missing

  GET    /users/:id      → Get user by id
                           Returns 200 + user object
                           Returns 404 + { error: "Not found" }

  GET    /users          → List all users
                           Supports ?email= filter (exact, case-insensitive)
                           Returns 200 + { data: User[], count: number }

  PUT    /users/:id      → Update user (partial update)
                           Returns 200 + updated user
                           Returns 404 if not found

  DELETE /users/:id      → Delete user
                           Returns 200 + { deleted: true }
                           Returns 404 if not found

────────────────────────────────────────
Level 2 — Middleware & Validation

  Add middleware to the app:

  requestLogger: Logs method, path, status, and duration (ms)
    to the provided logs array. Runs on ALL routes.

  apiKeyAuth: Reads "x-api-key" header. If missing or doesn't
    match the expected key, return 401 + { error: "Unauthorized" }.
    Runs on ALL routes except GET /health.

  validateBody(required: string[]): Returns middleware that checks
    req.body has all required keys with non-empty string values.
    Returns 400 + { error: "Missing fields", fields: [...] }
    if validation fails.

  GET /health → Returns 200 + { status: "ok" } (no auth required)

────────────────────────────────────────
Level 3 — External API Integration

  Add a route that calls an external API (simulated by FakeStripeAPI):

  POST /charges
    Body: { amount: number, currency: string, source: string,
            description?: string, idempotency_key?: string }
    - Validate required fields (amount, currency, source)
    - amount must be > 0 and an integer (cents)
    - currency must be 3 lowercase letters
    - Call FakeStripeAPI.createCharge() with the data
    - If idempotency_key provided, pass it in headers
    - Return 201 + charge object on success
    - Return 402 + { error } if charge is declined
    - Return 500 + { error } on API errors

  GET /charges/:id
    - Call FakeStripeAPI.getCharge(id)
    - Return 200 + charge, or 404

  POST /refunds
    Body: { charge_id: string, amount?: number }
    - Call FakeStripeAPI.createRefund()
    - amount is optional (full refund if omitted)
    - Return 201 + refund object
    - Return 400 if charge not found or already fully refunded

────────────────────────────────────────
Level 4 — Webhook Handler + Tests

  POST /webhooks/stripe
    - Read raw body (important: must use raw body for signature verification)
    - Verify signature using FakeStripeAPI.verifyWebhookSignature()
    - Return 400 if signature invalid
    - Handle event types:
      "charge.succeeded" → store in processed events
      "charge.refunded"  → store in processed events
      "charge.failed"    → store in processed events
    - Deduplicate by event id
    - Return 200 + { received: true }

  getProcessedWebhooks(): WebhookEvent[]
    Returns all processed webhook events in order.

  Write tests (using the built-in test harness) for:
    - Creating a user and retrieving it
    - Auth middleware rejects missing API key
    - Creating a charge and refunding it
    - Webhook signature verification
    - Idempotency (same key = same response)
*/

// ─── Fake Stripe API (simulates external API calls) ────────────

type Charge = {
  id: string;
  amount: number;
  currency: string;
  source: string;
  status: "succeeded" | "failed";
  description: string;
  amount_refunded: number;
  created: number;
};

type Refund = {
  id: string;
  charge: string;
  amount: number;
  status: "succeeded";
  created: number;
};

type WebhookEvent = {
  id: string;
  type: string;
  data: { object: Record<string, unknown> };
  signature: string;
};

class FakeStripeAPI {
  private charges = new Map<string, Charge>();
  private refunds = new Map<string, Refund>();
  private nextChargeId = 1;
  private nextRefundId = 1;
  private idempotencyCache = new Map<string, Charge>();
  readonly webhookSecret = "whsec_test_secret_123";

  async createCharge(data: {
    amount: number;
    currency: string;
    source: string;
    description?: string;
    idempotency_key?: string;
  }): Promise<{ status: number; body: Charge | { error: string } }> {
    // Idempotency check
    if (data.idempotency_key && this.idempotencyCache.has(data.idempotency_key)) {
      return { status: 200, body: this.idempotencyCache.get(data.idempotency_key)! };
    }

    // Simulate decline for specific test card
    if (data.source === "tok_declined") {
      return { status: 402, body: { error: "Card declined" } };
    }

    const charge: Charge = {
      id: `ch_${String(this.nextChargeId++).padStart(4, "0")}`,
      amount: data.amount,
      currency: data.currency,
      source: data.source,
      status: "succeeded",
      description: data.description ?? "",
      amount_refunded: 0,
      created: Date.now(),
    };
    this.charges.set(charge.id, charge);

    if (data.idempotency_key) {
      this.idempotencyCache.set(data.idempotency_key, charge);
    }

    return { status: 201, body: charge };
  }

  async getCharge(id: string): Promise<{ status: number; body: Charge | { error: string } }> {
    const charge = this.charges.get(id);
    if (!charge) return { status: 404, body: { error: "Charge not found" } };
    return { status: 200, body: charge };
  }

  async createRefund(data: {
    charge_id: string;
    amount?: number;
  }): Promise<{ status: number; body: Refund | { error: string } }> {
    const charge = this.charges.get(data.charge_id);
    if (!charge) return { status: 400, body: { error: "Charge not found" } };

    const refundAmount = data.amount ?? (charge.amount - charge.amount_refunded);
    if (refundAmount <= 0 || refundAmount > charge.amount - charge.amount_refunded) {
      return { status: 400, body: { error: "Invalid refund amount" } };
    }

    charge.amount_refunded += refundAmount;

    const refund: Refund = {
      id: `re_${String(this.nextRefundId++).padStart(4, "0")}`,
      charge: charge.id,
      amount: refundAmount,
      status: "succeeded",
      created: Date.now(),
    };
    this.refunds.set(refund.id, refund);

    return { status: 201, body: refund };
  }

  makeWebhookEvent(type: string, data: Record<string, unknown>): WebhookEvent {
    const id = `evt_${Math.random().toString(36).slice(2, 10)}`;
    const payload = JSON.stringify({ id, type, data: { object: data } });
    return {
      id,
      type,
      data: { object: data },
      signature: this.computeSignature(payload),
    };
  }

  verifyWebhookSignature(rawBody: string, signature: string): boolean {
    return signature === this.computeSignature(rawBody);
  }

  private computeSignature(payload: string): string {
    let hash = 0;
    const str = payload + this.webhookSecret;
    for (let i = 0; i < str.length; i++) {
      hash = ((hash << 5) - hash + str.charCodeAt(i)) | 0;
    }
    return "sig_" + Math.abs(hash).toString(36);
  }
}

// ─── Express App Skeleton ──────────────────────────────────────

/*
  YOUR IMPLEMENTATION GOES HERE.

  You'll build a createApp() function that returns an Express app.
  This function receives the FakeStripeAPI instance and config.

  The test harness below will call createApp(), make HTTP requests
  to it, and verify the responses.

  Scaffold:

  import express from "express";

  export function createApp(config: {
    stripeApi: FakeStripeAPI;
    apiKey: string;
    logs: LogEntry[];
  }) {
    const app = express();
    app.use(express.json());

    // ... implement routes and middleware ...

    return app;
  }
*/

type LogEntry = {
  method: string;
  path: string;
  status: number;
  durationMs: number;
};

type User = {
  id: string;
  name: string;
  email: string;
  created_at: number;
};

// Stub — replace with your implementation
function createApp(config: {
  stripeApi: FakeStripeAPI;
  apiKey: string;
  logs: LogEntry[];
}): any {
  throw new Error("TODO: implement createApp");
}

// ─── Test Harness (simulates HTTP without needing a running server) ──

class TestClient {
  private app: any;
  private users: Map<string, User> = new Map();
  private nextUserId = 1;
  private processedWebhooks: WebhookEvent[] = [];
  private processedEventIds = new Set<string>();

  constructor(
    private stripeApi: FakeStripeAPI,
    private apiKey: string,
    private logs: LogEntry[],
  ) {
    // We'll test by directly calling the createApp function
    // and simulating requests. For this drill, we use a
    // simplified request simulator instead of supertest.
  }

  // Simulated request — this is what you'd use supertest for
  // in a real integration test. Here we just call the function directly.
  async request(
    method: string,
    path: string,
    body?: Record<string, unknown>,
    headers?: Record<string, string>,
  ): Promise<{ status: number; body: any }> {
    // This is a simplified simulation. In the real interview,
    // you'd use the Express app with supertest or similar.
    throw new Error("TODO: implement via createApp");
  }
}

// ─── Self-Checks ───────────────────────────────────────────────
// Since this drill requires express (which may not be installed),
// we use a pure-TypeScript simulation that tests the same patterns.
// The logic is identical to what you'd write with Express.

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

function level(name: string, fn: () => Promise<void>): Promise<void> {
  return new Promise((resolve) => {
    console.log(name);
    fn()
      .then(resolve)
      .catch((e) => {
        const msg = e instanceof Error ? e.message : String(e);
        if (msg.startsWith("TODO:")) {
          console.log(`  ○ ${msg}`);
        } else {
          _failed++;
          console.log(`  ✗ ${msg}`);
        }
        resolve();
      });
  });
}

/*
  Because Express is an external dependency, this drill provides
  TWO ways to practice:

  OPTION A (recommended): Install express and implement createApp()
    npm install express @types/express
    Then implement createApp with real Express routes.
    To test, use supertest: npm install supertest @types/supertest

  OPTION B (no dependencies): Implement the Router class below
    which simulates Express routing patterns in pure TypeScript.
    Same logic, same patterns, zero npm installs.

  The self-checks below use Option B so they work out of the box.
*/

// ─── Option B: Pure TypeScript Express Simulator ───────────────

type Handler = (req: SimReq, res: SimRes, next?: () => void) => void | Promise<void>;
type Middleware = (req: SimReq, res: SimRes, next: () => void) => void | Promise<void>;

interface SimReq {
  method: string;
  path: string;
  params: Record<string, string>;
  query: Record<string, string>;
  body: any;
  headers: Record<string, string>;
  rawBody?: string;
}

interface SimRes {
  statusCode: number;
  _body: any;
  _sent: boolean;
  status(code: number): SimRes;
  json(data: any): void;
  send(data?: any): void;
}

function createSimRes(): SimRes {
  const res: SimRes = {
    statusCode: 200,
    _body: null,
    _sent: false,
    status(code: number) { res.statusCode = code; return res; },
    json(data: any) { res._body = data; res._sent = true; },
    send(data?: any) { res._body = data; res._sent = true; },
  };
  return res;
}

class Router {
  private middlewares: Middleware[] = [];
  private routes: Array<{
    method: string;
    pattern: string;
    handlers: Handler[];
  }> = [];

  use(...handlers: Middleware[]): void {
    this.middlewares.push(...handlers);
  }

  get(path: string, ...handlers: Handler[]): void {
    this.routes.push({ method: "GET", pattern: path, handlers });
  }

  post(path: string, ...handlers: Handler[]): void {
    this.routes.push({ method: "POST", pattern: path, handlers });
  }

  put(path: string, ...handlers: Handler[]): void {
    this.routes.push({ method: "PUT", pattern: path, handlers });
  }

  delete(path: string, ...handlers: Handler[]): void {
    this.routes.push({ method: "DELETE", pattern: path, handlers });
  }

  async handle(req: SimReq): Promise<SimRes> {
    const res = createSimRes();

    // Run global middleware
    for (const mw of this.middlewares) {
      let called = false;
      await mw(req, res, () => { called = true; });
      if (res._sent) return res;
      if (!called) return res;
    }

    // Find matching route
    for (const route of this.routes) {
      if (route.method !== req.method) continue;
      const params = matchRoute(route.pattern, req.path);
      if (params === null) continue;
      req.params = params;

      // Run route handlers (including route-level middleware)
      for (const handler of route.handlers) {
        let called = false;
        await handler(req, res, () => { called = true; });
        if (res._sent) return res;
      }
      return res;
    }

    res.statusCode = 404;
    res._body = { error: "Not found" };
    res._sent = true;
    return res;
  }
}

function matchRoute(pattern: string, path: string): Record<string, string> | null {
  const patternParts = pattern.split("/");
  const pathParts = path.split("?")[0].split("/");
  if (patternParts.length !== pathParts.length) return null;
  const params: Record<string, string> = {};
  for (let i = 0; i < patternParts.length; i++) {
    if (patternParts[i].startsWith(":")) {
      params[patternParts[i].slice(1)] = pathParts[i];
    } else if (patternParts[i] !== pathParts[i]) {
      return null;
    }
  }
  return params;
}

function parseQuery(path: string): Record<string, string> {
  const idx = path.indexOf("?");
  if (idx === -1) return {};
  const params: Record<string, string> = {};
  for (const pair of path.slice(idx + 1).split("&")) {
    const [k, v] = pair.split("=");
    if (k) params[decodeURIComponent(k)] = decodeURIComponent(v ?? "");
  }
  return params;
}

// ─── YOUR IMPLEMENTATION (Option B) ────────────────────────────

function createRouter(config: {
  stripeApi: FakeStripeAPI;
  apiKey: string;
  logs: LogEntry[];
}): Router {
  throw new Error("TODO: implement createRouter");

  // Example structure (delete this comment when implementing):
  //
  // const router = new Router();
  // const users = new Map<string, User>();
  // let nextId = 1;
  //
  // // Logging middleware
  // router.use(async (req, res, next) => {
  //   const start = Date.now();
  //   next();
  //   config.logs.push({
  //     method: req.method,
  //     path: req.path,
  //     status: res.statusCode,
  //     durationMs: Date.now() - start,
  //   });
  // });
  //
  // // Auth middleware
  // router.use((req, res, next) => {
  //   if (req.path === "/health") return next();
  //   if (req.headers["x-api-key"] !== config.apiKey) {
  //     return res.status(401).json({ error: "Unauthorized" });
  //   }
  //   next();
  // });
  //
  // router.get("/health", (req, res) => {
  //   res.json({ status: "ok" });
  // });
  //
  // ... etc
  //
  // return router;
}

// Helper to make simulated requests
async function request(
  router: Router,
  method: string,
  path: string,
  body?: any,
  headers?: Record<string, string>,
): Promise<{ status: number; body: any }> {
  const req: SimReq = {
    method,
    path: path.split("?")[0],
    params: {},
    query: parseQuery(path),
    body: body ?? {},
    headers: headers ?? {},
    rawBody: body ? JSON.stringify(body) : undefined,
  };
  const res = await router.handle(req);
  return { status: res.statusCode, body: res._body };
}

// ─── Self-Checks ───────────────────────────────────────────────

async function runSelfChecks(): Promise<void> {
  const stripeApi = new FakeStripeAPI();
  const logs: LogEntry[] = [];
  const apiKey = "sk_test_abc123";

  await level("Level 1 — CRUD Routes", async () => {
    const router = createRouter({ stripeApi, apiKey, logs });
    const h = { "x-api-key": apiKey };

    // Create user
    const created = await request(router, "POST", "/users", { name: "Alice", email: "alice@test.com" }, h);
    check("create status", created.status, 201);
    check("create name", created.body.name, "Alice");
    check("create email", created.body.email, "alice@test.com");
    check("create has id", typeof created.body.id, "string");

    const userId = created.body.id;

    // Get user
    const fetched = await request(router, "GET", `/users/${userId}`, undefined, h);
    check("get status", fetched.status, 200);
    check("get name", fetched.body.name, "Alice");

    // Get missing
    const missing = await request(router, "GET", "/users/nope", undefined, h);
    check("get 404", missing.status, 404);

    // List users
    const listed = await request(router, "GET", "/users", undefined, h);
    check("list status", listed.status, 200);
    check("list count", listed.body.count, 1);

    // Create second user
    await request(router, "POST", "/users", { name: "Bob", email: "bob@test.com" }, h);

    // List with email filter
    const filtered = await request(router, "GET", "/users?email=alice@test.com", undefined, h);
    check("filter count", filtered.body.count, 1);
    check("filter name", filtered.body.data[0].name, "Alice");

    // Update
    const updated = await request(router, "PUT", `/users/${userId}`, { name: "Alice Updated" }, h);
    check("update status", updated.status, 200);
    check("update name", updated.body.name, "Alice Updated");

    // Delete
    const deleted = await request(router, "DELETE", `/users/${userId}`, undefined, h);
    check("delete status", deleted.status, 200);
    check("delete body", deleted.body.deleted, true);

    // Get after delete
    const afterDelete = await request(router, "GET", `/users/${userId}`, undefined, h);
    check("after delete 404", afterDelete.status, 404);

    // Validation: missing fields
    const badCreate = await request(router, "POST", "/users", { name: "Alice" }, h);
    check("missing email 400", badCreate.status, 400);
  });

  await level("Level 2 — Middleware & Validation", async () => {
    logs.length = 0;
    const router = createRouter({ stripeApi, apiKey, logs });
    const h = { "x-api-key": apiKey };

    // Health check — no auth required
    const health = await request(router, "GET", "/health");
    check("health status", health.status, 200);
    check("health body", health.body.status, "ok");

    // Missing auth
    const noAuth = await request(router, "GET", "/users");
    check("no auth 401", noAuth.status, 401);

    // Wrong auth
    const badAuth = await request(router, "GET", "/users", undefined, { "x-api-key": "wrong" });
    check("bad auth 401", badAuth.status, 401);

    // Valid auth
    const authed = await request(router, "GET", "/users", undefined, h);
    check("valid auth 200", authed.status, 200);

    // Request logger
    check("logs recorded", logs.length > 0, true);
    check("log has method", typeof logs[0].method, "string");
    check("log has status", typeof logs[0].status, "number");
    check("log has duration", typeof logs[0].durationMs, "number");
  });

  await level("Level 3 — External API Integration", async () => {
    const router = createRouter({ stripeApi, apiKey, logs });
    const h = { "x-api-key": apiKey };

    // Create charge
    const charge = await request(router, "POST", "/charges", {
      amount: 2000,
      currency: "usd",
      source: "tok_visa",
      description: "Test charge",
    }, h);
    check("charge status", charge.status, 201);
    check("charge amount", charge.body.amount, 2000);
    check("charge id", charge.body.id.startsWith("ch_"), true);

    const chargeId = charge.body.id;

    // Get charge
    const fetched = await request(router, "GET", `/charges/${chargeId}`, undefined, h);
    check("get charge", fetched.status, 200);
    check("get charge amount", fetched.body.amount, 2000);

    // Get missing charge
    const missingCharge = await request(router, "GET", "/charges/ch_9999", undefined, h);
    check("missing charge 404", missingCharge.status, 404);

    // Declined card
    const declined = await request(router, "POST", "/charges", {
      amount: 1000,
      currency: "usd",
      source: "tok_declined",
    }, h);
    check("declined 402", declined.status, 402);

    // Validation
    const badCharge = await request(router, "POST", "/charges", { amount: 1000 }, h);
    check("missing fields 400", badCharge.status, 400);

    const badAmount = await request(router, "POST", "/charges", {
      amount: -5,
      currency: "usd",
      source: "tok_visa",
    }, h);
    check("negative amount 400", badAmount.status, 400);

    // Refund
    const refund = await request(router, "POST", "/refunds", { charge_id: chargeId, amount: 500 }, h);
    check("refund status", refund.status, 201);
    check("refund amount", refund.body.amount, 500);

    // Partial refund — remainder
    const refund2 = await request(router, "POST", "/refunds", { charge_id: chargeId }, h);
    check("full refund", refund2.status, 201);
    check("full refund amount", refund2.body.amount, 1500);

    // Over-refund
    const overRefund = await request(router, "POST", "/refunds", { charge_id: chargeId }, h);
    check("over-refund 400", overRefund.status, 400);

    // Idempotency
    const idem1 = await request(router, "POST", "/charges", {
      amount: 3000,
      currency: "usd",
      source: "tok_visa",
      idempotency_key: "idem_123",
    }, h);
    const idem2 = await request(router, "POST", "/charges", {
      amount: 3000,
      currency: "usd",
      source: "tok_visa",
      idempotency_key: "idem_123",
    }, h);
    check("idempotent same id", idem1.body.id, idem2.body.id);
  });

  await level("Level 4 — Webhook Handler + Tests", async () => {
    const router = createRouter({ stripeApi, apiKey, logs });

    // Valid webhook
    const evt = stripeApi.makeWebhookEvent("charge.succeeded", { id: "ch_0001", amount: 2000 });
    const rawBody = JSON.stringify({ id: evt.id, type: evt.type, data: evt.data });
    const whRes = await request(router, "POST", "/webhooks/stripe",
      { id: evt.id, type: evt.type, data: evt.data },
      { "stripe-signature": evt.signature });
    // Note: rawBody needs to be available for signature verification
    check("webhook 200", whRes.status, 200);
    check("webhook received", whRes.body.received, true);

    // Duplicate
    const dupRes = await request(router, "POST", "/webhooks/stripe",
      { id: evt.id, type: evt.type, data: evt.data },
      { "stripe-signature": evt.signature });
    check("duplicate skipped", dupRes.status, 200);

    // Bad signature
    const badSigRes = await request(router, "POST", "/webhooks/stripe",
      { id: "evt_bad", type: "charge.succeeded", data: {} },
      { "stripe-signature": "bad_sig" });
    check("bad sig 400", badSigRes.status, 400);

    // Second event
    const evt2 = stripeApi.makeWebhookEvent("charge.refunded", { id: "ch_0001", amount_refunded: 500 });
    await request(router, "POST", "/webhooks/stripe",
      { id: evt2.id, type: evt2.type, data: evt2.data },
      { "stripe-signature": evt2.signature });

    // Unhandled event type
    const evt3 = stripeApi.makeWebhookEvent("customer.created", { id: "cus_001" });
    const unhandled = await request(router, "POST", "/webhooks/stripe",
      { id: evt3.id, type: evt3.type, data: evt3.data },
      { "stripe-signature": evt3.signature });
    check("unhandled event 200", unhandled.status, 200);
  });
}

async function main(): Promise<void> {
  console.log("\nExpress API + Testing\n");
  await runSelfChecks();
  const total = _passed + _failed;
  console.log(`\n${_passed}/${total} passed`);
  if (_failed === 0 && total > 0) console.log("All tests passed.");
}

main();
