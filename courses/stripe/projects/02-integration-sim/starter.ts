/*
  Integration Sim — Merchant Payment Service (starter.ts)

  YOUR IMPLEMENTATION FILE.

  Read the README.md spec FIRST, then read server.ts to understand the
  existing codebase. Implement the functions below.

  Run:   npx tsx starter.ts
  Time:  50 minutes total
*/

import {
  Router,
  Database,
  PaymentProvider,
  PaymentError,
  registerExistingRoutes,
  makeRequest,
  check,
  level,
  _passed,
  _failed,
  resetCounters,
} from "./server.js";

import type {
  Order,
  PaymentIntent,
  Refund,
  RefundRecord,
  WebhookEvent,
  SimReq,
  SimRes,
} from "./server.js";

// ─── Part 1: Checkout Flow (15 min) ───────────────────────────
//
// Implement:
//   POST /orders/:id/pay
//     - Look up the order by ID (404 if not found)
//     - Order must be in "pending" status (400 otherwise)
//     - Create a PaymentIntent via paymentProvider.createPaymentIntent()
//       with the order's total, currency, and metadata: { order_id }
//     - If body includes capture_method: "manual", pass it through
//     - If body includes idempotency_key, pass it through
//     - Store the payment_intent_id on the order
//     - Update order status to "payment_processing"
//     - Return 200 + { client_secret, payment_intent_id }
//     - Handle PaymentError → return error.statusCode + { error: error.message }
//
//   POST /orders/:id/confirm
//     - Look up the order by ID (404 if not found)
//     - Order must be in "payment_processing" status (400 otherwise)
//     - Read payment_method from body (required, 400 if missing)
//     - Call paymentProvider.confirmPaymentIntent(payment_intent_id, payment_method)
//     - If PI status is "succeeded": update order status to "paid"
//     - If PI status is "requires_action": keep order in "payment_processing",
//       return 200 + { status: "requires_action", payment_intent }
//     - If PI status is "requires_capture": keep order in "payment_processing",
//       return 200 + { status: "requires_capture", payment_intent }
//     - Handle PaymentError with code "card_declined":
//       update order to "payment_failed", return 402 + { error }
//     - Return 200 + { status: "succeeded", payment_intent } on success

function registerPaymentRoutes(
  router: Router,
  db: Database,
  paymentProvider: PaymentProvider,
): void {
  router.post("/orders/:id/pay", async (req, res) => {
    throw new Error("TODO: implement POST /orders/:id/pay");
  });

  router.post("/orders/:id/confirm", async (req, res) => {
    throw new Error("TODO: implement POST /orders/:id/confirm");
  });
}

// ─── Part 2: Capture & Refunds (15 min) ───────────────────────
//
// Implement:
//   POST /orders/:id/capture
//     - Look up order (404 if not found)
//     - Order must be in "payment_processing" with a payment_intent_id (400 otherwise)
//     - Verify the PI is in "requires_capture" status by calling
//       paymentProvider.getPaymentIntent() (400 if not capturable)
//     - If body includes amount, pass it to capturePaymentIntent()
//     - Call paymentProvider.capturePaymentIntent()
//     - Update order status to "paid"
//     - Return 200 + { payment_intent }
//     - Handle PaymentError appropriately
//
//   POST /orders/:id/refund
//     - Look up order (404 if not found)
//     - Order must be in "paid" or "partially_refunded" status (400 otherwise)
//     - Read optional amount and reason from body
//     - If amount provided, validate: must be positive integer (400 otherwise)
//     - Call paymentProvider.createRefund(payment_intent_id, amount, reason)
//     - Record the refund on the order's refunds array
//     - Calculate total refunded; if equals order total → "refunded",
//       otherwise → "partially_refunded"
//     - Return 200 + { refund, order }
//     - Handle PaymentError (e.g., refund exceeds payment) → return statusCode + { error }

function registerCaptureAndRefundRoutes(
  router: Router,
  db: Database,
  paymentProvider: PaymentProvider,
): void {
  router.post("/orders/:id/capture", async (req, res) => {
    throw new Error("TODO: implement POST /orders/:id/capture");
  });

  router.post("/orders/:id/refund", async (req, res) => {
    throw new Error("TODO: implement POST /orders/:id/refund");
  });
}

