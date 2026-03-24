/*
  Integration Sim — Merchant Payment Service (starter.ts)

  YOUR IMPLEMENTATION FILE.

  1. Read the README.md spec
  2. Read server.ts — understand the existing code and test patterns
  3. Implement the routes below
  4. Write your own tests

  Run:   npx tsx starter.ts
  Time:  50 minutes total
*/

import express from "express";
import request from "supertest";
import {
  createApp,
  PaymentAPI,
  Database,
  runExistingTests,
  check,
  level,
  _passed,
  _failed,
  resetCounters,
} from "./server.js";

import type { Order, WebhookEvent } from "./server.js";

// ─── Your Routes ────────────────────────────────────────────────
//
// This function receives the Express app, database, and PaymentAPI.
// Add your routes here. The existing product + order routes are
// already registered by createApp().
//
// IMPORTANT: PaymentAPI returns { status, body } — it does NOT throw.
// Always check response.status before using response.body.
// Read the existing PaymentAPI tests in server.ts to see the pattern.

function registerRoutes(
  app: express.Express,
  db: Database,
  paymentApi: PaymentAPI,
): void {

  // ── Part 1: Checkout Flow (15 min) ───────────────────────────
  //
  //   POST /orders/:id/pay
  //     - Look up order (404 if not found), must be "pending" (400)
  //     - Call paymentApi.createPaymentIntent({ amount, currency, metadata: { order_id }, capture_method?, idempotency_key? })
  //     - Check response status — if not 201, forward the error
  //     - Store payment_intent_id on order, set status "payment_processing"
  //     - Return 200 + { client_secret, payment_intent_id }
  //
  //   POST /orders/:id/confirm
  //     - Look up order (404), must be "payment_processing" (400)
  //     - payment_method required in body (400 if missing)
  //     - Call paymentApi.confirmPaymentIntent(payment_intent_id, payment_method)
  //     - Check response status:
  //       200 + status "succeeded"        → order "paid"
  //       200 + status "requires_action"  → keep "payment_processing"
  //       200 + status "requires_capture" → keep "payment_processing"
  //       402 (card_declined)             → order "payment_failed"
  //     - Return { status, payment_intent }

  // TODO: implement POST /orders/:id/pay
  // TODO: implement POST /orders/:id/confirm

  // ── Part 2: Capture & Refunds (15 min) ───────────────────────
  //
  //   POST /orders/:id/capture
  //     - Look up order (404), must be "payment_processing" with payment_intent_id (400)
  //     - Call paymentApi.getPaymentIntent() to verify "requires_capture" (400 if not)
  //     - Call paymentApi.capturePaymentIntent(), pass optional amount from body
  //     - Order → "paid", return { payment_intent }
  //
  //   POST /orders/:id/refund
  //     - Look up order (404), must be "paid" or "partially_refunded" (400)
  //     - Optional amount (positive integer) and reason from body
  //     - Call paymentApi.createRefund({ payment_intent, amount, reason })
  //     - Record on order.refunds array
  //     - If total refunded >= order.total → "refunded", else "partially_refunded"
  //     - Return { refund, order }

  // TODO: implement POST /orders/:id/capture
  // TODO: implement POST /orders/:id/refund

  // ── Part 3: Webhook Handler (12 min) ─────────────────────────
  //
  //   POST /webhooks
  //     - Read req.rawBody and req.headers["stripe-signature"]
  //     - Missing signature → 400
  //     - Call paymentApi.constructWebhookEvent(rawBody, signature)
  //       (this one DOES throw on bad signature — catch it, return 400)
  //     - Deduplicate by event.id (return 200 if already processed)
  //     - "payment_intent.succeeded" → find order via metadata.order_id, set "paid"
  //     - "payment_intent.payment_failed" → find order, set "payment_failed"
  //     - "charge.refunded" → acknowledge, no order update
  //     - Return 200 + { received: true }

  // TODO: implement POST /webhooks
}

