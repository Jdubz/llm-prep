# Stripe TSE Interview Prep

Comprehensive preparation for the Stripe Technical Solutions Engineer onsite interview. Covers both Stripe product knowledge and interview-specific strategy.

## Product Knowledge (Lessons 01-04)

| # | File | Topic |
|---|------|-------|
| 01 | `01-api-fundamentals-and-core-objects.md` | API design, authentication, core objects, idempotency, metadata, webhooks |
| 02 | `02-payments-deep-dive.md` | PaymentIntents lifecycle, PaymentMethods, SetupIntents, Checkout, refunds, disputes |
| 03 | `03-billing-and-subscriptions.md` | Products, Prices, Subscriptions lifecycle, Invoices, proration, metered billing, Billing Portal |
| 04 | `04-connect-and-platform-payments.md` | Account types, charge models, onboarding, application fees, transfers, payouts |

Each lesson has: **Concepts** → **API patterns** → **Decision frameworks** → **Check yourself** questions. Read sequentially; 01-02 are highest priority.

## Onsite Interview Guide (Lesson 05)

| # | File | Topic |
|---|------|-------|
| 05 | `05-onsite-interview-guide.md` | All 4 interview rounds, strategies, practice problems, 7-day prep plan |

Covers: Programming Exercise, Integration Exercise, Bug Squash, Behavioral rounds. Includes Stripe operating principles, questions for interviewers, environment setup checklist, and a day-by-day study schedule.

## Drills (in `drills/`)

Run with `cd drills && make d1`, `make d2`, etc. Or directly: `npx tsx drills/drill_01_rate_limiter.ts`

| # | File | Pattern | Target |
|---|------|---------|--------|
| -- | `toolbox.ts` | **Speed reference** — copy-paste-ready patterns for Maps, sorting, parsing, rate limiting, union-find, HTTP clients, state machines, undo stacks | Review before each drill |
| 01 | `drill_01_rate_limiter.ts` | Fixed window, sliding window, multi-tier, token bucket | 35 min |
| 02 | `drill_02_record_dedup.ts` | Exact match, fuzzy scoring, transitive merge (union-find), conflict rules | 35 min |
| 03 | `drill_03_transaction_ledger.ts` | Double-entry transfers, history queries, rules engine, batch + rollback | 35 min |
| 04 | `drill_04_log_sanitizer.ts` | Regex redaction, multi-pattern, structured deep-clone, streaming with partial buffers | 30 min |
| 05 | `drill_05_api_client.ts` | **Integration Exercise prep** — CRUD, pagination, idempotency/retry, webhook processing | 35 min |
| 06 | `drill_06_express_api.ts` | **Integration Exercise prep** — Express routes, auth middleware, Stripe charges/refunds/webhooks, testing | 40 min |

Each drill has 4 levels with self-checks. Levels build on each other. All stubs throw `TODO:` — implement and run to verify.

## Interview Simulations (in `projects/`)

Full timed simulations — one per interview round. See `projects/README.md` for detailed usage.

| # | Directory | Simulates | Time | What You Do |
|---|-----------|-----------|------|-------------|
| 01 | `projects/01-programming-sim/` | Programming Exercise | 50 min | Read spec, build a Subscription Analytics Engine in 4 parts (49 tests) |
| 02 | `projects/02-integration-sim/` | Integration Exercise | 50 min | Read spec + existing 600-line codebase, add payment/refund/webhook routes (56 tests) |
| 03 | `projects/03-bug-squash-sim/` | Bug Squash | 50 min | Run failing tests, find and fix 5 bugs in an EventBus library (12 failing → 0) |
| 04 | `projects/04-behavioral-prep/` | Behavioral | 70 min | Fill-in workbook: STAR stories, project deep-dives, Stripe principles, interviewer questions |

Each project has a README (your spec), a starter or buggy file, and a reference solution. Do NOT open solutions until done.

## Reference

- `TSE_Prep_Document.pdf` — Official Stripe interview prep document
