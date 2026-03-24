# Integration Exercise Simulation: Merchant Payment Service

**Timer: 50 minutes.** The actual round is 60 minutes (2:30-3:30 PM with Adam Fuller). This is the LAST interview of the day -- you will be fatigued. Practice this one last in your prep sessions to simulate real conditions.

---

## What This Round Tests

The Integration Exercise is a practical coding round. In the real interview, you clone an existing repo that has a partially-built service, read the API documentation for an external service, and extend the codebase by making HTTP requests to a running server. The work is ETL-shaped: read data from APIs, transform it, store results, handle errors.

This simulation mirrors that format. The "existing codebase" is `server.ts` — a real Express app with existing routes, existing tests, and a PaymentAPI class. Your implementation goes in `starter.ts`.

### Setup

```
cd courses/stripe/projects/04-integration
npm install        # express, supertest
npx tsx starter.ts # run your implementation
```

### Key difference from the coding drills

The PaymentAPI returns `{ status, body }` — it does **NOT** throw exceptions. You must check `status` before using `body`. This matches how real HTTP APIs behave (fetch does not reject on 4xx/5xx). Read the existing PaymentAPI tests in server.ts to see the pattern.

### What the interviewer evaluates

| Dimension | What they watch for |
|---|---|
| **Ability to help yourself** | Do you read the existing code and docs before asking? Do you explore the codebase to understand conventions? Do you use the API reference effectively? |
| **Abstractions and writing code** | Is your code clean and well-structured? Do you follow the patterns already in the codebase? Do you handle edge cases? |
| **Correctness / Testing / Debugging** | Does your code work? Do you write tests? When something breaks, can you diagnose it systematically? |
| **Interaction and collaboration** | Do you think out loud? Do you ask clarifying questions when genuinely stuck (not before reading the docs)? Do you communicate trade-offs? |

---

## Setup

Read this ENTIRE spec before writing any code. The existing codebase is in `server.ts` -- read that too.

Your implementation goes in `starter.ts`.

```
npx tsx starter.ts
```

**Do not modify `server.ts`.** It exports everything you need.

---

## Existing Codebase (server.ts)

Spend the first few minutes reading this. Understand the patterns before you write anything.

| Component | Purpose |
|---|---|
| `Database` | Map-based store with products (pre-seeded) and orders |
| `PaymentAPI` | Simulates an external payment service — returns `{ status, body }`, NOT exceptions |
| `createApp()` | Factory — returns Express app with existing routes. Pass your `registerRoutes` function to add routes. |
| `runExistingTests()` | Demonstrates supertest + check() testing patterns — **read these before writing your own tests** |

### Existing Routes (already working)

```
GET  /products          -> { data: Product[], count }
GET  /products/:id      -> Product | 404
POST /orders            -> body: { customer_id, items: [{ product_id, quantity }] }
GET  /orders/:id        -> Order | 404
GET  /orders?customer_id=X -> { data: Order[], count }
```

### Existing Tests (read for patterns)

When you run `npx tsx starter.ts`, the existing tests run first. **Read them in server.ts** — they demonstrate:
- How to use supertest: `request(app).post("/orders").send({...})`
- How to check status + body
- How to test error cases (404, 400)
- How PaymentAPI returns `{ status, body }` instead of throwing

### Order Status Flow

```
pending -> payment_processing -> paid -> partially_refunded -> refunded
                              \-> payment_failed
```

---

## PaymentAPI Reference

All methods are async and return `{ status: number, body: any }`.
They do **NOT** throw. Check `status` before using `body`.

### createPaymentIntent({ amount, currency, metadata?, capture_method?, idempotency_key? })

Returns `{ status: 201, body: PaymentIntent }` on success.
Returns `{ status: 400, body: { error: { code, message } } }` on validation error.

### confirmPaymentIntent(id, paymentMethod)

Test methods: `pm_card_visa` (succeeds), `pm_card_declined` (402), `pm_card_3ds_required` (requires_action).

Returns `{ status: 200, body: PaymentIntent }` on success.
Returns `{ status: 402, body: { error: { code: "card_declined", ... } } }` on decline.

### capturePaymentIntent(id, amountToCapture?)

Captures an authorized PI (manual capture only).
Returns `{ status: 200, body: PaymentIntent }` or `{ status: 400 }`.

### getPaymentIntent(id)

Returns `{ status: 200, body: PaymentIntent }` or `{ status: 404 }`.

### createRefund({ payment_intent, amount?, reason? })

Refunds a succeeded PI. Defaults to full remaining amount.
Returns `{ status: 201, body: Refund }` or `{ status: 400 }`.

### constructWebhookEvent(rawBody, signature)

**This one DOES throw** on bad signature (matches real Stripe SDK).
Returns parsed `WebhookEvent` on success.

### createTestEvent(type, data) -- Test Helper

Creates a test webhook event with valid signature. Returns `{ rawBody, signature, event }`.

---

## Requirements

### Part 1: Checkout Flow (15 min)

**`POST /orders/:id/pay`**
- Look up order (404 if not found), must be `"pending"` (400 otherwise)
- Create PaymentIntent with order's `total`, `currency`, `metadata: { order_id }`
- Pass through `capture_method` and `idempotency_key` from body if present
- Store `payment_intent_id` on order, set status to `"payment_processing"`
- Return 200 + `{ client_secret, payment_intent_id }`
- If PaymentAPI returns non-201, forward its status + body as the response

