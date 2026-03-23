/*
Drill 06 — Express API (Integration Exercise Prep)

Build an Express API server with routes, middleware, and external
API integration. This simulates the Stripe Integration Exercise:
you're given a server skeleton + an external API to call, and
you build the routes.

Setup (one-time):
  cd drills && npm install express supertest @types/express @types/supertest

Run:
  npx tsx drill_06_express_api.ts

Target time: 35 minutes for all 3 parts.

────────────────────────────────────
Part 1 — Routes & Auth Middleware (10 min)

  Build createApp() returning an Express app. It receives a config
  with stripeApi, apiKey, and a logs array.

  Routes:
    GET  /health          → 200 + { status: "ok" } (NO auth required)

    POST /users           → 201 + { id, name, email, created_at }
                            400 if name or email missing

    GET  /users/:id       → 200 + user, or 404 + { error: "Not found" }

    GET  /users           → 200 + { data: User[], count: number }
                            Supports ?email= filter (case-insensitive)

  Auth middleware (all routes EXCEPT /health):
    Read "x-api-key" header. If missing or wrong, return
    401 + { error: "Unauthorized" }.

────────────────────────────────────
Part 2 — External API Integration (15 min)

  Add routes that call the provided FakeStripeAPI:

  POST /charges
    Body: { amount, currency, source, description?, idempotency_key? }
    - Validate: amount (> 0, integer), currency (3 lowercase letters),
      source (required)
    - Call stripeApi.createCharge()
    - Pass idempotency_key if provided
    - Return 201 + charge on success
    - Return 402 + { error } if declined
    - Return 400 for validation failures

  GET /charges/:id
    - Call stripeApi.getCharge(id)
    - Return 200 + charge, or 404

  POST /refunds
    Body: { charge_id, amount? }
    - Call stripeApi.createRefund()
    - Return 201 + refund on success
    - Return 400 if charge not found or already refunded

────────────────────────────────────
Part 3 — Webhook Handler (10 min)

  POST /webhooks/stripe
    - Use express.raw() for this route (need raw body for signature)
    - Verify signature: stripeApi.verifyWebhookSignature(rawBody, sig)
    - Return 400 if invalid signature
    - Deduplicate by event id
    - Store events with type "charge.succeeded", "charge.refunded",
      or "charge.failed". Ignore other types.
    - Return 200 + { received: true }

  createApp() should return { app, getProcessedWebhooks }
  where getProcessedWebhooks() returns stored event objects in order.
*/

import express, { Request, Response, NextFunction } from "express";
import { error } from "node:console";
import request from "supertest";

// ─── Fake Stripe API (simulates external service — do not edit) ─

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
    if (data.idempotency_key && this.idempotencyCache.has(data.idempotency_key)) {
      return { status: 200, body: this.idempotencyCache.get(data.idempotency_key)! };
    }
    if (data.source === "tok_declined") {
      return { status: 402, body: { error: "Card declined" } };
    }
    const charge: Charge = {
      id: `ch_${String(this.nextChargeId++).padStart(4, "0")}`,
      amount: data.amount, currency: data.currency, source: data.source,
      status: "succeeded", description: data.description ?? "",
      amount_refunded: 0, created: Date.now(),
    };
    this.charges.set(charge.id, charge);
    if (data.idempotency_key) this.idempotencyCache.set(data.idempotency_key, charge);
    return { status: 201, body: charge };
  }

  async getCharge(id: string): Promise<{ status: number; body: Charge | { error: string } }> {
    const charge = this.charges.get(id);
    return charge
      ? { status: 200, body: charge }
      : { status: 404, body: { error: "Charge not found" } };
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
      charge: charge.id, amount: refundAmount,
      status: "succeeded", created: Date.now(),
    };
    this.refunds.set(refund.id, refund);
    return { status: 201, body: refund };
  }

  makeWebhookEvent(type: string, data: Record<string, unknown>): WebhookEvent {
    const id = `evt_${Math.random().toString(36).slice(2, 10)}`;
    const payload = JSON.stringify({ id, type, data: { object: data } });
    return { id, type, data: { object: data }, signature: this.computeSignature(payload) };
  }

  verifyWebhookSignature(rawBody: string, signature: string): boolean {
    return signature === this.computeSignature(rawBody);
  }

  private computeSignature(payload: string): string {
    let hash = 0;
    const str = payload + this.webhookSecret;
    for (let i = 0; i < str.length; i++) hash = ((hash << 5) - hash + str.charCodeAt(i)) | 0;
    return "sig_" + Math.abs(hash).toString(36);
  }
}

