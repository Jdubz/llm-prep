/*
  Integration Sim — Merchant Payment Service (server.ts)

  THIS IS THE EXISTING CODEBASE. Read it carefully before writing code.

  It provides:
    - Database class (Map-based, products + orders)
    - PaymentAPI class (simulates an external payment service — returns { status, body }, NOT exceptions)
    - Express app factory with existing routes
    - Existing tests you can read for patterns
    - check() / level() test helpers

  Your implementation goes in starter.ts.
  Run: npx tsx starter.ts
*/

import express, { Request, Response } from "express";
import request from "supertest";

// ─── Types ─────────────────────────────────────────────────────

export type Product = {
  id: string;
  name: string;
  description: string;
  price: number;
  currency: string;
  active: boolean;
};

export type LineItem = {
  product_id: string;
  quantity: number;
  unit_price: number;
};

export type RefundRecord = {
  id: string;
  amount: number;
  reason: string;
  created_at: number;
};

export type Order = {
  id: string;
  customer_id: string;
  line_items: LineItem[];
  total: number;
  currency: string;
  status: "pending" | "payment_processing" | "paid" | "payment_failed" | "refunded" | "partially_refunded";
  payment_intent_id: string | null;
  refunds: RefundRecord[];
  created_at: number;
  updated_at: number;
};

export type PaymentIntent = {
  id: string;
  amount: number;
  currency: string;
  status: string;
  client_secret: string;
  payment_method: string | null;
  capture_method: "automatic" | "manual";
  metadata: Record<string, string>;
  amount_received: number;
  amount_capturable: number;
  created: number;
};

export type Refund = {
  id: string;
  payment_intent: string;
  amount: number;
  status: string;
  reason: string;
  created: number;
};

export type WebhookEvent = {
  id: string;
  type: string;
  data: { object: Record<string, unknown> };
  created: number;
};

// ─── Database ──────────────────────────────────────────────────

export class Database {
  products = new Map<string, Product>();
  orders = new Map<string, Order>();
  private nextOrderId = 1;

  constructor() {
    const seeds = [
      { name: "Basic Widget", description: "A simple widget", price: 1999 },
      { name: "Pro Widget", description: "Professional grade widget", price: 4999 },
      { name: "Widget Deluxe", description: "Top-of-the-line widget", price: 9999 },
      { name: "Widget Bundle", description: "5-pack of basic widgets", price: 7999 },
    ];
    seeds.forEach((s, i) => {
      const id = `prod_${String(i + 1).padStart(4, "0")}`;
      this.products.set(id, { id, ...s, currency: "usd", active: true });
    });
  }

  getProduct(id: string): Product | undefined { return this.products.get(id); }
  listProducts(): Product[] { return [...this.products.values()].filter(p => p.active); }

  createOrder(customerId: string, items: { product_id: string; quantity: number }[]): Order | { error: string } {
    const lineItems: LineItem[] = [];
    let total = 0, currency = "usd";
    for (const item of items) {
      const product = this.products.get(item.product_id);
      if (!product) return { error: `Product not found: ${item.product_id}` };
      if (!product.active) return { error: `Product not active: ${item.product_id}` };
      if (item.quantity < 1) return { error: `Invalid quantity for ${item.product_id}` };
      lineItems.push({ product_id: product.id, quantity: item.quantity, unit_price: product.price });
      total += product.price * item.quantity;
      currency = product.currency;
    }
    if (lineItems.length === 0) return { error: "Order must have at least one line item" };
    const id = `ord_${String(this.nextOrderId++).padStart(4, "0")}`;
    const now = Date.now();
    const order: Order = {
      id, customer_id: customerId, line_items: lineItems, total, currency,
      status: "pending", payment_intent_id: null, refunds: [],
      created_at: now, updated_at: now,
    };
    this.orders.set(id, order);
    return order;
  }

  getOrder(id: string): Order | undefined { return this.orders.get(id); }
  listOrdersByCustomer(cid: string): Order[] { return [...this.orders.values()].filter(o => o.customer_id === cid); }
  updateOrder(id: string, updates: Partial<Order>): Order | undefined {
    const order = this.orders.get(id);
    if (!order) return undefined;
    Object.assign(order, updates, { updated_at: Date.now() });
    return order;
  }
}