// ─── Part 3: Webhook Handler (12 min) ─────────────────────────
//
// Implement:
//   POST /webhooks
//     - Read rawBody from req.rawBody and signature from
//       req.headers["stripe-signature"]
//     - If signature missing, return 400 + { error: "Missing signature" }
//     - Call paymentProvider.constructWebhookEvent(rawBody, signature)
//       to verify and parse the event
//     - If verification fails (PaymentError), return 400 + { error }
//     - Deduplicate: if event.id already processed, return 200 + { received: true }
//     - Handle event types:
//       "payment_intent.succeeded":
//         - Find order by metadata.order_id in event.data.object
//         - Update order status to "paid"
//       "payment_intent.payment_failed":
//         - Find order by metadata.order_id
//         - Update order status to "payment_failed"
//       "charge.refunded":
//         - Log the event (no order update needed — refund route handles it)
//     - Store the event ID as processed
//     - Return 200 + { received: true } immediately
//
// Store processed event IDs in a Set (closure variable).

function registerWebhookRoutes(
  router: Router,
  db: Database,
  paymentProvider: PaymentProvider,
): void {
  // const processedEventIds = new Set<string>();

  router.post("/webhooks", async (req, res) => {
    throw new Error("TODO: implement POST /webhooks");
  });
}

// ─── Part 4: Your Tests (8 min) ──────────────────────────────
//
// Write at least 5 tests covering:
//   1. Happy path: create order → pay → confirm → order is "paid"
//   2. Declined card: pay → confirm with pm_card_declined → "payment_failed"
//   3. Refund: paid order → refund → verify order status
//   4. Webhook: send a valid event → verify 200 + dedup
//   5. Idempotency: pay with same idempotency_key twice → same PI
//
// Use the createTestApp() function below and makeRequest() from server.ts.

async function runCandidateTests(
  createApp: () => { router: Router; db: Database; pp: PaymentProvider },
): Promise<void> {
  throw new Error("TODO: implement Part 4 — Your Tests");

  // Example:
  // const { router, db, pp } = createApp();
  //
  // // Seed an order
  // const orderRes = await makeRequest(router, "POST", "/orders", {
  //   customer_id: "cus_test",
  //   items: [{ product_id: "prod_0001", quantity: 2 }],
  // });
  // const orderId = orderRes.body.id;
  //
  // // Test 1: Happy path
  // const payRes = await makeRequest(router, "POST", `/orders/${orderId}/pay`);
  // check("pay status", payRes.status, 200);
  // ...
}

// ─── App Factory ──────────────────────────────────────────────

function createTestApp(): { router: Router; db: Database; pp: PaymentProvider } {
  const db = new Database();
  const pp = new PaymentProvider();
  const router = new Router();

  registerExistingRoutes(router, db);
  registerPaymentRoutes(router, db, pp);
  registerCaptureAndRefundRoutes(router, db, pp);
  registerWebhookRoutes(router, db, pp);

  return { router, db, pp };
}

// ─── Self-Checks ──────────────────────────────────────────────

