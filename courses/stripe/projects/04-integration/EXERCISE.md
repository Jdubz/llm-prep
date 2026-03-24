# Integration Exercise — Merchant Reporting Service

**Timer: 50 minutes. Start now.**

You've just cloned this repo. It's an existing Express + TypeScript API.
Your job is to add a merchant reporting feature.

---

## Setup (do this FIRST — 2 min max)

```
cd express-api-starter-ts
npm install   # already done if you followed the README
npm test      # verify existing tests pass (4 should pass)
```

---

## Before you code

**Spend 5 minutes reading the existing codebase.** Understand:
- How `src/app.ts` sets up middleware and mounts routes
- How `src/api/emojis.ts` defines a route module (this is the pattern you'll follow)
- How `test/api.test.ts` writes tests with supertest + vitest
- Where the data files are: `data/merchants.json` and `data/transactions.json`

---

## API Reference: Fee Schedule

Use these rates to calculate processing fees:

| Transaction Type | Flat Fee (cents) | Percent Fee |
|---|---|---|
| `card_present` | 10 | 1.80% |
| `card_not_present` | 30 | 2.90% |

Fee = flatFee + ceil(amount × percentFee / 100)

---

## Part 1: Load Data & List Merchants (12 min)

Add a new route module at `src/api/merchants.ts`.
Mount it in `src/api/index.ts` at `/merchants` (follow the emojis pattern).

**`GET /api/v1/merchants`**
- Read `data/merchants.json` from disk
- Return `{ data: Merchant[], count: number }`

**`GET /api/v1/merchants/:id`**
- Return the merchant, or 404

**Write tests** in `test/merchants.test.ts`:
- List returns 3 merchants
- Get by ID returns correct merchant
- Get missing ID returns 404

---

## Part 2: Transaction Summary (15 min)

**`GET /api/v1/merchants/:id/transactions`**
- Read `data/transactions.json` from disk
- Filter to this merchant's transactions
- Return `{ data: Transaction[], count: number }`

**`GET /api/v1/merchants/:id/summary`**
- Calculate for this merchant:
  - `totalVolume`: sum of all transaction amounts
  - `totalFees`: sum of fees (using the fee schedule above)
  - `transactionCount`: number of transactions
  - `averageTransaction`: totalVolume / transactionCount (rounded down)
- Return the summary object
- Return 404 if merchant not found

**Write tests:**
- merch_001 has 4 transactions
- merch_001 totalVolume = 4999 + 12500 + 3200 + 650 = 21349
- merch_001 fees: txn_001 = 10+90=100, txn_002 = 30+363=393, txn_003 = 10+58=68, txn_008 = 10+12=22 → total 583
- Summary for missing merchant returns 404

---

## Part 3: Settlement Report (15 min)

**`POST /api/v1/settlement`**
- Body: `{ date: "2024-03-15" }` (filter transactions to this date only)
- Group by merchant
- For each merchant: `{ merchant_id, merchant_name, currency, grossVolume, totalFees, netAmount }`
- `netAmount = grossVolume - totalFees`
- Sort by merchant_id ascending
- Return `{ date, entries: [...], totalNet: sum of all netAmounts }`
- Write the result to `data/settlement_2024-03-15.json`

**Write tests:**
- Settlement for 2024-03-15 has 3 entries (one per merchant)
- Settlement for 2024-03-17 has 0 entries
- Output file is written to disk

---

## Part 4: Bonus — Batch Import (8 min)

**`POST /api/v1/transactions/import`**
- Body: `{ file: "path/to/file.json" }`
- Read the file, validate each transaction:
  - `amount` must be positive integer
  - `currency` must be 3 uppercase letters
  - `type` must be `card_present` or `card_not_present`
  - `merchant_id` must exist in merchants.json
- Return `{ imported: number, rejected: { id, reason }[] }`

**Write tests:**
- Create a small test JSON file with valid + invalid entries
- Verify counts

---

## Scoring (how the interviewer evaluates)

1. **Did you read the codebase first?** Your routes should follow the existing patterns.
2. **Do your tests pass?** Run `npm test` frequently.
3. **Is your code clean?** Variable names, error handling, consistent patterns.
4. **Did you handle edge cases?** 404s, validation, missing data.
5. **Did you talk out loud?** Narrate your approach as you work.

Completing Parts 1-3 cleanly with tests is a strong pass.
Part 4 is bonus — only attempt it if you have time.

---

## Quick Reference

```typescript
// Read a file (same pattern as reading merchants.json)
import { readFileSync } from 'fs';
const data = JSON.parse(readFileSync('data/file.json', 'utf-8'));

// Write a file
import { writeFileSync } from 'fs';
writeFileSync('data/output.json', JSON.stringify(result, null, 2));

// Math
Math.ceil(amount * 290 / 10000)  // 2.90% fee on amount in cents

// Test pattern (from existing tests)
import request from 'supertest';
import app from '../src/app.js';

describe('GET /api/v1/merchants', () => {
  it('returns list of merchants', async () => {
    const res = await request(app).get('/api/v1/merchants');
    expect(res.status).toBe(200);
    expect(res.body.count).toBe(3);
  });
});
```