// ─── PaymentAPI (simulates external payment service) ───────────
//
// IMPORTANT: All methods return { status, body }.
// They do NOT throw exceptions. Check status before using body.
// This matches how real HTTP APIs behave (fetch does not throw on 4xx/5xx).

export class PaymentAPI {
  private paymentIntents = new Map<string, PaymentIntent>();
  private refunds = new Map<string, Refund>();
  private nextPiId = 1;
  private nextRefundId = 1;
  private idempotencyCache = new Map<string, { status: number; body: any }>();
  readonly webhookSecret = "whsec_test_secret_abc123";

  async createPaymentIntent(params: {
    amount: number;
    currency: string;
    metadata?: Record<string, string>;
    capture_method?: "automatic" | "manual";
    idempotency_key?: string;
  }): Promise<{ status: number; body: any }> {
    if (params.idempotency_key && this.idempotencyCache.has(params.idempotency_key)) {
      return this.idempotencyCache.get(params.idempotency_key)!;
    }
    if (params.amount <= 0) return { status: 400, body: { error: { code: "invalid_amount", message: "Amount must be greater than 0" } } };
    if (params.amount > 99999999) return { status: 400, body: { error: { code: "amount_too_large", message: "Amount exceeds maximum" } } };

    const id = `pi_${String(this.nextPiId++).padStart(6, "0")}`;
    const pi: PaymentIntent = {
      id, amount: params.amount, currency: params.currency.toLowerCase(),
      status: "requires_payment_method",
      client_secret: `${id}_secret_${Math.random().toString(36).slice(2, 14)}`,
      payment_method: null, capture_method: params.capture_method ?? "automatic",
      metadata: params.metadata ?? {}, amount_received: 0, amount_capturable: 0,
      created: Date.now(),
    };
    this.paymentIntents.set(id, pi);
    const result = { status: 201, body: { ...pi } };
    if (params.idempotency_key) this.idempotencyCache.set(params.idempotency_key, result);
    return result;
  }

  async confirmPaymentIntent(id: string, paymentMethod: string): Promise<{ status: number; body: any }> {
    const pi = this.paymentIntents.get(id);
    if (!pi) return { status: 404, body: { error: { code: "not_found", message: `PaymentIntent ${id} not found` } } };
    if (pi.status !== "requires_payment_method" && pi.status !== "requires_confirmation") {
      return { status: 400, body: { error: { code: "invalid_state", message: `Status is ${pi.status}` } } };
    }
    pi.payment_method = paymentMethod;
    if (paymentMethod === "pm_card_declined") {
      pi.status = "canceled";
      return { status: 402, body: { error: { code: "card_declined", message: "Your card was declined." } } };
    }
    if (paymentMethod === "pm_card_3ds_required") {
      pi.status = "requires_action";
      return { status: 200, body: { ...pi } };
    }
    if (pi.capture_method === "manual") {
      pi.status = "requires_capture";
      pi.amount_capturable = pi.amount;
    } else {
      pi.status = "succeeded";
      pi.amount_received = pi.amount;
    }
    return { status: 200, body: { ...pi } };
  }

  async capturePaymentIntent(id: string, amountToCapture?: number): Promise<{ status: number; body: any }> {
    const pi = this.paymentIntents.get(id);
    if (!pi) return { status: 404, body: { error: { code: "not_found", message: `PaymentIntent ${id} not found` } } };
    if (pi.status !== "requires_capture") return { status: 400, body: { error: { code: "invalid_state", message: `Status is ${pi.status}` } } };
    const amt = amountToCapture ?? pi.amount;
    if (amt <= 0 || amt > pi.amount_capturable) return { status: 400, body: { error: { code: "invalid_capture_amount", message: `Cannot capture ${amt}` } } };
    pi.status = "succeeded";
    pi.amount_received = amt;
    pi.amount_capturable = 0;
    return { status: 200, body: { ...pi } };
  }

  async getPaymentIntent(id: string): Promise<{ status: number; body: any }> {
    const pi = this.paymentIntents.get(id);
    if (!pi) return { status: 404, body: { error: { code: "not_found", message: `Not found` } } };
    return { status: 200, body: { ...pi } };
  }

