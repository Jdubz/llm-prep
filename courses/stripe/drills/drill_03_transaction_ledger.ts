/*
Drill 03 — Transaction Ledger

Build a double-entry bookkeeping ledger. Process transactions,
enforce rules, and generate reports. Commonly reported Stripe
Programming Exercise pattern.

Target time: 35 minutes for all 4 parts.

────────────────────────────────────
Part 1 — Accounts & Transfers (8 min)

  createAccount(id: string, balance: number): boolean
    Create an account. Returns false if id already exists.

  transfer(from: string, to: string, amount: number, timestamp?: number): boolean
    Move amount from one account to another.
    Returns false if:
      - either account doesn't exist
      - from and to are the same account
      - amount <= 0
      - insufficient funds (balance < amount)

  getBalance(id: string): number | null
    Returns balance or null if account not found.

  Example:
    ledger.createAccount("alice", 1000)  → true
    ledger.createAccount("bob", 500)     → true
    ledger.transfer("alice", "bob", 200) → true
    ledger.getBalance("alice")           → 800
    ledger.getBalance("bob")             → 700
    ledger.transfer("alice", "bob", 5000) → false  // insufficient

────────────────────────────────────
Part 2 — Transaction History & Queries (10 min)

  getHistory(accountId: string): Transaction[]
    Returns all transactions involving this account, chronologically.
    Returns [] if account not found.

    Transaction = { id: string; from: string; to: string;
                    amount: number; timestamp: number }

  getBalanceAt(accountId: string, timestamp: number): number | null
    Returns the balance as of the given timestamp (inclusive —
    includes transactions AT that timestamp).
    Returns the initial balance if no transactions at or before ts.
    Returns null if account doesn't exist.

  Example:
    ledger.transfer("alice", "bob", 100, 1000)   // alice → 900
    ledger.transfer("bob", "carol", 50, 2000)    // bob → 550
    ledger.transfer("alice", "carol", 200, 3000) // alice → 700
    ledger.getBalanceAt("alice", 2000)            → 900
    ledger.getHistory("bob").length               → 2

────────────────────────────────────
Part 3 — Rules Engine (10 min)

  addRule(rule: TransferRule): void
    Add a rule that runs on every transfer attempt.
    check() returns true if the transfer should be ALLOWED.
    All rules must pass for a transfer to succeed.
    Rules run AFTER basic validation (account exists, amount > 0,
    sufficient funds). If basic validation fails, rules are skipped.

  transfer() now also returns false if any rule rejects.

  getBlockedTransfers(): Array<{ from: string; to: string;
                                  amount: number; blockedBy: string }>
    Returns all rule-blocked transfers with the name of the first
    blocking rule, in chronological order. Transfers that fail
    basic validation are NOT included.

────────────────────────────────────
Part 4 — Batch Processing & Rollback (7 min)

  processBatch(transfers: Array<{ from: string; to: string; amount: number }>): {
    succeeded: number;
    failed: number;
    results: boolean[];
  }
    Process multiple transfers in order. Each is independent —
    a failure doesn't stop the batch.

  checkpoint(): string
    Save a snapshot of all account balances AND transaction history.
    Returns a checkpoint id (any unique string).

  rollback(checkpointId: string): boolean
    Restore all account balances and transaction history to the
    checkpoint state. Checkpoint is consumed (single use).
    Returns false if not found.
*/

export type Transaction = {
  id: string;
  from: string;
  to: string;
  amount: number;
  timestamp: number;
};

export type TransferRule = {
  name: string;
  check: (tx: {
    from: string;
    to: string;
    amount: number;
    fromBalance: number;
    toBalance: number;
  }) => boolean;
};

export class TransactionLedger {
  constructor() {
  }

  // Part 1
  createAccount(id: string, balance: number): boolean { throw new Error("TODO"); }
  transfer(from: string, to: string, amount: number, timestamp?: number): boolean { throw new Error("TODO"); }
  getBalance(id: string): number | null { throw new Error("TODO"); }

  // Part 2
  getHistory(accountId: string): Transaction[] { throw new Error("TODO"); }
  getBalanceAt(accountId: string, timestamp: number): number | null { throw new Error("TODO"); }

  // Part 3
  addRule(rule: TransferRule): void { throw new Error("TODO"); }
  getBlockedTransfers(): Array<{ from: string; to: string; amount: number; blockedBy: string }> { throw new Error("TODO"); }

  // Part 4
  processBatch(transfers: Array<{ from: string; to: string; amount: number }>): { succeeded: number; failed: number; results: boolean[] } { throw new Error("TODO"); }
  checkpoint(): string { throw new Error("TODO"); }
  rollback(checkpointId: string): boolean { throw new Error("TODO"); }
}

// ─── Self-Checks (do not edit below this line) ──────────────────

let _passed = 0;
let _failed = 0;