// ─── Types ──────────────────────────────────────────────────────

type User = { id: string; name: string; email: string; created_at: number };

type AppConfig = {
  stripeApi: FakeStripeAPI;
  apiKey: string;
};

// ─── Your Implementation ────────────────────────────────────────

export function createApp(config: AppConfig): {
  app: express.Express;
  getProcessedWebhooks: () => WebhookEvent[];
} {
  const app = express();
  const users = new Map<string, User>();
  let nextId = 1;
  const processedWebhooks: WebhookEvent[] = [];
  const seenEventIds = new Set<string>();
  const { stripeApi, apiKey } = config;
  
  app.post('/webhooks/stripe', express.raw({ type: 'application/json' }), async (req, res) => {
    const { body, headers } = req;
    const verified = stripeApi.verifyWebhookSignature(body, headers['stripe-signature'] as string);
    if (!verified) return res.status(400).send({ error: 'invalid signature' });
    const event = JSON.parse(body);
    if (seenEventIds.has(event.id)) return res.send({ received: true });
    seenEventIds.add(event.id);
    if (["charge.succeeded", "charge.refunded", "charge.failed"].includes(event.type)) {
      processedWebhooks.push(event);
    }
    return res.send({ received: true });
  });
  // REVIEW: Good — placing this BEFORE express.json() is correct.
  // The raw body is needed for signature verification and you clearly
  // understood the ordering issue.
  //
  // One bug: line 212 passes `body` (a Buffer) directly to
  // verifyWebhookSignature, which expects a string. This works in the
  // tests because supertest sends a string body, but with a real HTTP
  // client the Buffer wouldn't match. Call `body.toString()` to be safe.
  //
  // Line 214: `JSON.parse(body)` — same thing, works here but
  // `JSON.parse(body.toString())` is more defensive.
  //
  // Good: seenEventIds is a Set (O(1) dedup). Good: the type filter
  // on line 217 is clean. Good: unrecognized events still get 200.
  //
  // Minor: the "received: true" response is sent even for duplicates
  // (line 215) — that matches the spec. Correct.

  app.use(express.json());
  
  app.get('/health', (req, res) => {
    return res.send({ status: 'ok' });
  });
  // REVIEW: Clean one-liner.

  app.use((req, res, next) => {
    const reqKey = req.headers['x-api-key'];
    if (reqKey !== apiKey) return res.status(401).send({ error: "Unauthorized" });
    next();
  });
  // REVIEW: Correct. Good that /health is registered ABOVE this
  // middleware so it bypasses auth. This is the cleanest approach —
  // no conditional check inside the middleware needed.

  app.post('/users', (req, res) => {
    const { name, email } = req.body;
    if (!name || !email) return res.status(400).send({ error: 'missing required parameters' });
    const newUser: User = {
      id: crypto.randomUUID(),
      name,
      email,
      created_at: Date.now(),
    }
    users.set(newUser.id, newUser);
    return res.status(201).send(newUser);
  });
  // REVIEW: Clean. Good use of crypto.randomUUID(), destructuring,
  // and early return for validation.

  app.get('/users/:id', (req, res) => {
    const user = users.get(req.params.id);
    if (!user) return res.status(404).send({ error: 'user not found' });
    return res.send(user)
  });
  // REVIEW: Clean.

  app.get('/users', (req, res) => {
    const allUsers = Array.from(users.values());
    const response = { data: allUsers, count: users.size }
    if (req.query.email) {
      const filtered = allUsers.filter((u) => u.email === req.query.email);
      response.data = filtered;
      response.count = filtered.length;
    }
    return res.send(response);
  });
  // REVIEW: Works but the email filter is case-sensitive (line 258).
  // The spec says "case-insensitive." Fix:
  //   u.email.toLowerCase() === (req.query.email as string).toLowerCase()
  //
  // Also: when there's no filter, response.count uses users.size
  // which is correct. But if you later add delete functionality,
  // users.size and allUsers.length could diverge if you're not
  // careful. Using allUsers.length is safer.

  app.post('/charges', async (req, res) => {
    const { amount, currency, source, description, idempotency_key } = req.body;
    if (!source) return res.status(400).send({ error: 'missing source' });
    if (!Number.isInteger(amount) || amount <= 0) return res.status(400).send({ error: 'improper amount format' });
    if (currency.length !== 3 || currency !== currency.toLowerCase()) return res.status(400).send({ error: 'improper currency' });

    const charge = await stripeApi.createCharge(req.body);
    return res.status(charge.status).send(charge.body);
  });
  // REVIEW: Solid. The validation guards are good — checking integer,
  // positive, 3-char lowercase currency. The status passthrough on
  // line 272 (res.status(charge.status)) is elegant — you let the
  // FakeStripeAPI dictate the status code instead of mapping it
  // yourself. This handles 201 (success) and 402 (declined) cleanly.
  //
  // One edge case: if `currency` is undefined/null, line 269
  // `currency.length` will throw. Check for its existence before
  // accessing .length, or validate all required fields together:
  //   if (!amount || !currency || !source) return res.status(400)...
  //
  // Minor: you destructure idempotency_key on line 266 but never
  // use it — you pass req.body directly to createCharge (line 271).
  // This works because createCharge reads idempotency_key from the
  // object, but the unused destructured variable is noise. Either
  // use it explicitly or don't destructure it.

  app.get('/charges/:id', async (req, res) => {
    const { id } = req.params;
    const charge = await stripeApi.getCharge(id);
    return res.status(charge.status).send(charge.body);
  });
  // REVIEW: Clean. Same status passthrough pattern. Good.

  app.post('/refunds', async (req, res) => {
    const { charge_id, amount } = req.body;
    const refund = await stripeApi.createRefund({ charge_id, amount });

    return res.status(refund.status).send(refund.body);
  });
  // REVIEW: Clean. Same passthrough pattern — consistent with charges.
  //
  // Overall architecture note: the status passthrough pattern
  // (res.status(apiResult.status).send(apiResult.body)) that you use
  // for charges, get-charge, and refunds is a great instinct. You
  // wrote it once and applied it consistently. In a real codebase
  // you'd extract it into a helper:
  //   const forward = (res, result) => res.status(result.status).send(result.body);
  // But for a 35-minute interview, the repetition is fine.

  return { app, getProcessedWebhooks: () => processedWebhooks };
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
  const stripeApi = new FakeStripeAPI();
  const apiKey = "sk_test_abc123";

  await part("Part 1 — Routes & Auth Middleware", async () => {
    const { app } = createApp({ stripeApi, apiKey });
    const h = { "x-api-key": apiKey };

    // Health — no auth
    const health = await request(app).get("/health");
    check("health status", health.status, 200);
    check("health body", health.body.status, "ok");

    // Auth — missing key
    const noAuth = await request(app).get("/users");
    check("no auth 401", noAuth.status, 401);

    // Auth — wrong key
    const badAuth = await request(app).get("/users").set("x-api-key", "wrong");
    check("bad auth 401", badAuth.status, 401);

    // Create user
    const created = await request(app).post("/users").set(h).send({ name: "Alice", email: "alice@test.com" });
    check("create status", created.status, 201);
    check("create name", created.body.name, "Alice");
    check("create email", created.body.email, "alice@test.com");
    check("create has id", typeof created.body.id, "string");

    const userId = created.body.id;

    // Get user
    const fetched = await request(app).get(`/users/${userId}`).set(h);
    check("get status", fetched.status, 200);
    check("get name", fetched.body.name, "Alice");

    // Get missing
    const missing = await request(app).get("/users/nope").set(h);
    check("get 404", missing.status, 404);

    // List
    await request(app).post("/users").set(h).send({ name: "Bob", email: "bob@test.com" });
    const listed = await request(app).get("/users").set(h);
    check("list count", listed.body.count, 2);

    // Filter by email
    const filtered = await request(app).get("/users?email=alice@test.com").set(h);
    check("filter count", filtered.body.count, 1);
    check("filter name", filtered.body.data[0].name, "Alice");

    // Validation
    const badCreate = await request(app).post("/users").set(h).send({ name: "Alice" });
    check("missing email 400", badCreate.status, 400);
  });

  await part("Part 2 — External API Integration", async () => {
    const { app } = createApp({ stripeApi, apiKey });
    const h = { "x-api-key": apiKey };

    // Create charge
    const charge = await request(app).post("/charges").set(h)
      .send({ amount: 2000, currency: "usd", source: "tok_visa", description: "Test" });
    check("charge status", charge.status, 201);
    check("charge amount", charge.body.amount, 2000);
    check("charge id", charge.body.id.startsWith("ch_"), true);

    const chargeId = charge.body.id;

    // Get charge
    const fetched = await request(app).get(`/charges/${chargeId}`).set(h);
    check("get charge", fetched.status, 200);
    check("get charge amount", fetched.body.amount, 2000);

    // Missing charge
    const missing = await request(app).get("/charges/ch_9999").set(h);
    check("missing charge 404", missing.status, 404);

    // Declined card
    const declined = await request(app).post("/charges").set(h)
      .send({ amount: 1000, currency: "usd", source: "tok_declined" });
    check("declined 402", declined.status, 402);

    // Validation — missing fields
    const noSource = await request(app).post("/charges").set(h).send({ amount: 1000 });
    check("missing fields 400", noSource.status, 400);

    // Validation — bad amount
    const badAmt = await request(app).post("/charges").set(h)
      .send({ amount: -5, currency: "usd", source: "tok_visa" });
    check("negative amount 400", badAmt.status, 400);

    // Refund
    const refund = await request(app).post("/refunds").set(h)
      .send({ charge_id: chargeId, amount: 500 });
    check("refund status", refund.status, 201);
    check("refund amount", refund.body.amount, 500);

    // Full refund of remainder
    const refund2 = await request(app).post("/refunds").set(h)
      .send({ charge_id: chargeId });
    check("full refund", refund2.status, 201);
    check("full refund amount", refund2.body.amount, 1500);

    // Over-refund
    const overRefund = await request(app).post("/refunds").set(h)
      .send({ charge_id: chargeId });
    check("over-refund 400", overRefund.status, 400);

    // Idempotency
    const idem1 = await request(app).post("/charges").set(h)
      .send({ amount: 3000, currency: "usd", source: "tok_visa", idempotency_key: "idem_1" });
    const idem2 = await request(app).post("/charges").set(h)
      .send({ amount: 3000, currency: "usd", source: "tok_visa", idempotency_key: "idem_1" });
    check("idempotent same id", idem1.body.id, idem2.body.id);
  });

  await part("Part 3 — Webhook Handler", async () => {
    const localApi = new FakeStripeAPI();
    const { app, getProcessedWebhooks } = createApp({ stripeApi: localApi, apiKey });

    // Valid webhook
    const evt = localApi.makeWebhookEvent("charge.succeeded", { id: "ch_0001", amount: 2000 });
    const payload = JSON.stringify({ id: evt.id, type: evt.type, data: evt.data });
    const whRes = await request(app).post("/webhooks/stripe")
      .set("content-type", "application/json")
      .set("stripe-signature", evt.signature)
      .send(payload);
    check("webhook 200", whRes.status, 200);
    check("webhook received", whRes.body.received, true);

    // Duplicate
    const dupRes = await request(app).post("/webhooks/stripe")
      .set("content-type", "application/json")
      .set("stripe-signature", evt.signature)
      .send(payload);
    check("duplicate 200", dupRes.status, 200);
    check("not stored twice", getProcessedWebhooks().length, 1);

    // Bad signature
    const badSigRes = await request(app).post("/webhooks/stripe")
      .set("content-type", "application/json")
      .set("stripe-signature", "bad_sig")
      .send(JSON.stringify({ id: "evt_bad", type: "charge.succeeded", data: {} }));
    check("bad sig 400", badSigRes.status, 400);

    // Second valid event
    const evt2 = localApi.makeWebhookEvent("charge.refunded", { id: "ch_0001" });
    const payload2 = JSON.stringify({ id: evt2.id, type: evt2.type, data: evt2.data });
    await request(app).post("/webhooks/stripe")
      .set("content-type", "application/json")
      .set("stripe-signature", evt2.signature)
      .send(payload2);
    check("two events stored", getProcessedWebhooks().length, 2);

    // Unrecognized event type — acknowledged but not stored
    const evt3 = localApi.makeWebhookEvent("customer.created", { id: "cus_001" });
    const payload3 = JSON.stringify({ id: evt3.id, type: evt3.type, data: evt3.data });
    const unkRes = await request(app).post("/webhooks/stripe")
      .set("content-type", "application/json")
      .set("stripe-signature", evt3.signature)
      .send(payload3);
    check("unrecognized 200", unkRes.status, 200);
    check("not stored", getProcessedWebhooks().length, 2);
  });
}

async function main(): Promise<void> {
  console.log("\nExpress API (Integration Exercise Prep)\n");
  await runSelfChecks();
  const total = _passed + _failed;
  console.log(`\n${_passed}/${total} passed`);
  if (_failed === 0 && total > 0) console.log("All tests passed.");
}

main();