**`POST /orders/:id/confirm`**
- Look up order (404), must be `"payment_processing"` (400)
- `payment_method` required in body (400 if missing)
- Call `confirmPaymentIntent(payment_intent_id, payment_method)`
- `"succeeded"` -> order `"paid"`, return `{ status: "succeeded", payment_intent }`
- `"requires_action"` -> keep `"payment_processing"`, return `{ status: "requires_action", payment_intent }`
- `"requires_capture"` -> keep `"payment_processing"`, return `{ status: "requires_capture", payment_intent }`
- 402 response (card_declined) -> order `"payment_failed"`, return 402

### Part 2: Capture & Refunds (15 min)

**`POST /orders/:id/capture`**
- Look up order (404), must be `"payment_processing"` with `payment_intent_id` (400)
- Verify PI is in `"requires_capture"` (400 if not)
- Call `capturePaymentIntent()`, pass optional `amount` from body
- Set order to `"paid"`, return 200 + `{ payment_intent }`

**`POST /orders/:id/refund`**
- Look up order (404), must be `"paid"` or `"partially_refunded"` (400)
- Optional `amount` (positive integer) and `reason` from body
- Call `createRefund(payment_intent_id, amount, reason)`
- Record on `order.refunds` array
- If total refunded >= `order.total` -> `"refunded"`, else `"partially_refunded"`
- Return 200 + `{ refund, order }`

### Part 3: Webhook Handler (12 min)

**`POST /webhooks`**
- Read `stripe-signature` header (400 if missing)
- Verify with `paymentApi.constructWebhookEvent(req.rawBody, signature)` -- throws on failure, catch and return 400
- Note: `req.rawBody` is available because the app uses `express.json()` with a `verify` callback
- Deduplicate by `event.id` (return 200 if already processed)
- `payment_intent.succeeded` -> find order via metadata, set `"paid"`
- `payment_intent.payment_failed` -> find order, set `"payment_failed"`
- `charge.refunded` -> acknowledge (no order update)
- Return 200 + `{ received: true }`

### Part 4: Your Tests (8 min)

Write at least 5 tests in `runCandidateTests()`:
1. Happy path: create order, pay, confirm, verify `"paid"`
2. Declined card: confirm with `pm_card_declined`, verify `"payment_failed"`
3. Refund: pay an order, refund it, verify status
4. Webhook: send valid event, verify dedup
5. Idempotency: pay with same key twice, verify same PI returned

### Part 5: Batch Processing from File (bonus, 8 min)

**This part simulates the file I/O pattern from the real integration exercise.**

Read `batch_orders.json` from disk. Each entry has `customer_id`, `items`, and `payment_method`.

**`processBatchFile(router, filePath): Promise<BatchResult>`**
- Read and parse the JSON file
- For each entry: create order → pay → confirm with payment_method
- Collect results: `{ succeeded: string[]; failed: { customer_id, error }[]; skipped: { customer_id, error }[] }`
  - `succeeded`: order IDs that reached `"paid"`
  - `failed`: entries where the card was declined (include customer_id and error)
  - `skipped`: entries where order creation failed (e.g., bad product_id)
- Write results to `batch_results.json`
- Return the result object

The test data includes: 2 successful, 1 declined card, 1 bad product, 1 successful.

---

## How to Approach This (Read Before Starting)

**First 3-5 minutes: Read, don't write.** Open `server.ts` and understand the Router, Database, and PaymentProvider. Look at how the existing routes are structured. Your code should follow the same patterns.

**Use the API reference.** In the real interview, you get docs for the external service. Practice using the reference above instead of guessing at method signatures. The test payment methods (`pm_card_visa`, `pm_card_declined`, `pm_card_3ds_required`) are critical -- know what each one does.

**Work sequentially.** Part 1 -> Part 2 -> Part 3 -> Part 4. Each part builds on the previous. If you get stuck on something, leave a reasonable stub and move on. Partial credit is real.

**Write tests as you go, not just at the end.** The interviewers care about correctness and debugging ability. If you verify each route works before moving to the next, you will catch issues early and look more confident.

**Talk out loud.** Narrate your approach: "I'm going to read the order, validate the status, then call the payment provider." When you encounter an error, say what you think the issue is before diving in. This is collaboration signal.

**Handle errors like you mean it.** PaymentAPI returns `{ status, body }` — it never throws (except `constructWebhookEvent`). Always check `status` before using `body`. If the PaymentAPI returns a 400 or 402, forward it as your HTTP response. This is the core Stripe/fetch pattern — APIs don't throw on errors, they return error status codes.

---

## Quick Reference

| Test Payment Method | Behavior |
|---|---|
| `pm_card_visa` | Succeeds |
| `pm_card_declined` | Throws `card_declined` (402) |
| `pm_card_3ds_required` | Returns `requires_action` |

| Testing Pattern | Usage |
|---|---|
| `request(app).get("/path")` | supertest GET request |
| `request(app).post("/path").send(body)` | supertest POST with JSON body |
| `request(app).post("/path").set("header", "value").send(body)` | POST with custom header |
| `paymentApi.createTestEvent(type, data)` | Returns `{ rawBody, signature, event }` for webhook testing |
