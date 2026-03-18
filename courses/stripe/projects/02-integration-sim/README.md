# Integration Sim: Merchant Payment Service

**Time: 50 minutes** | Set a timer before you start.

**Read this ENTIRE spec before writing any code.** The existing codebase is in `server.ts`. Your implementation goes in `starter.ts`.

```
npx tsx starter.ts
```

---

## Context

You're joining an existing order management service. Products and orders are already implemented and working. Your task is to add **payment processing, refunds, and webhook handling** using the `PaymentProvider` class (which simulates Stripe's API).

**Do not modify `server.ts`.** It exports everything you need.

---

## Existing Codebase (server.ts)

Familiarize yourself with these before coding:

| Component | Purpose |
|---|---|
| `Database` | Map-based store with products (pre-seeded) and orders |
| `Router` | Express-like router with `get/post/put/delete`, middleware via `use()` |
| `PaymentProvider` | Simulates Stripe — PaymentIntents, refunds, webhooks |
| `registerExistingRoutes()` | Already registers product + order routes |
| `makeRequest()` | Test helper — `makeRequest(router, "POST", "/path", body)` |

### Existing Routes (already working)

```
GET  /products          → { data: Product[], count }
GET  /products/:id      → Product | 404
POST /orders            → body: { customer_id, items: [{ product_id, quantity }] }
                           Returns 201 + Order
GET  /orders/:id        → Order | 404
GET  /orders?customer_id=X → { data: Order[], count }
```

### Order Status Flow

```
pending → payment_processing → paid → partially_refunded → refunded
                             ↘ payment_failed
```

---

## PaymentProvider API Reference

The `PaymentProvider` class simulates Stripe's API. All methods are synchronous (no network calls). Errors throw `PaymentError` with `.code`, `.message`, and `.statusCode`.

### createPaymentIntent(amount, currency, metadata?, captureMethod?, idempotencyKey?)

Creates a new PaymentIntent.

**Parameters:**
- `amount` (number, required) — Amount in cents. Must be > 0 and <= 99,999,999.
- `currency` (string, required) — Three-letter currency code (e.g., "usd").
- `metadata` (Record<string, string>, optional) — Arbitrary key-value pairs.
- `captureMethod` ("automatic" | "manual", optional) — Defaults to "automatic".
- `idempotencyKey` (string, optional) — If provided, returns cached result for duplicate calls.

**Returns:** `PaymentIntent` object with fields:
```typescript
{
  id: string;              // "pi_000001"
  amount: number;
  currency: string;
  status: "requires_payment_method";  // initial status
  client_secret: string;   // "pi_000001_secret_..."
  payment_method: null;
  capture_method: "automatic" | "manual";
  metadata: Record<string, string>;
  amount_received: 0;
  amount_capturable: 0;
  created: number;         // timestamp
}
```

**Errors:**
- `invalid_amount` (400) — Amount <= 0
- `amount_too_large` (400) — Amount > 99,999,999

---

### confirmPaymentIntent(id, paymentMethod)

Confirms a PaymentIntent with a payment method.

**Parameters:**
- `id` (string, required) — PaymentIntent ID.
- `paymentMethod` (string, required) — Payment method token.

**Test Payment Methods:**
| Token | Behavior |
|---|---|
| `pm_card_visa` | Succeeds (auto-capture: `succeeded`, manual: `requires_capture`) |
| `pm_card_declined` | Throws `card_declined` error (402) |
| `pm_card_3ds_required` | Returns `requires_action` status |

**Returns:** Updated `PaymentIntent`. Status depends on payment method and capture mode.

**Errors:**
- `not_found` (404) — PI doesn't exist
- `invalid_state` (400) — PI not in confirmable state
- `card_declined` (402) — Card was declined

---

### capturePaymentIntent(id, amountToCapture?)

Captures an authorized PaymentIntent (manual capture only).

**Parameters:**
- `id` (string, required) — PaymentIntent ID.
- `amountToCapture` (number, optional) — Defaults to full amount. Must be <= `amount_capturable`.

**Returns:** Updated `PaymentIntent` with `status: "succeeded"`.

**Errors:**
- `not_found` (404) — PI doesn't exist
- `invalid_state` (400) — PI not in `requires_capture` state
- `invalid_capture_amount` (400) — Amount invalid

---

### getPaymentIntent(id)

Retrieves a PaymentIntent by ID.

**Returns:** `PaymentIntent` object.

**Errors:**
- `not_found` (404) — PI doesn't exist

---

### createRefund(paymentIntentId, amount?, reason?)

Creates a refund against a succeeded PaymentIntent.

**Parameters:**
- `paymentIntentId` (string, required) — The PI to refund.
- `amount` (number, optional) — Partial refund amount in cents. Defaults to remaining unreturned amount.
- `reason` (string, optional) — Defaults to "requested_by_customer".

**Returns:** `Refund` object:
```typescript
{
  id: string;             // "re_0001"
  payment_intent: string;
  amount: number;
  status: "succeeded";
  reason: string;
  created: number;
}
```