  async createRefund(params: {
    payment_intent: string;
    amount?: number;
    reason?: string;
  }): Promise<{ status: number; body: any }> {
    const pi = this.paymentIntents.get(params.payment_intent);
    if (!pi) return { status: 404, body: { error: { code: "not_found", message: "PaymentIntent not found" } } };
    if (pi.status !== "succeeded") return { status: 400, body: { error: { code: "invalid_state", message: `Cannot refund status ${pi.status}` } } };
    const alreadyRefunded = [...this.refunds.values()]
      .filter(r => r.payment_intent === params.payment_intent && r.status === "succeeded")
      .reduce((sum, r) => sum + r.amount, 0);
    const refundAmount = params.amount ?? (pi.amount_received - alreadyRefunded);
    if (refundAmount <= 0) return { status: 400, body: { error: { code: "invalid_refund_amount", message: "Amount must be positive" } } };
    if (refundAmount > pi.amount_received - alreadyRefunded) {
      return { status: 400, body: { error: { code: "refund_exceeds_payment", message: `Exceeds remaining ${pi.amount_received - alreadyRefunded}` } } };
    }
    const id = `re_${String(this.nextRefundId++).padStart(4, "0")}`;
    const refund: Refund = { id, payment_intent: params.payment_intent, amount: refundAmount, status: "succeeded", reason: params.reason ?? "requested_by_customer", created: Date.now() };
    this.refunds.set(id, refund);
    return { status: 201, body: refund };
  }

  // Webhook helpers — constructWebhookEvent DOES throw on bad signature
  // (matches real Stripe SDK behavior: stripe.webhooks.constructEvent throws)
  constructWebhookEvent(rawBody: string, signature: string): WebhookEvent {
    if (signature !== this.computeSignature(rawBody)) {
      throw new Error("Webhook signature verification failed");
    }
    return JSON.parse(rawBody);
  }

  createTestEvent(type: string, data: Record<string, unknown>): { rawBody: string; signature: string; event: WebhookEvent } {
    const event: WebhookEvent = { id: `evt_${Math.random().toString(36).slice(2, 12)}`, type, data: { object: data }, created: Date.now() };
    const rawBody = JSON.stringify(event);
    return { rawBody, signature: this.computeSignature(rawBody), event };
  }

  private computeSignature(payload: string): string {
    let hash = 0;
    const str = payload + this.webhookSecret;
    for (let i = 0; i < str.length; i++) hash = ((hash << 5) - hash + str.charCodeAt(i)) | 0;
    return "whsig_" + Math.abs(hash).toString(36);
  }
}

// ─── App Factory ───────────────────────────────────────────────

export function createApp(registerRoutes?: (app: express.Express, db: Database, paymentApi: PaymentAPI) => void): {
  app: express.Express;
  db: Database;
  paymentApi: PaymentAPI;
} {
  const app = express();
  const db = new Database();
  const paymentApi = new PaymentAPI();

  // JSON parsing with raw body preservation (for webhook signatures)
  app.use(express.json({
    verify: (req: any, _res, buf) => { req.rawBody = buf.toString(); },
  }));

  // ── Existing routes (products + orders) ──

  app.get("/products", (_req, res) => {
    const products = db.listProducts();
    res.json({ data: products, count: products.length });
  });

  app.get("/products/:id", (req, res) => {
    const product = db.getProduct(req.params.id);
    if (!product) return res.status(404).json({ error: "Product not found" });
    res.json(product);
  });

  app.post("/orders", (req, res) => {
    const { customer_id, items } = req.body;
    if (!customer_id || typeof customer_id !== "string") return res.status(400).json({ error: "customer_id is required" });
    if (!Array.isArray(items) || items.length === 0) return res.status(400).json({ error: "items array is required" });
    const result = db.createOrder(customer_id, items);
    if ("error" in result) return res.status(400).json({ error: result.error });
    res.status(201).json(result);
  });

  app.get("/orders/:id", (req, res) => {
    const order = db.getOrder(req.params.id);
    if (!order) return res.status(404).json({ error: "Order not found" });
    res.json(order);
  });

  app.get("/orders", (req, res) => {
    const cid = req.query.customer_id as string;
    if (!cid) return res.status(400).json({ error: "customer_id query parameter is required" });
    const orders = db.listOrdersByCustomer(cid);
    res.json({ data: orders, count: orders.length });
  });

  // ── Register candidate routes ──
  if (registerRoutes) registerRoutes(app, db, paymentApi);

  return { app, db, paymentApi };
}

