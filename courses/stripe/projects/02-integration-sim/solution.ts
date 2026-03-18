/*
╔══════════════════════════════════════════════════════════════════╗
║                                                                  ║
║   DO NOT OPEN THIS FILE UNTIL YOU HAVE COMPLETED YOUR ATTEMPT.   ║
║                                                                  ║
║   This is the reference solution. Looking at it before finishing  ║
║   your implementation defeats the purpose of the exercise.       ║
║                                                                  ║
║   Set a 50-minute timer. Work in starter.ts. Come back here      ║
║   ONLY to compare after you're done.                             ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝
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

// ─── Part 1: Checkout Flow ────────────────────────────────────

function registerPaymentRoutes(
  router: Router,
  db: Database,
  paymentProvider: PaymentProvider,
): void {
  // POST /orders/:id/pay
  router.post("/orders/:id/pay", async (req, res) => {
    const order = db.getOrder(req.params.id);
    if (!order) return res.status(404).json({ error: "Order not found" });

    if (order.status !== "pending") {
      return res.status(400).json({
        error: `Order status is ${order.status}, expected pending`,
      });
    }

    try {
      const pi = paymentProvider.createPaymentIntent(
        order.total,
        order.currency,
        { order_id: order.id },
        req.body.capture_method,
        req.body.idempotency_key,
      );

      db.updateOrder(order.id, {
        payment_intent_id: pi.id,
        status: "payment_processing",
      });

      res.json({
        client_secret: pi.client_secret,
        payment_intent_id: pi.id,
      });
    } catch (err) {
      if (err instanceof PaymentError) {
        return res.status(err.statusCode).json({ error: err.message });
      }
      res.status(500).json({ error: "Internal server error" });
    }
  });

  // POST /orders/:id/confirm
  router.post("/orders/:id/confirm", async (req, res) => {
    const order = db.getOrder(req.params.id);
    if (!order) return res.status(404).json({ error: "Order not found" });

    if (order.status !== "payment_processing") {
      return res.status(400).json({
        error: `Order status is ${order.status}, expected payment_processing`,
      });
    }

    const paymentMethod = req.body.payment_method;
    if (!paymentMethod || typeof paymentMethod !== "string") {
      return res.status(400).json({ error: "payment_method is required" });
    }

    if (!order.payment_intent_id) {
      return res.status(400).json({ error: "Order has no payment intent" });
    }

    try {
      const pi = paymentProvider.confirmPaymentIntent(
        order.payment_intent_id,
        paymentMethod,
      );

      if (pi.status === "succeeded") {
        db.updateOrder(order.id, { status: "paid" });
        return res.json({ status: "succeeded", payment_intent: pi });
      }

      if (pi.status === "requires_action") {
        return res.json({ status: "requires_action", payment_intent: pi });
      }

      if (pi.status === "requires_capture") {
        return res.json({ status: "requires_capture", payment_intent: pi });
      }

      // Other statuses
      res.json({ status: pi.status, payment_intent: pi });
    } catch (err) {
      if (err instanceof PaymentError && err.code === "card_declined") {
        db.updateOrder(order.id, { status: "payment_failed" });
        return res.status(402).json({ error: err.message });
      }
      if (err instanceof PaymentError) {
        return res.status(err.statusCode).json({ error: err.message });
      }
      res.status(500).json({ error: "Internal server error" });
    }
  });
}

// ─── Part 2: Capture & Refunds ────────────────────────────────

function registerCaptureAndRefundRoutes(
  router: Router,
  db: Database,
  paymentProvider: PaymentProvider,
): void {
  // POST /orders/:id/capture
  router.post("/orders/:id/capture", async (req, res) => {
    const order = db.getOrder(req.params.id);
    if (!order) return res.status(404).json({ error: "Order not found" });

    if (order.status !== "payment_processing" || !order.payment_intent_id) {
      return res.status(400).json({
        error: "Order is not in a capturable state",
      });
    }

    try {
      // Verify PI is capturable
      const currentPi = paymentProvider.getPaymentIntent(order.payment_intent_id);
      if (currentPi.status !== "requires_capture") {
        return res.status(400).json({
          error: `PaymentIntent status is ${currentPi.status}, expected requires_capture`,
        });
      }

      const pi = paymentProvider.capturePaymentIntent(
        order.payment_intent_id,
        req.body.amount,
      );

      db.updateOrder(order.id, { status: "paid" });

      res.json({ payment_intent: pi });
    } catch (err) {
      if (err instanceof PaymentError) {
        return res.status(err.statusCode).json({ error: err.message });
      }
      res.status(500).json({ error: "Internal server error" });
    }
  });

  // POST /orders/:id/refund
  router.post("/orders/:id/refund", async (req, res) => {
    const order = db.getOrder(req.params.id);
    if (!order) return res.status(404).json({ error: "Order not found" });

    if (order.status !== "paid" && order.status !== "partially_refunded") {
      return res.status(400).json({
        error: `Cannot refund order with status ${order.status}`,
      });
    }

    if (!order.payment_intent_id) {
      return res.status(400).json({ error: "Order has no payment intent" });
    }

    const { amount, reason } = req.body;

    if (amount !== undefined) {
      if (typeof amount !== "number" || amount <= 0 || !Number.isInteger(amount)) {
        return res.status(400).json({ error: "Amount must be a positive integer" });
      }
    }

    try {
      const refund = paymentProvider.createRefund(
        order.payment_intent_id,
        amount,
        reason,
      );

      // Record refund on order
      const refundRecord: RefundRecord = {
        id: refund.id,
        amount: refund.amount,
        reason: refund.reason,
        created_at: refund.created,
      };

      const updatedRefunds = [...order.refunds, refundRecord];
      const totalRefunded = updatedRefunds.reduce((sum, r) => sum + r.amount, 0);
      const newStatus = totalRefunded >= order.total ? "refunded" : "partially_refunded";

      const updatedOrder = db.updateOrder(order.id, {
        refunds: updatedRefunds,
        status: newStatus,
      });

      res.json({ refund, order: updatedOrder });
    } catch (err) {
      if (err instanceof PaymentError) {
        return res.status(err.statusCode).json({ error: err.message });
      }
      res.status(500).json({ error: "Internal server error" });
    }
  });
}

// ─── Part 3: Webhook Handler ──────────────────────────────────

function registerWebhookRoutes(
  router: Router,
  db: Database,
  paymentProvider: PaymentProvider,
): void {
  const processedEventIds = new Set<string>();

  router.post("/webhooks", async (req, res) => {
    const signature = req.headers["stripe-signature"];
    if (!signature) {
      return res.status(400).json({ error: "Missing signature" });
    }

    const rawBody = req.rawBody;
    if (!rawBody) {
      return res.status(400).json({ error: "Missing request body" });
    }

    // Verify signature and parse event
    let event: WebhookEvent;
    try {
      event = paymentProvider.constructWebhookEvent(rawBody, signature);
    } catch (err) {
      if (err instanceof PaymentError) {
        return res.status(400).json({ error: err.message });
      }
      return res.status(400).json({ error: "Invalid webhook" });
    }

    // Deduplicate
    if (processedEventIds.has(event.id)) {
      return res.json({ received: true });
    }

    // Process event
    const eventData = event.data.object as Record<string, unknown>;
    const metadata = (eventData.metadata ?? {}) as Record<string, string>;
    const orderId = metadata.order_id;

    switch (event.type) {
      case "payment_intent.succeeded": {
        if (orderId) {
          db.updateOrder(orderId, { status: "paid" });
        }
        break;
      }
      case "payment_intent.payment_failed": {
        if (orderId) {
          db.updateOrder(orderId, { status: "payment_failed" });
        }
        break;
      }
      case "charge.refunded": {
        // Logged but no order update — refund route handles status
        break;
      }
      default:
        // Unknown event type — acknowledge but don't process
        break;
    }

    processedEventIds.add(event.id);
    res.json({ received: true });
  });
}

// ─── Part 4: Candidate Tests ─────────────────────────────────

async function runCandidateTests(
  createApp: () => { router: Router; db: Database; pp: PaymentProvider },
): Promise<void> {
  // Test 1: Happy path — create order, pay, confirm, verify paid
  {
    const { router, db, pp } = createApp();
    const orderRes = await makeRequest(router, "POST", "/orders", {
      customer_id: "cus_test_1",
      items: [{ product_id: "prod_0001", quantity: 2 }],
    });
    const orderId = orderRes.body.id;

    const payRes = await makeRequest(router, "POST", `/orders/${orderId}/pay`);
    check("T1: pay ok", payRes.status, 200);

    const confirmRes = await makeRequest(router, "POST", `/orders/${orderId}/confirm`, {
      payment_method: "pm_card_visa",
    });
    check("T1: confirm ok", confirmRes.status, 200);
    check("T1: status succeeded", confirmRes.body.status, "succeeded");

    const finalOrder = await makeRequest(router, "GET", `/orders/${orderId}`);
    check("T1: order paid", finalOrder.body.status, "paid");
  }

  // Test 2: Declined card
  {
    const { router, db, pp } = createApp();
    const orderRes = await makeRequest(router, "POST", "/orders", {
      customer_id: "cus_test_2",
      items: [{ product_id: "prod_0001", quantity: 1 }],
    });
    const orderId = orderRes.body.id;

    await makeRequest(router, "POST", `/orders/${orderId}/pay`);
    const confirmRes = await makeRequest(router, "POST", `/orders/${orderId}/confirm`, {
      payment_method: "pm_card_declined",
    });
    check("T2: declined 402", confirmRes.status, 402);

    const failedOrder = await makeRequest(router, "GET", `/orders/${orderId}`);
    check("T2: payment_failed", failedOrder.body.status, "payment_failed");
  }

  // Test 3: Refund
  {
    const { router, db, pp } = createApp();
    const orderRes = await makeRequest(router, "POST", "/orders", {
      customer_id: "cus_test_3",
      items: [{ product_id: "prod_0002", quantity: 1 }],
    });
    const orderId = orderRes.body.id;

    await makeRequest(router, "POST", `/orders/${orderId}/pay`);
    await makeRequest(router, "POST", `/orders/${orderId}/confirm`, {
      payment_method: "pm_card_visa",
    });

    const refundRes = await makeRequest(router, "POST", `/orders/${orderId}/refund`, {
      reason: "customer_request",
    });
    check("T3: refund ok", refundRes.status, 200);
    check("T3: order refunded", refundRes.body.order.status, "refunded");
  }

  // Test 4: Webhook delivery and dedup
  {
    const { router, db, pp } = createApp();
    const orderRes = await makeRequest(router, "POST", "/orders", {
      customer_id: "cus_test_4",
      items: [{ product_id: "prod_0001", quantity: 1 }],
    });
    const orderId = orderRes.body.id;
    await makeRequest(router, "POST", `/orders/${orderId}/pay`);
    const orderDetail = await makeRequest(router, "GET", `/orders/${orderId}`);

    const { rawBody, signature } = pp.createTestEvent("payment_intent.succeeded", {
      id: orderDetail.body.payment_intent_id,
      metadata: { order_id: orderId },
    });

    const whReq = {
      method: "POST" as const,
      path: "/webhooks",
      params: {},
      query: {},
      body: JSON.parse(rawBody),
      headers: { "stripe-signature": signature },
      rawBody,
    };
    const whRes = await router.handle(whReq);
    check("T4: webhook 200", whRes.statusCode, 200);

    // Duplicate
    const whRes2 = await router.handle({ ...whReq, params: {}, query: {} });
    check("T4: dedup 200", whRes2.statusCode, 200);
  }

  // Test 5: Idempotency on pay
  {
    const { router, db, pp } = createApp();
    const orderRes = await makeRequest(router, "POST", "/orders", {
      customer_id: "cus_test_5",
      items: [{ product_id: "prod_0001", quantity: 1 }],
    });
    const orderId = orderRes.body.id;

    const pay1 = await makeRequest(router, "POST", `/orders/${orderId}/pay`, {
      idempotency_key: "idem_test_5",
    });

    const orderRes2 = await makeRequest(router, "POST", "/orders", {
      customer_id: "cus_test_5b",
      items: [{ product_id: "prod_0002", quantity: 1 }],
    });
    const pay2 = await makeRequest(router, "POST", `/orders/${orderRes2.body.id}/pay`, {
      idempotency_key: "idem_test_5",
    });

    check("T5: idem same PI", pay1.body.payment_intent_id, pay2.body.payment_intent_id);
  }
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

// ─── Self-Checks (same as starter.ts) ─────────────────────────

async function runSelfChecks(): Promise<void> {
  resetCounters();

  await level("Part 1 — Checkout Flow", async () => {
    const { router, db, pp } = createTestApp();

    const orderRes = await makeRequest(router, "POST", "/orders", {
      customer_id: "cus_001",
      items: [{ product_id: "prod_0001", quantity: 2 }],
    });
    check("order created", orderRes.status, 201);
    const orderId = orderRes.body.id;

    const payRes = await makeRequest(router, "POST", `/orders/${orderId}/pay`);
    check("pay status", payRes.status, 200);
    check("pay has client_secret", typeof payRes.body.client_secret, "string");
    check("pay has pi_id", payRes.body.payment_intent_id.startsWith("pi_"), true);

    const orderAfterPay = await makeRequest(router, "GET", `/orders/${orderId}`);
    check("order status payment_processing", orderAfterPay.body.status, "payment_processing");
    check("order has pi_id", orderAfterPay.body.payment_intent_id, payRes.body.payment_intent_id);

    const confirmRes = await makeRequest(router, "POST", `/orders/${orderId}/confirm`, {
      payment_method: "pm_card_visa",
    });
    check("confirm status", confirmRes.status, 200);
    check("confirm result", confirmRes.body.status, "succeeded");

    const orderAfterConfirm = await makeRequest(router, "GET", `/orders/${orderId}`);
    check("order paid", orderAfterConfirm.body.status, "paid");

    const noOrder = await makeRequest(router, "POST", "/orders/ord_9999/pay");
    check("pay 404", noOrder.status, 404);

    const dupPay = await makeRequest(router, "POST", `/orders/${orderId}/pay`);
    check("pay already paid 400", dupPay.status, 400);

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

    const payRes = await makeRequest(router, "POST", `/orders/${orderId}/pay`, {
      capture_method: "manual",
    });
    check("manual pay ok", payRes.status, 200);

    const confirmRes = await makeRequest(router, "POST", `/orders/${orderId}/confirm`, {
      payment_method: "pm_card_visa",
    });
    check("manual confirm ok", confirmRes.status, 200);
    check("requires_capture", confirmRes.body.status, "requires_capture");

    const captureRes = await makeRequest(router, "POST", `/orders/${orderId}/capture`);
    check("capture ok", captureRes.status, 200);

    const capturedOrder = await makeRequest(router, "GET", `/orders/${orderId}`);
    check("order paid after capture", capturedOrder.body.status, "paid");

    const dupCapture = await makeRequest(router, "POST", `/orders/${orderId}/capture`);
    check("double capture 400", dupCapture.status, 400);
  });

  await level("Part 2b — Refunds", async () => {
    const { router, db, pp } = createTestApp();

    const orderRes = await makeRequest(router, "POST", "/orders", {
      customer_id: "cus_020",
      items: [{ product_id: "prod_0001", quantity: 3 }],
    });
    const orderId = orderRes.body.id;
    const orderTotal = orderRes.body.total;

    await makeRequest(router, "POST", `/orders/${orderId}/pay`);
    await makeRequest(router, "POST", `/orders/${orderId}/confirm`, {
      payment_method: "pm_card_visa",
    });

    const refundRes = await makeRequest(router, "POST", `/orders/${orderId}/refund`, {
      amount: 1000,
      reason: "item_damaged",
    });
    check("partial refund ok", refundRes.status, 200);
    check("refund amount", refundRes.body.refund.amount, 1000);
    check("order partially_refunded", refundRes.body.order.status, "partially_refunded");
    check("refund recorded", refundRes.body.order.refunds.length, 1);

    const refundRes2 = await makeRequest(router, "POST", `/orders/${orderId}/refund`, {
      amount: orderTotal - 1000,
    });
    check("full refund ok", refundRes2.status, 200);
    check("order fully refunded", refundRes2.body.order.status, "refunded");
    check("two refunds recorded", refundRes2.body.order.refunds.length, 2);

    const overRefund = await makeRequest(router, "POST", `/orders/${orderId}/refund`, {
      amount: 1,
    });
    check("over-refund 400", overRefund.status, 400);

    const pendingOrder = await makeRequest(router, "POST", "/orders", {
      customer_id: "cus_021",
      items: [{ product_id: "prod_0001", quantity: 1 }],
    });
    const badRefund = await makeRequest(router, "POST", `/orders/${pendingOrder.body.id}/refund`);
    check("refund pending order 400", badRefund.status, 400);

    const noOrderRefund = await makeRequest(router, "POST", "/orders/ord_9999/refund");
    check("refund 404", noOrderRefund.status, 404);
  });

  await level("Part 3 — Webhook Handler", async () => {
    const { router, db, pp } = createTestApp();

    const orderRes = await makeRequest(router, "POST", "/orders", {
      customer_id: "cus_030",
      items: [{ product_id: "prod_0001", quantity: 1 }],
    });
    const orderId = orderRes.body.id;
    await makeRequest(router, "POST", `/orders/${orderId}/pay`);

    const orderDetail = await makeRequest(router, "GET", `/orders/${orderId}`);
    const piId = orderDetail.body.payment_intent_id;

    const { rawBody, signature, event } = pp.createTestEvent("payment_intent.succeeded", {
      id: piId,
      amount: orderRes.body.total,
      metadata: { order_id: orderId },
    });

    const whReq = {
      method: "POST" as const,
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

    const orderAfterWh = await makeRequest(router, "GET", `/orders/${orderId}`);
    check("order paid via webhook", orderAfterWh.body.status, "paid");

    const whRes2 = await router.handle({ ...whReq, params: {}, query: {} });
    check("duplicate 200", whRes2.statusCode, 200);
    check("duplicate received", whRes2._body.received, true);

    const badSigReq = {
      method: "POST" as const,
      path: "/webhooks",
      params: {},
      query: {},
      body: { fake: true },
      headers: { "stripe-signature": "bad_signature" },
      rawBody: JSON.stringify({ fake: true }),
    };
    const badSigRes = await router.handle(badSigReq);
    check("bad sig 400", badSigRes.statusCode, 400);

    const noSigReq = {
      method: "POST" as const,
      path: "/webhooks",
      params: {},
      query: {},
      body: {},
      headers: {},
      rawBody: "{}",
    };
    const noSigRes = await router.handle(noSigReq);
    check("no sig 400", noSigRes.statusCode, 400);

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
      method: "POST" as const,
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
  console.log("\nIntegration Sim — Merchant Payment Service (SOLUTION)\n");

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
