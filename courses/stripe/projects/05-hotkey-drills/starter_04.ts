// DRILL 4 — Build from Types
// Transform this into target_04.ts using hotkeys.
//
// Tasks:
//   Given these types, build the function stubs below them.
//   The technique: copy the type fields down, then use multi-cursor
//   to transform them into destructuring, Map operations, etc.
//
//   1. Copy the Charge type fields → use as destructuring in processCharge
//   2. Copy the ChargeResult type → use as return object shape
//   3. Build the function body using Ctrl+Space for autocomplete
//   4. Duplicate processCharge → modify into processRefund
//
// Key hotkeys: Alt+Shift+↓ (copy line down), multi-cursor, Ctrl+Space

type Charge = {
  id: string;
  amount: number;
  currency: string;
  source: string;
  status: "succeeded" | "failed";
};

type ChargeResult = {
  chargeId: string;
  fee: number;
  net: number;
  currency: string;
};

type RefundResult = {
  chargeId: string;
  refundedAmount: number;
  remainingBalance: number;
};

// Build these functions using hotkeys — don't type from scratch:

// processCharge(charge: Charge, feePercent: number): ChargeResult
// - fee = Math.ceil(charge.amount * feePercent / 100)
// - net = charge.amount - fee
// - return { chargeId: charge.id, fee, net, currency: charge.currency }

// processRefund(charge: Charge, refundAmount: number): RefundResult
// - return { chargeId: charge.id, refundedAmount: refundAmount, remainingBalance: charge.amount - refundAmount }