**Errors:**
- `not_found` (404) — PI doesn't exist
- `invalid_state` (400) — PI not in `succeeded` status
- `invalid_refund_amount` (400) — Amount <= 0
- `refund_exceeds_payment` (400) — Amount exceeds remaining refundable

---

### constructWebhookEvent(rawBody, signature)

Verifies a webhook signature and returns the parsed event.

**Parameters:**
- `rawBody` (string, required) — The raw JSON string of the request body.
- `signature` (string, required) — Value from the `stripe-signature` header.

**Returns:** `WebhookEvent` object:
```typescript
{
  id: string;           // "evt_..."
  type: string;         // e.g., "payment_intent.succeeded"
  data: {
    object: {           // The relevant object (e.g., PaymentIntent data)
      id: string;
      metadata: { order_id: string };
      // ... other fields
    }
  };
  created: number;
}
```

**Errors:**
- `signature_verification_failed` (400) — Signature doesn't match

---

### createTestEvent(type, data) — Test Helper

Creates a test webhook event with valid signature. Returns `{ rawBody, signature, event }`. Use this in your Part 4 tests.

---

## Requirements

### Part 1: Checkout Flow (15 minutes)

Implement two routes:

**`POST /orders/:id/pay`**
- Look up order by ID (404 if not found)
- Order must be in `"pending"` status (400 otherwise)
- Create a PaymentIntent with the order's `total`, `currency`, and `metadata: { order_id }`
- Pass through `capture_method` and `idempotency_key` from request body if present
- Store `payment_intent_id` on the order
- Update order status to `"payment_processing"`
- Return 200 + `{ client_secret, payment_intent_id }`
- Catch `PaymentError` and return its `statusCode` + `{ error: message }`

**`POST /orders/:id/confirm`**
- Look up order (404 if not found)
- Order must be in `"payment_processing"` (400 otherwise)
- `payment_method` required in body (400 if missing)
- Call `confirmPaymentIntent(payment_intent_id, payment_method)`
- On `"succeeded"`: update order to `"paid"`, return `{ status: "succeeded", payment_intent }`
- On `"requires_action"`: keep `"payment_processing"`, return `{ status: "requires_action", payment_intent }`
- On `"requires_capture"`: keep `"payment_processing"`, return `{ status: "requires_capture", payment_intent }`
- On `card_declined` error: update order to `"payment_failed"`, return 402

### Part 2: Capture & Refunds (15 minutes)

**`POST /orders/:id/capture`**
- Look up order (404 if not found)
- Order must be `"payment_processing"` with a `payment_intent_id` (400 otherwise)
- Verify PI is in `"requires_capture"` via `getPaymentIntent()` (400 if not)
- Call `capturePaymentIntent()`, pass optional `amount` from body
- Update order to `"paid"`
- Return 200 + `{ payment_intent }`

**`POST /orders/:id/refund`**
- Look up order (404 if not found)
- Order must be `"paid"` or `"partially_refunded"` (400 otherwise)
- Read optional `amount` (must be positive integer if present) and `reason` from body
- Call `createRefund(payment_intent_id, amount, reason)`
- Record refund on `order.refunds` array as `RefundRecord`
- Calculate total refunded: if >= `order.total` set `"refunded"`, else `"partially_refunded"`
- Return 200 + `{ refund, order }`

### Part 3: Webhook Handler (12 minutes)

**`POST /webhooks`**
- Read `stripe-signature` header (400 if missing)
- Read `req.rawBody` for signature verification
- Call `constructWebhookEvent(rawBody, signature)` — return 400 on failure
- Deduplicate by `event.id` (return 200 if already processed)
- Handle event types:
  - `payment_intent.succeeded` — find order via `event.data.object.metadata.order_id`, set `"paid"`
  - `payment_intent.payment_failed` — find order, set `"payment_failed"`
  - `charge.refunded` — acknowledge (no order update needed)
- Store processed event ID
- Return 200 + `{ received: true }`

### Part 4: Your Tests (8 minutes)

Write at least 5 tests in `runCandidateTests()`:
1. **Happy path**: create order, pay, confirm, verify `"paid"`
2. **Declined card**: confirm with `pm_card_declined`, verify `"payment_failed"`
3. **Refund**: pay an order, refund it, verify status
4. **Webhook**: send a valid event, verify dedup works
5. **Idempotency**: pay with same `idempotency_key` twice, verify same PI returned

---

## Evaluation Criteria

1. **Spec comprehension** — Did you read the API docs and handle all cases?
2. **Working within existing code** — Do you use the existing patterns (Router, Database, types)?
3. **Error handling** — Do you catch `PaymentError`, validate inputs, return proper status codes?
4. **Testing** — Are your tests meaningful? Do they cover edge cases?
5. **Code organization** — Is your code clean and consistent with the existing codebase?

---

## Tips

- Read `server.ts` first. Understand the `Router.handle()` flow and `PaymentProvider` behavior.
- The `PaymentError` class has `.code`, `.message`, and `.statusCode` — use them.
- `req.rawBody` is available for webhook signature verification.
- Test payment methods: `pm_card_visa` (success), `pm_card_declined` (fail), `pm_card_3ds_required` (3DS).
- The self-check harness runs automatically. Watch for the check marks.