// ─── Part 4: Your Tests (8 min) ────────────────────────────────
//
// Write at least 5 tests. Follow the patterns from the existing
// tests in server.ts (supertest + check).
//
// Required tests:
//   1. Happy path: create order → pay → confirm → order is "paid"
//   2. Declined card: confirm with pm_card_declined → "payment_failed"
//   3. Refund: paid order → refund → verify status
//   4. Webhook: valid event → 200, duplicate → 200, bad sig → 400
//   5. Idempotency: pay with same key twice → same PI returned

async function runCandidateTests(app: express.Express, paymentApi: PaymentAPI): Promise<void> {
  throw new Error("TODO: implement your tests");

  // Example (follow the pattern from existing tests):
  //
  // const order = await request(app).post("/orders")
  //   .send({ customer_id: "cus_test", items: [{ product_id: "prod_0001", quantity: 1 }] });
  // const orderId = order.body.id;
  //
  // const pay = await request(app).post(`/orders/${orderId}/pay`);
  // check("pay → 200", pay.status, 200);
  // check("has client_secret", typeof pay.body.client_secret, "string");
  //
  // const confirm = await request(app).post(`/orders/${orderId}/confirm`)
  //   .send({ payment_method: "pm_card_visa" });
  // check("confirm → succeeded", confirm.body.status, "succeeded");
}

// ─── Part 5: Batch File Processing (bonus, 8 min) ──────────────
//
// Read batch_orders.json from disk. Each entry has:
//   { customer_id, items, payment_method }
//
// For each: create order → pay → confirm with payment_method.
// Collect results, write to batch_results.json.

type BatchResult = {
  succeeded: string[];
  failed: { customer_id: string; error: string }[];
  skipped: { customer_id: string; error: string }[];
};

async function processBatchFile(
  app: express.Express,
  filePath: string,
): Promise<BatchResult> {
  throw new Error("TODO: implement processBatchFile");
}

// ─── Self-Checks ───────────────────────────────────────────────