async function runSelfChecks(): Promise<void> {
  resetCounters();

  await level("Part 1 — Checkout Flow", async () => {
    const { router, db, pp } = createTestApp();

    // Create an order first
    const orderRes = await makeRequest(router, "POST", "/orders", {
      customer_id: "cus_001",
      items: [{ product_id: "prod_0001", quantity: 2 }],
    });
    check("order created", orderRes.status, 201);
    const orderId = orderRes.body.id;

    // Pay
    const payRes = await makeRequest(router, "POST", `/orders/${orderId}/pay`);
    check("pay status", payRes.status, 200);
    check("pay has client_secret", typeof payRes.body.client_secret, "string");
    check("pay has pi_id", payRes.body.payment_intent_id.startsWith("pi_"), true);

    // Verify order updated
    const orderAfterPay = await makeRequest(router, "GET", `/orders/${orderId}`);
    check("order status payment_processing", orderAfterPay.body.status, "payment_processing");
    check("order has pi_id", orderAfterPay.body.payment_intent_id, payRes.body.payment_intent_id);

    // Confirm with valid card
    const confirmRes = await makeRequest(router, "POST", `/orders/${orderId}/confirm`, {
      payment_method: "pm_card_visa",
    });
    check("confirm status", confirmRes.status, 200);
    check("confirm result", confirmRes.body.status, "succeeded");

    // Verify order is paid
    const orderAfterConfirm = await makeRequest(router, "GET", `/orders/${orderId}`);
    check("order paid", orderAfterConfirm.body.status, "paid");

    // Pay non-existent order
    const noOrder = await makeRequest(router, "POST", "/orders/ord_9999/pay");
    check("pay 404", noOrder.status, 404);

    // Pay already-processing order
    const dupPay = await makeRequest(router, "POST", `/orders/${orderId}/pay`);
    check("pay already paid 400", dupPay.status, 400);

    // Confirm missing payment_method
    // Create fresh order for this test
    const orderRes2 = await makeRequest(router, "POST", "/orders", {
      customer_id: "cus_002",
      items: [{ product_id: "prod_0002", quantity: 1 }],
    });
    await makeRequest(router, "POST", `/orders/${orderRes2.body.id}/pay`);
    const badConfirm = await makeRequest(router, "POST", `/orders/${orderRes2.body.id}/confirm`, {});
    check("confirm missing pm 400", badConfirm.status, 400);
  });

  await level("Part 1b — Declined Card & 3DS", async () => {
    const { router, db, pp } = createTestApp();

    // Declined card
    const orderRes = await makeRequest(router, "POST", "/orders", {
      customer_id: "cus_003",
      items: [{ product_id: "prod_0001", quantity: 1 }],
    });
    const orderId = orderRes.body.id;

    await makeRequest(router, "POST", `/orders/${orderId}/pay`);
    const declinedRes = await makeRequest(router, "POST", `/orders/${orderId}/confirm`, {
      payment_method: "pm_card_declined",
    });
    check("declined 402", declinedRes.status, 402);

    const declinedOrder = await makeRequest(router, "GET", `/orders/${orderId}`);
    check("order payment_failed", declinedOrder.body.status, "payment_failed");

    // 3DS required
    const orderRes2 = await makeRequest(router, "POST", "/orders", {
      customer_id: "cus_004",
      items: [{ product_id: "prod_0002", quantity: 1 }],
    });
    const orderId2 = orderRes2.body.id;

    await makeRequest(router, "POST", `/orders/${orderId2}/pay`);
    const threeDsRes = await makeRequest(router, "POST", `/orders/${orderId2}/confirm`, {
      payment_method: "pm_card_3ds_required",
    });
    check("3ds status", threeDsRes.status, 200);
    check("3ds requires_action", threeDsRes.body.status, "requires_action");

    // Order still payment_processing
    const order3ds = await makeRequest(router, "GET", `/orders/${orderId2}`);
    check("3ds order still processing", order3ds.body.status, "payment_processing");
  });

  await level("Part 1c — Idempotency", async () => {
    const { router, db, pp } = createTestApp();

    const orderRes = await makeRequest(router, "POST", "/orders", {
      customer_id: "cus_005",
      items: [{ product_id: "prod_0001", quantity: 1 }],
    });
    const orderId = orderRes.body.id;

    const payRes1 = await makeRequest(router, "POST", `/orders/${orderId}/pay`, {
      idempotency_key: "idem_abc",
    });
    check("idem pay 1 ok", payRes1.status, 200);

    // Second pay with same key on different order should get same PI
    const orderRes2 = await makeRequest(router, "POST", "/orders", {
      customer_id: "cus_006",
      items: [{ product_id: "prod_0002", quantity: 1 }],
    });
    const payRes2 = await makeRequest(router, "POST", `/orders/${orderRes2.body.id}/pay`, {
      idempotency_key: "idem_abc",
    });
    check("idem pay 2 ok", payRes2.status, 200);
    check("idem same pi_id", payRes1.body.payment_intent_id, payRes2.body.payment_intent_id);
  });

  await level("Part 2 — Manual Capture", async () => {
    const { router, db, pp } = createTestApp();

    const orderRes = await makeRequest(router, "POST", "/orders", {
      customer_id: "cus_010",
      items: [{ product_id: "prod_0003", quantity: 1 }],
    });
    const orderId = orderRes.body.id;

    // Pay with manual capture
    const payRes = await makeRequest(router, "POST", `/orders/${orderId}/pay`, {
      capture_method: "manual",
    });
    check("manual pay ok", payRes.status, 200);

    // Confirm
    const confirmRes = await makeRequest(router, "POST", `/orders/${orderId}/confirm`, {
      payment_method: "pm_card_visa",
    });
    check("manual confirm ok", confirmRes.status, 200);
    check("requires_capture", confirmRes.body.status, "requires_capture");

    // Capture
    const captureRes = await makeRequest(router, "POST", `/orders/${orderId}/capture`);
    check("capture ok", captureRes.status, 200);

    const capturedOrder = await makeRequest(router, "GET", `/orders/${orderId}`);
    check("order paid after capture", capturedOrder.body.status, "paid");

    // Capture non-capturable order
    const dupCapture = await makeRequest(router, "POST", `/orders/${orderId}/capture`);
    check("double capture 400", dupCapture.status, 400);
  });

  await level("Part 2b — Refunds", async () => {
    const { router, db, pp } = createTestApp();

    // Create and pay an order
    const orderRes = await makeRequest(router, "POST", "/orders", {
      customer_id: "cus_020",
      items: [{ product_id: "prod_0001", quantity: 3 }], // 1999 * 3 = 5997
    });
    const orderId = orderRes.body.id;
    const orderTotal = orderRes.body.total;

    await makeRequest(router, "POST", `/orders/${orderId}/pay`);
    await makeRequest(router, "POST", `/orders/${orderId}/confirm`, {
      payment_method: "pm_card_visa",
    });

    // Partial refund
    const refundRes = await makeRequest(router, "POST", `/orders/${orderId}/refund`, {
      amount: 1000,
      reason: "item_damaged",
    });
    check("partial refund ok", refundRes.status, 200);
    check("refund amount", refundRes.body.refund.amount, 1000);
    check("order partially_refunded", refundRes.body.order.status, "partially_refunded");
    check("refund recorded", refundRes.body.order.refunds.length, 1);

    // Second partial refund (rest)
    const refundRes2 = await makeRequest(router, "POST", `/orders/${orderId}/refund`, {
      amount: orderTotal - 1000,
    });
    check("full refund ok", refundRes2.status, 200);
    check("order fully refunded", refundRes2.body.order.status, "refunded");
    check("two refunds recorded", refundRes2.body.order.refunds.length, 2);

    // Over-refund
    const overRefund = await makeRequest(router, "POST", `/orders/${orderId}/refund`, {
      amount: 1,
    });
    check("over-refund 400", overRefund.status, 400);

    // Refund unpaid order
    const pendingOrder = await makeRequest(router, "POST", "/orders", {
      customer_id: "cus_021",
      items: [{ product_id: "prod_0001", quantity: 1 }],
    });
    const badRefund = await makeRequest(router, "POST", `/orders/${pendingOrder.body.id}/refund`);
    check("refund pending order 400", badRefund.status, 400);

    // Refund non-existent order
    const noOrderRefund = await makeRequest(router, "POST", "/orders/ord_9999/refund");
    check("refund 404", noOrderRefund.status, 404);
  });

  await level("Part 3 — Webhook Handler", async () => {
    const { router, db, pp } = createTestApp();

    // Create and pay an order for webhook to reference
    const orderRes = await makeRequest(router, "POST", "/orders", {
      customer_id: "cus_030",
      items: [{ product_id: "prod_0001", quantity: 1 }],
    });
    const orderId = orderRes.body.id;
    await makeRequest(router, "POST", `/orders/${orderId}/pay`);

    // Get the PI ID
    const orderDetail = await makeRequest(router, "GET", `/orders/${orderId}`);
    const piId = orderDetail.body.payment_intent_id;

    // Simulate payment_intent.succeeded webhook
    const { rawBody, signature, event } = pp.createTestEvent("payment_intent.succeeded", {
      id: piId,
      amount: orderRes.body.total,
      metadata: { order_id: orderId },
    });

    // Send webhook with rawBody as the body (special: we pass rawBody directly)
    const whReq = {
      method: "POST",
      path: "/webhooks",
      params: {},
      query: {},
      body: JSON.parse(rawBody),
      headers: { "stripe-signature": signature },
      rawBody,
    };
    const whRes = await router.handle(whReq);
    check("webhook 200", whRes.statusCode, 200);
    check("webhook received", whRes._body.received, true);

    // Check order updated by webhook
    const orderAfterWh = await makeRequest(router, "GET", `/orders/${orderId}`);
    check("order paid via webhook", orderAfterWh.body.status, "paid");

    // Duplicate event
    const whReq2 = {
      method: "POST",
      path: "/webhooks",
      params: {},
      query: {},
      body: JSON.parse(rawBody),
      headers: { "stripe-signature": signature },
      rawBody,
    };
    const whRes2 = await router.handle(whReq2);
    check("duplicate 200", whRes2.statusCode, 200);
    check("duplicate received", whRes2._body.received, true);

    // Bad signature
    const badSigReq = {
      method: "POST",
      path: "/webhooks",
      params: {},
      query: {},
      body: { fake: true },
      headers: { "stripe-signature": "bad_signature" },
      rawBody: JSON.stringify({ fake: true }),
    };
    const badSigRes = await router.handle(badSigReq);
    check("bad sig 400", badSigRes.statusCode, 400);

    // Missing signature
    const noSigReq = {
      method: "POST",
      path: "/webhooks",
      params: {},
      query: {},
      body: {},
      headers: {},
      rawBody: "{}",
    };
    const noSigRes = await router.handle(noSigReq);
    check("no sig 400", noSigRes.statusCode, 400);

    // payment_failed event
    const orderRes2 = await makeRequest(router, "POST", "/orders", {
      customer_id: "cus_031",
      items: [{ product_id: "prod_0002", quantity: 1 }],
    });
    const orderId2 = orderRes2.body.id;
    await makeRequest(router, "POST", `/orders/${orderId2}/pay`);
    const orderDetail2 = await makeRequest(router, "GET", `/orders/${orderId2}`);
    const piId2 = orderDetail2.body.payment_intent_id;

    const failEvent = pp.createTestEvent("payment_intent.payment_failed", {
      id: piId2,
      metadata: { order_id: orderId2 },
    });
    const failReq = {
      method: "POST",
      path: "/webhooks",
      params: {},
      query: {},
      body: JSON.parse(failEvent.rawBody),
      headers: { "stripe-signature": failEvent.signature },
      rawBody: failEvent.rawBody,
    };
    const failRes = await router.handle(failReq);
    check("fail webhook 200", failRes.statusCode, 200);

    const failedOrder = await makeRequest(router, "GET", `/orders/${orderId2}`);
    check("order failed via webhook", failedOrder.body.status, "payment_failed");
  });

  await level("Part 4 — Candidate Tests", async () => {
    await runCandidateTests(createTestApp);
  });
}

// ─── Main ─────────────────────────────────────────────────────

async function main(): Promise<void> {
  console.log("\nIntegration Sim — Merchant Payment Service\n");

  // Verify existing routes work first
  const { router, db } = createTestApp();
  const productsRes = await makeRequest(router, "GET", "/products");
  if (productsRes.status !== 200 || productsRes.body.count !== 4) {
    console.log("ERROR: Existing routes are broken. Do not modify server.ts!");
    return;
  }
  console.log("Existing routes verified (products + orders working)\n");

  await runSelfChecks();

  const total = _passed + _failed;
  console.log(`\n${_passed}/${total} passed`);
  if (_failed === 0 && total > 0) console.log("All tests passed.");
}

main();
