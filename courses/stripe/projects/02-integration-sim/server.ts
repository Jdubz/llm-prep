/*
  Integration Sim — Merchant Payment Service (server.ts)

  This file is the EXISTING CODEBASE. Read it carefully before writing code.
  It provides:
    - Database class (Map-based, products + orders)
    - Router class (same pattern as drill_06)
    - PaymentProvider class (simulates Stripe's API)
    - Existing routes for products and orders
    - Helper function makeRequest() for testing

  Your implementation goes in starter.ts (or solution.ts).

  Run: npx tsx starter.ts
*/

// ─── Types ─────────────────────────────────────────────────────

export type Product = {
  id: string;
  name: string;
  description: string;
  price: number; // in cents
  currency: string;
  active: boolean;
};

export type LineItem = {
  product_id: string;
  quantity: number;
  unit_price: number; // snapshot at time of order
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
  total: number; // in cents
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
  status: "requires_payment_method" | "requires_confirmation" | "requires_action" | "processing" | "requires_capture" | "succeeded" | "canceled";
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
  status: "succeeded" | "pending" | "failed";
  reason: string;
  created: number;
};

export type WebhookEvent = {
  id: string;
  type: string;
  data: { object: Record<string, unknown> };
  created: number;
};

// ─── SimReq / SimRes (same pattern as drill_06) ────────────────

export type Handler = (req: SimReq, res: SimRes, next?: () => void) => void | Promise<void>;
export type Middleware = (req: SimReq, res: SimRes, next: () => void) => void | Promise<void>;

export interface SimReq {
  method: string;
  path: string;
  params: Record<string, string>;
  query: Record<string, string>;
  body: any;
  headers: Record<string, string>;
  rawBody?: string;
}

export interface SimRes {
  statusCode: number;
  _body: any;
  _sent: boolean;
  status(code: number): SimRes;
  json(data: any): void;
  send(data?: any): void;
}