async function runSelfChecks(app: express.Express, paymentApi: PaymentAPI): Promise<void> {
  await level("Part 1 — Checkout Flow", async () => {
    const order = await request(app).post("/orders")
      .send({ customer_id: "cus_001", items: [{ product_id: "prod_0001", quantity: 2 }] });
    check("order created", order.status, 201);
    const orderId = order.body.id;

    const pay = await request(app).post(`/orders/${orderId}/pay`);
    check("pay → 200", pay.status, 200);
    check("has client_secret", typeof pay.body.client_secret, "string");
    check("has pi_id", pay.body.payment_intent_id.startsWith("pi_"), true);

    const afterPay = await request(app).get(`/orders/${orderId}`);
    check("status → payment_processing", afterPay.body.status, "payment_processing");

    const confirm = await request(app).post(`/orders/${orderId}/confirm`)
      .send({ payment_method: "pm_card_visa" });
    check("confirm → 200", confirm.status, 200);
    check("confirm succeeded", confirm.body.status, "succeeded");

    const afterConfirm = await request(app).get(`/orders/${orderId}`);
    check("order → paid", afterConfirm.body.status, "paid");

    // Error cases
    const no404 = await request(app).post("/orders/ord_9999/pay");
    check("pay missing → 404", no404.status, 404);

    const dupPay = await request(app).post(`/orders/${orderId}/pay`);
    check("pay non-pending → 400", dupPay.status, 400);

    // Confirm missing payment_method
    const order2 = await request(app).post("/orders")
      .send({ customer_id: "cus_002", items: [{ product_id: "prod_0002", quantity: 1 }] });
    await request(app).post(`/orders/${order2.body.id}/pay`);
    const badConfirm = await request(app).post(`/orders/${order2.body.id}/confirm`).send({});
    check("confirm missing pm → 400", badConfirm.status, 400);
  });

  await level("Part 1b — Declined Card & 3DS", async () => {
    // Declined
    const order = await request(app).post("/orders")
      .send({ customer_id: "cus_003", items: [{ product_id: "prod_0001", quantity: 1 }] });
    await request(app).post(`/orders/${order.body.id}/pay`);
    const declined = await request(app).post(`/orders/${order.body.id}/confirm`)
      .send({ payment_method: "pm_card_declined" });
    check("declined → 402", declined.status, 402);

    const afterDecline = await request(app).get(`/orders/${order.body.id}`);
    check("order → payment_failed", afterDecline.body.status, "payment_failed");

    // 3DS required
    const order2 = await request(app).post("/orders")
      .send({ customer_id: "cus_004", items: [{ product_id: "prod_0002", quantity: 1 }] });
    await request(app).post(`/orders/${order2.body.id}/pay`);
    const threeds = await request(app).post(`/orders/${order2.body.id}/confirm`)
      .send({ payment_method: "pm_card_3ds_required" });
    check("3ds → requires_action", threeds.body.status, "requires_action");

    const after3ds = await request(app).get(`/orders/${order2.body.id}`);
    check("order still processing", after3ds.body.status, "payment_processing");
  });

  await level("Part 1c — Idempotency", async () => {
    const order1 = await request(app).post("/orders")
      .send({ customer_id: "cus_005", items: [{ product_id: "prod_0001", quantity: 1 }] });
    const pay1 = await request(app).post(`/orders/${order1.body.id}/pay`)
      .send({ idempotency_key: "idem_abc" });
    check("idem pay 1", pay1.status, 200);

    const order2 = await request(app).post("/orders")
      .send({ customer_id: "cus_006", items: [{ product_id: "prod_0002", quantity: 1 }] });
    const pay2 = await request(app).post(`/orders/${order2.body.id}/pay`)
      .send({ idempotency_key: "idem_abc" });
    check("idem pay 2", pay2.status, 200);
    check("same PI returned", pay1.body.payment_intent_id, pay2.body.payment_intent_id);
  });

  await level("Part 2 — Manual Capture", async () => {
    const order = await request(app).post("/orders")
      .send({ customer_id: "cus_010", items: [{ product_id: "prod_0003", quantity: 1 }] });
    await request(app).post(`/orders/${order.body.id}/pay`).send({ capture_method: "manual" });
    const confirm = await request(app).post(`/orders/${order.body.id}/confirm`)
      .send({ payment_method: "pm_card_visa" });
    check("requires_capture", confirm.body.status, "requires_capture");

    const capture = await request(app).post(`/orders/${order.body.id}/capture`);
    check("capture → 200", capture.status, 200);

    const after = await request(app).get(`/orders/${order.body.id}`);
    check("order → paid", after.body.status, "paid");

    const dup = await request(app).post(`/orders/${order.body.id}/capture`);
    check("double capture → 400", dup.status, 400);
  });

  await level("Part 2b — Refunds", async () => {
    const order = await request(app).post("/orders")
      .send({ customer_id: "cus_020", items: [{ product_id: "prod_0001", quantity: 3 }] });
    const orderId = order.body.id;
    const orderTotal = order.body.total;
    await request(app).post(`/orders/${orderId}/pay`);
    await request(app).post(`/orders/${orderId}/confirm`)
      .send({ payment_method: "pm_card_visa" });

    const ref1 = await request(app).post(`/orders/${orderId}/refund`)
      .send({ amount: 1000, reason: "item_damaged" });
    check("partial refund → 200", ref1.status, 200);
    check("refund amount", ref1.body.refund.amount, 1000);
    check("order → partially_refunded", ref1.body.order.status, "partially_refunded");
    check("refund recorded", ref1.body.order.refunds.length, 1);

    const ref2 = await request(app).post(`/orders/${orderId}/refund`)
      .send({ amount: orderTotal - 1000 });
    check("full refund", ref2.body.order.status, "refunded");
    check("two refunds", ref2.body.order.refunds.length, 2);

    const over = await request(app).post(`/orders/${orderId}/refund`).send({ amount: 1 });
    check("over-refund → 400", over.status, 400);

    const pending = await request(app).post("/orders")
      .send({ customer_id: "cus_021", items: [{ product_id: "prod_0001", quantity: 1 }] });
    const badRefund = await request(app).post(`/orders/${pending.body.id}/refund`);
    check("refund pending → 400", badRefund.status, 400);
  });

  await level("Part 3 — Webhook Handler", async () => {
    // Create and pay an order for webhook to reference
    const order = await request(app).post("/orders")
      .send({ customer_id: "cus_030", items: [{ product_id: "prod_0001", quantity: 1 }] });
    const orderId = order.body.id;
    await request(app).post(`/orders/${orderId}/pay`);
    const detail = await request(app).get(`/orders/${orderId}`);
    const piId = detail.body.payment_intent_id;

    // Successful payment webhook
    const evt = paymentApi.createTestEvent("payment_intent.succeeded", {
      id: piId, metadata: { order_id: orderId },
    });
    const wh = await request(app).post("/webhooks")
      .set("stripe-signature", evt.signature)
      .send(evt.event);
    check("webhook → 200", wh.status, 200);
    check("received: true", wh.body.received, true);

    const afterWh = await request(app).get(`/orders/${orderId}`);
    check("order → paid via webhook", afterWh.body.status, "paid");

    // Duplicate
    const dup = await request(app).post("/webhooks")
      .set("stripe-signature", evt.signature)
      .send(evt.event);
    check("duplicate → 200", dup.status, 200);

    // Bad signature
    const badSig = await request(app).post("/webhooks")
      .set("stripe-signature", "bad_sig")
      .send({ fake: true });
    check("bad sig → 400", badSig.status, 400);

    // Missing signature
    const noSig = await request(app).post("/webhooks").send({});
    check("no sig → 400", noSig.status, 400);

    // Payment failed webhook
    const order2 = await request(app).post("/orders")
      .send({ customer_id: "cus_031", items: [{ product_id: "prod_0002", quantity: 1 }] });
    await request(app).post(`/orders/${order2.body.id}/pay`);
    const detail2 = await request(app).get(`/orders/${order2.body.id}`);
    const failEvt = paymentApi.createTestEvent("payment_intent.payment_failed", {
      id: detail2.body.payment_intent_id, metadata: { order_id: order2.body.id },
    });
    await request(app).post("/webhooks")
      .set("stripe-signature", failEvt.signature)
      .send(failEvt.event);
    const failed = await request(app).get(`/orders/${order2.body.id}`);
    check("order → failed via webhook", failed.body.status, "payment_failed");
  });

  await level("Part 4 — Your Tests", async () => {
    await runCandidateTests(app, paymentApi);
  });

  await level("Part 5 — Batch File Processing", async () => {
    const path = new URL("./batch_orders.json", import.meta.url).pathname;
    const result = await processBatchFile(app, path);
    check("batch succeeded", result.succeeded.length, 3);
    check("batch failed", result.failed.length, 1);
    check("batch failed customer", result.failed[0].customer_id, "cus_batch_003");
    check("batch skipped", result.skipped.length, 1);
    check("batch skipped customer", result.skipped[0].customer_id, "cus_batch_004");

    const { readFileSync } = await import("fs");
    const written = JSON.parse(readFileSync(
      new URL("./batch_results.json", import.meta.url).pathname, "utf-8"
    ));
    check("results file written", written.succeeded.length, 3);
  });
}

// ─── Main ──────────────────────────────────────────────────────

async function main(): Promise<void> {
  console.log("\nIntegration Sim — Merchant Payment Service\n");

  const { app, paymentApi } = createApp(registerRoutes);

  // First: run existing tests to verify baseline
  await runExistingTests(app, paymentApi);

  console.log("\n── Your Implementation Tests ──\n");

  resetCounters();
  await runSelfChecks(app, paymentApi);

  const total = _passed + _failed;
  console.log(`\n${_passed}/${total} passed`);
  if (_failed === 0 && total > 0) console.log("All tests passed.");
}

main();