// ─── Existing Tests (READ THESE FOR PATTERNS) ──────────────────
//
// These tests demonstrate how to:
//   1. Use supertest to make requests: request(app).get("/path")
//   2. Check status codes and response bodies
//   3. Chain operations (create then retrieve)
//   4. Test error cases (404, 400)
//   5. Call PaymentAPI and check { status, body } responses

export async function runExistingTests(app: express.Express, paymentApi: PaymentAPI): Promise<void> {
  console.log("── Existing Tests (read these for patterns) ──\n");

  await level("Products — list & get", async () => {
    const list = await request(app).get("/products");
    check("GET /products → 200", list.status, 200);
    check("4 seeded products", list.body.count, 4);

    const single = await request(app).get("/products/prod_0001");
    check("GET /products/:id → product", single.body.name, "Basic Widget");
    check("has price in cents", single.body.price, 1999);

    const missing = await request(app).get("/products/prod_9999");
    check("GET missing → 404", missing.status, 404);
  });

  await level("Orders — create, get, validate", async () => {
    const created = await request(app).post("/orders")
      .send({ customer_id: "cus_test", items: [{ product_id: "prod_0001", quantity: 2 }] });
    check("POST /orders → 201", created.status, 201);
    check("order has id", created.body.id.startsWith("ord_"), true);
    check("total = price × qty", created.body.total, 1999 * 2);
    check("status is pending", created.body.status, "pending");

    const fetched = await request(app).get(`/orders/${created.body.id}`);
    check("GET /orders/:id → order", fetched.body.id, created.body.id);

    const bad = await request(app).post("/orders").send({ items: [] });
    check("missing customer_id → 400", bad.status, 400);

    const byCustomer = await request(app).get("/orders?customer_id=cus_test");
    check("GET /orders?customer_id → matches", byCustomer.body.count, 1);
  });

  await level("PaymentAPI — status codes, not exceptions", async () => {
    // SUCCESS: returns { status: 201, body: PaymentIntent }
    const pi = await paymentApi.createPaymentIntent({ amount: 1000, currency: "usd" });
    check("create PI → 201", pi.status, 201);
    check("PI has id", pi.body.id.startsWith("pi_"), true);
    check("PI status", pi.body.status, "requires_payment_method");

    // ERROR: returns { status: 400, body: { error: {...} } } — does NOT throw
    const bad = await paymentApi.createPaymentIntent({ amount: -1, currency: "usd" });
    check("invalid amount → 400", bad.status, 400);
    check("error has code", bad.body.error.code, "invalid_amount");

    // CONFIRM with test card
    const confirmed = await paymentApi.confirmPaymentIntent(pi.body.id, "pm_card_visa");
    check("confirm → 200", confirmed.status, 200);
    check("PI succeeded", confirmed.body.status, "succeeded");

    // DECLINED: returns 402, not an exception
    const pi2 = await paymentApi.createPaymentIntent({ amount: 500, currency: "usd" });
    const declined = await paymentApi.confirmPaymentIntent(pi2.body.id, "pm_card_declined");
    check("declined → 402", declined.status, 402);
    check("declined code", declined.body.error.code, "card_declined");
  });
}

// ─── Test Helpers ──────────────────────────────────────────────

export let _passed = 0;
export let _failed = 0;

export function resetCounters(): void { _passed = 0; _failed = 0; }

export function check(label: string, actual: unknown, expected: unknown): void {
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

export function level(name: string, fn: () => Promise<void>): Promise<void> {
  return new Promise((resolve) => {
    console.log(name);
    fn()
      .then(resolve)
      .catch((e) => {
        const msg = e instanceof Error ? e.message : String(e);
        if (msg.startsWith("TODO")) {
          console.log(`  ○ ${msg}`);
        } else {
          _failed++;
          console.log(`  ✗ ${msg}`);
        }
        resolve();
      });
  });
}