function check(label: string, actual: unknown, expected: unknown): void {
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

function part(name: string, fn: () => void): void {
  console.log(name);
  try {
    fn();
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    if (msg.startsWith("TODO") || msg.includes("is not a function")) {
      console.log(`  ○ not yet implemented`);
    } else {
      _failed++;
      console.log(`  ✗ ${msg}`);
    }
  }
}

function runSelfChecks(): void {
  part("Part 1 — Accounts & Transfers", () => {
    const l = new TransactionLedger();
    check("create", l.createAccount("alice", 1000), true);
    check("create dup", l.createAccount("alice", 500), false);
    check("create bob", l.createAccount("bob", 500), true);
    check("balance", l.getBalance("alice"), 1000);
    check("missing", l.getBalance("nope"), null);
    check("transfer", l.transfer("alice", "bob", 200), true);
    check("alice after", l.getBalance("alice"), 800);
    check("bob after", l.getBalance("bob"), 700);
    check("overdraft", l.transfer("alice", "bob", 5000), false);
    check("self transfer", l.transfer("alice", "alice", 100), false);
    check("zero amount", l.transfer("alice", "bob", 0), false);
    check("negative", l.transfer("alice", "bob", -10), false);
    check("bad from", l.transfer("nope", "bob", 100), false);
  });

  part("Part 2 — History & Queries", () => {
    const l = new TransactionLedger();
    l.createAccount("alice", 1000);
    l.createAccount("bob", 500);
    l.createAccount("carol", 200);
    l.transfer("alice", "bob", 100, 1000);
    l.transfer("bob", "carol", 50, 2000);
    l.transfer("alice", "carol", 200, 3000);

    const hist = l.getHistory("alice");
    check("history length", hist.length, 2);
    check("history[0] amount", hist[0].amount, 100);
    check("history[1] to", hist[1].to, "carol");

    const bobHist = l.getHistory("bob");
    check("bob history length", bobHist.length, 2);

    // After tx@1000: alice=900, bob=600, carol=200
    // After tx@2000: alice=900, bob=550, carol=250
    // After tx@3000: alice=700, bob=550, carol=450
    check("alice at t=1000", l.getBalanceAt("alice", 1000), 900);
    check("bob at t=1000", l.getBalanceAt("bob", 1000), 600);
    check("alice at t=2500", l.getBalanceAt("alice", 2500), 900);
    check("before any tx", l.getBalanceAt("alice", 500), 1000);
    check("missing account", l.getBalanceAt("nope", 0), null);
    check("history missing", l.getHistory("nope"), []);
  });

  part("Part 3 — Rules Engine", () => {
    const l = new TransactionLedger();
    l.createAccount("alice", 1000);
    l.createAccount("bob", 500);
    l.createAccount("carol", 100);

    l.addRule({
      name: "max_transfer",
      check: (tx) => tx.amount <= 500,
    });
    l.addRule({
      name: "max_balance",
      check: (tx) => tx.toBalance + tx.amount <= 2000,
    });

    check("allowed", l.transfer("alice", "bob", 200), true);
    check("blocked by max_transfer", l.transfer("alice", "bob", 600), false);
    check("alice unchanged", l.getBalance("alice"), 800);
    check("bob unchanged", l.getBalance("bob"), 700);

    const blocked = l.getBlockedTransfers();
    check("blocked count", blocked.length, 1);
    check("blocked by", blocked[0].blockedBy, "max_transfer");
    check("blocked amount", blocked[0].amount, 600);

    l.createAccount("rich", 1900);
    check("blocked by max_balance", l.transfer("alice", "rich", 200), false);
    check("blocked count 2", l.getBlockedTransfers().length, 2);
    check("second blocked by", l.getBlockedTransfers()[1].blockedBy, "max_balance");

    // Basic validation failures don't appear in blocked list
    l.transfer("nope", "bob", 100);
    check("basic failures excluded", l.getBlockedTransfers().length, 2);
  });

  part("Part 4 — Batch & Rollback", () => {
    const l = new TransactionLedger();
    l.createAccount("alice", 1000);
    l.createAccount("bob", 500);
    l.createAccount("carol", 200);

    const cpId = l.checkpoint();

    const result = l.processBatch([
      { from: "alice", to: "bob", amount: 100 },
      { from: "alice", to: "carol", amount: 50 },
      { from: "bob", to: "carol", amount: 9999 }, // insufficient
      { from: "alice", to: "carol", amount: 100 },
    ]);
    check("batch succeeded", result.succeeded, 3);
    check("batch failed", result.failed, 1);
    check("batch results", result.results, [true, true, false, true]);
    check("alice after batch", l.getBalance("alice"), 750);
    check("carol after batch", l.getBalance("carol"), 350);

    check("rollback", l.rollback(cpId), true);
    check("alice restored", l.getBalance("alice"), 1000);
    check("bob restored", l.getBalance("bob"), 500);
    check("carol restored", l.getBalance("carol"), 200);
    check("history cleared", l.getHistory("alice").length, 0);
    check("rollback bad id", l.rollback("nope"), false);
    check("rollback consumed", l.rollback(cpId), false);

    // Rollback preserves rules
    l.addRule({ name: "small_only", check: (tx) => tx.amount <= 300 });
    l.transfer("alice", "bob", 200);
    check("after rule-allowed", l.getBalance("alice"), 800);
    const cp2 = l.checkpoint();
    l.transfer("alice", "bob", 100);
    check("before rollback2", l.getBalance("alice"), 700);
    l.rollback(cp2);
    check("after rollback2", l.getBalance("alice"), 800);
    check("history after rollback2", l.getHistory("alice").length, 1);
  });
}

function main(): void {
  console.log("\nTransaction Ledger\n");
  runSelfChecks();
  const total = _passed + _failed;
  console.log(`\n${_passed}/${total} passed`);
  if (_failed === 0 && total > 0) console.log("All tests passed.");
}

main();