export function createSimRes(): SimRes {
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

// ─── Router ────────────────────────────────────────────────────

export function matchRoute(pattern: string, path: string): Record<string, string> | null {
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

export function parseQuery(path: string): Record<string, string> {
  const idx = path.indexOf("?");
  if (idx === -1) return {};
  const params: Record<string, string> = {};
  for (const pair of path.slice(idx + 1).split("&")) {
    const [k, v] = pair.split("=");
    if (k) params[decodeURIComponent(k)] = decodeURIComponent(v ?? "");
  }
  return params;
}

export class Router {
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

// ─── Database ──────────────────────────────────────────────────

export class Database {
  products = new Map<string, Product>();
  orders = new Map<string, Order>();
  private nextProductId = 1;
  private nextOrderId = 1;

  constructor() {
    // Seed some products
    this.seedProducts();
  }

  private seedProducts(): void {
    const seeds: Array<{ name: string; description: string; price: number }> = [
      { name: "Basic Widget", description: "A simple widget", price: 1999 },
      { name: "Pro Widget", description: "Professional grade widget", price: 4999 },
      { name: "Widget Deluxe", description: "Top-of-the-line widget", price: 9999 },
      { name: "Widget Bundle", description: "5-pack of basic widgets", price: 7999 },
    ];
    for (const seed of seeds) {
      const id = `prod_${String(this.nextProductId++).padStart(4, "0")}`;
      this.products.set(id, {
        id,
        name: seed.name,
        description: seed.description,
        price: seed.price,
        currency: "usd",
        active: true,
      });
    }
  }

  // ── Product methods ──

  listProducts(): Product[] {
    return Array.from(this.products.values()).filter((p) => p.active);
  }

  getProduct(id: string): Product | undefined {
    return this.products.get(id);
  }

  // ── Order methods ──

  createOrder(customerId: string, items: Array<{ product_id: string; quantity: number }>): Order | { error: string } {
    const lineItems: LineItem[] = [];
    let total = 0;
    let currency = "usd";

    for (const item of items) {
      const product = this.products.get(item.product_id);
      if (!product) return { error: `Product not found: ${item.product_id}` };
      if (!product.active) return { error: `Product not active: ${item.product_id}` };
      if (item.quantity < 1) return { error: `Invalid quantity for ${item.product_id}` };

      lineItems.push({
        product_id: product.id,
        quantity: item.quantity,
        unit_price: product.price,
      });
      total += product.price * item.quantity;
      currency = product.currency;
    }

    if (lineItems.length === 0) return { error: "Order must have at least one line item" };

    const id = `ord_${String(this.nextOrderId++).padStart(4, "0")}`;
    const now = Date.now();
    const order: Order = {
      id,
      customer_id: customerId,
      line_items: lineItems,
      total,
      currency,
      status: "pending",
      payment_intent_id: null,
      refunds: [],
      created_at: now,
      updated_at: now,
    };
    this.orders.set(id, order);
    return order;
  }

  getOrder(id: string): Order | undefined {
    return this.orders.get(id);
  }

  listOrdersByCustomer(customerId: string): Order[] {
    return Array.from(this.orders.values()).filter((o) => o.customer_id === customerId);
  }

  updateOrder(id: string, updates: Partial<Order>): Order | undefined {
    const order = this.orders.get(id);
    if (!order) return undefined;
    Object.assign(order, updates, { updated_at: Date.now() });
    return order;
  }
}

// ─── PaymentProvider (simulates Stripe API) ────────────────────

export class PaymentProvider {
  private paymentIntents = new Map<string, PaymentIntent>();
  private refunds = new Map<string, Refund>();
  private nextPiId = 1;
  private nextRefundId = 1;
  private idempotencyCache = new Map<string, PaymentIntent>();
  readonly webhookSecret = "whsec_test_secret_abc123";

  // Special test payment methods:
  //   "pm_card_visa"           → succeeds
  //   "pm_card_declined"       → fails (card_declined)
  //   "pm_card_3ds_required"   → requires_action (3D Secure)
  //   "pm_card_capture_manual" → succeeds with manual capture

  createPaymentIntent(
    amount: number,
    currency: string,
    metadata?: Record<string, string>,
    captureMethod?: "automatic" | "manual",
    idempotencyKey?: string,
  ): PaymentIntent {
    // Idempotency check
    if (idempotencyKey && this.idempotencyCache.has(idempotencyKey)) {
      return this.idempotencyCache.get(idempotencyKey)!;
    }

    if (amount <= 0) throw new PaymentError("invalid_amount", "Amount must be greater than 0", 400);
    if (amount > 99999999) throw new PaymentError("amount_too_large", "Amount exceeds maximum", 400);

    const id = `pi_${String(this.nextPiId++).padStart(6, "0")}`;
    const pi: PaymentIntent = {
      id,
      amount,
      currency: currency.toLowerCase(),
      status: "requires_payment_method",
      client_secret: `${id}_secret_${Math.random().toString(36).slice(2, 14)}`,
      payment_method: null,
      capture_method: captureMethod ?? "automatic",
      metadata: metadata ?? {},
      amount_received: 0,
      amount_capturable: 0,
      created: Date.now(),
    };

    this.paymentIntents.set(id, pi);

    if (idempotencyKey) {
      this.idempotencyCache.set(idempotencyKey, pi);
    }

    return pi;
  }

  confirmPaymentIntent(id: string, paymentMethod: string): PaymentIntent {
    const pi = this.paymentIntents.get(id);
    if (!pi) throw new PaymentError("not_found", `PaymentIntent ${id} not found`, 404);

    if (pi.status !== "requires_payment_method" && pi.status !== "requires_confirmation") {
      throw new PaymentError(
        "invalid_state",
        `PaymentIntent status is ${pi.status}, expected requires_payment_method or requires_confirmation`,
        400,
      );
    }

    pi.payment_method = paymentMethod;

    // Simulate different outcomes based on payment method
    if (paymentMethod === "pm_card_declined") {
      pi.status = "canceled";
      throw new PaymentError("card_declined", "Your card was declined.", 402);
    }

    if (paymentMethod === "pm_card_3ds_required") {
      pi.status = "requires_action";
      return { ...pi };
    }

    // Success path
    if (pi.capture_method === "manual") {
      pi.status = "requires_capture";
      pi.amount_capturable = pi.amount;
    } else {
      pi.status = "succeeded";
      pi.amount_received = pi.amount;
    }

    return { ...pi };
  }

  capturePaymentIntent(id: string, amountToCapture?: number): PaymentIntent {
    const pi = this.paymentIntents.get(id);
    if (!pi) throw new PaymentError("not_found", `PaymentIntent ${id} not found`, 404);

    if (pi.status !== "requires_capture") {
      throw new PaymentError(
        "invalid_state",
        `PaymentIntent status is ${pi.status}, expected requires_capture`,
        400,
      );
    }

    const captureAmount = amountToCapture ?? pi.amount;
    if (captureAmount <= 0 || captureAmount > pi.amount_capturable) {
      throw new PaymentError("invalid_capture_amount", `Cannot capture ${captureAmount}. Capturable: ${pi.amount_capturable}`, 400);
    }

    pi.status = "succeeded";
    pi.amount_received = captureAmount;
    pi.amount_capturable = 0;

    return { ...pi };
  }

  getPaymentIntent(id: string): PaymentIntent {
    const pi = this.paymentIntents.get(id);
    if (!pi) throw new PaymentError("not_found", `PaymentIntent ${id} not found`, 404);
    return { ...pi };
  }

  createRefund(
    paymentIntentId: string,
    amount?: number,
    reason?: string,
  ): Refund {
    const pi = this.paymentIntents.get(paymentIntentId);
    if (!pi) throw new PaymentError("not_found", `PaymentIntent ${paymentIntentId} not found`, 404);

    if (pi.status !== "succeeded") {
      throw new PaymentError("invalid_state", `Cannot refund a PaymentIntent with status ${pi.status}`, 400);
    }

    // Calculate already refunded
    const alreadyRefunded = Array.from(this.refunds.values())
      .filter((r) => r.payment_intent === paymentIntentId && r.status === "succeeded")
      .reduce((sum, r) => sum + r.amount, 0);

    const refundAmount = amount ?? (pi.amount_received - alreadyRefunded);

    if (refundAmount <= 0) {
      throw new PaymentError("invalid_refund_amount", "Refund amount must be positive", 400);
    }

    if (refundAmount > pi.amount_received - alreadyRefunded) {
      throw new PaymentError(
        "refund_exceeds_payment",
        `Refund of ${refundAmount} exceeds remaining ${pi.amount_received - alreadyRefunded}`,
        400,
      );
    }

    const id = `re_${String(this.nextRefundId++).padStart(4, "0")}`;
    const refund: Refund = {
      id,
      payment_intent: paymentIntentId,
      amount: refundAmount,
      status: "succeeded",
      reason: reason ?? "requested_by_customer",
      created: Date.now(),
    };

    this.refunds.set(id, refund);
    return refund;
  }

  constructWebhookEvent(rawBody: string, signature: string): WebhookEvent {
    const expected = this.computeSignature(rawBody);
    if (signature !== expected) {
      throw new PaymentError("signature_verification_failed", "Webhook signature verification failed", 400);
    }
    return JSON.parse(rawBody) as WebhookEvent;
  }

  // Used internally to create test events for the self-check harness
  createTestEvent(type: string, data: Record<string, unknown>): { rawBody: string; signature: string; event: WebhookEvent } {
    const event: WebhookEvent = {
      id: `evt_${Math.random().toString(36).slice(2, 12)}`,
      type,
      data: { object: data },
      created: Date.now(),
    };
    const rawBody = JSON.stringify(event);
    const signature = this.computeSignature(rawBody);
    return { rawBody, signature, event };
  }

  private computeSignature(payload: string): string {
    let hash = 0;
    const str = payload + this.webhookSecret;
    for (let i = 0; i < str.length; i++) {
      hash = ((hash << 5) - hash + str.charCodeAt(i)) | 0;
    }
    return "whsig_" + Math.abs(hash).toString(36);
  }
}

export class PaymentError extends Error {
  constructor(
    public code: string,
    message: string,
    public statusCode: number,
  ) {
    super(message);
    this.name = "PaymentError";
  }
}

// ─── Existing Routes (products + orders) ───────────────────────

export function registerExistingRoutes(router: Router, db: Database): void {
  // GET /products — list all active products
  router.get("/products", (req, res) => {
    const products = db.listProducts();
    res.json({ data: products, count: products.length });
  });

  // GET /products/:id — get a single product
  router.get("/products/:id", (req, res) => {
    const product = db.getProduct(req.params.id);
    if (!product) return res.status(404).json({ error: "Product not found" });
    res.json(product);
  });

  // POST /orders — create a new order
  router.post("/orders", (req, res) => {
    const { customer_id, items } = req.body;
    if (!customer_id || typeof customer_id !== "string") {
      return res.status(400).json({ error: "customer_id is required" });
    }
    if (!Array.isArray(items) || items.length === 0) {
      return res.status(400).json({ error: "items array is required and must not be empty" });
    }

    const result = db.createOrder(customer_id, items);
    if ("error" in result) {
      return res.status(400).json({ error: result.error });
    }

    res.status(201).json(result);
  });

  // GET /orders/:id — get an order
  router.get("/orders/:id", (req, res) => {
    const order = db.getOrder(req.params.id);
    if (!order) return res.status(404).json({ error: "Order not found" });
    res.json(order);
  });

  // GET /orders — list orders (requires customer_id query param)
  router.get("/orders", (req, res) => {
    const customerId = req.query.customer_id;
    if (!customerId) {
      return res.status(400).json({ error: "customer_id query parameter is required" });
    }
    const orders = db.listOrdersByCustomer(customerId);
    res.json({ data: orders, count: orders.length });
  });
}

// ─── Helper: makeRequest ───────────────────────────────────────

export async function makeRequest(
  router: Router,
  method: string,
  path: string,
  body?: any,
  headers?: Record<string, string>,
): Promise<{ status: number; body: any }> {
  const rawBody = body ? JSON.stringify(body) : undefined;
  const req: SimReq = {
    method,
    path: path.split("?")[0],
    params: {},
    query: parseQuery(path),
    body: body ?? {},
    headers: headers ?? {},
    rawBody,
  };
  const res = await router.handle(req);
  return { status: res.statusCode, body: res._body };
}

// ─── Self-Check Helpers (shared with starter/solution) ─────────

export let _passed = 0;
export let _failed = 0;

export function resetCounters(): void {
  _passed = 0;
  _failed = 0;
}

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
