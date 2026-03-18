/*
Drill 03 — Transaction Ledger

Build a double-entry bookkeeping ledger. Process transactions,
enforce rules, and generate reports. Commonly reported Stripe
Programming Exercise pattern.

Target time: 35 minutes for all 4 levels.

────────────────────────────────────────
Level 1 — Accounts & Transfers

  createAccount(id: string, balance: number): boolean
    Create an account. Returns false if id exists.

  transfer(fromId: string, toId: string, amount: number): boolean
    Move amount from one account to another.
    Returns false if either account doesn't exist, same account,
    amount <= 0, or insufficient funds.

  getBalance(id: string): number | null
    Returns balance or null if not found.

  getTransactionCount(): number
    Returns total number of successful transfers.

────────────────────────────────────────
Level 2 — Transaction History & Queries

  getHistory(accountId: string): Transaction[]
    Returns all transactions involving this account, in order.
    Transaction = { id: string; from: string; to: string;
                    amount: number; timestamp: number }

  getBalanceAt(accountId: string, timestamp: number): number | null
    Returns the account balance as of the given timestamp
    (inclusive — includes transactions AT that timestamp).
    Returns null if account doesn't exist.

  getTopAccounts(n: number): Array<{ id: string; balance: number }>
    Returns the top n accounts by balance, descending.
    Break ties by id ascending.

────────────────────────────────────────
Level 3 — Rules Engine

  addRule(rule: TransferRule): void
    Add a rule that runs on every transfer attempt.

    TransferRule = {
      name: string;
      check: (tx: { from: string; to: string; amount: number;
                     fromBalance: number; toBalance: number }) => boolean;
    }

    check() returns true if the transfer should be ALLOWED.
    All rules must pass for a transfer to succeed.

  transfer() now also returns false if any rule rejects.

  getBlockedTransfers(): Array<{ from: string; to: string;
                                  amount: number; blockedBy: string }>
    Returns all blocked transfers with the name of the first
    blocking rule. In chronological order.

────────────────────────────────────────
Level 4 — Batch Processing & Rollback

  processBatch(transfers: Array<{ from: string; to: string; amount: number }>): {
    succeeded: number;
    failed: number;
    results: boolean[];
  }
    Process multiple transfers in order. Each is independent —
    a failure doesn't stop the batch. Returns per-transfer results.

  checkpoint(): string
    Save a snapshot of all account balances. Returns a checkpoint id.

  rollback(checkpointId: string): boolean
    Restore all balances to the checkpoint state.
    Clears transaction history after the checkpoint.
    Returns false if checkpoint not found.
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
    throw new Error("TODO: implement constructor");
  }

  // Level 1
  createAccount(id: string, balance: number): boolean {
    throw new Error("TODO: implement createAccount");
  }

  transfer(fromId: string, toId: string, amount: number): boolean {
    throw new Error("TODO: implement transfer");
  }

  getBalance(id: string): number | null {
    throw new Error("TODO: implement getBalance");
  }

  getTransactionCount(): number {
    throw new Error("TODO: implement getTransactionCount");
  }

  // Level 2
  getHistory(accountId: string): Transaction[] {
    throw new Error("TODO: implement getHistory");
  }

  getBalanceAt(accountId: string, timestamp: number): number | null {
    throw new Error("TODO: implement getBalanceAt");
  }

  getTopAccounts(n: number): Array<{ id: string; balance: number }> {
    throw new Error("TODO: implement getTopAccounts");
  }

  // Level 3
  addRule(rule: TransferRule): void {
    throw new Error("TODO: implement addRule");
  }

  getBlockedTransfers(): Array<{ from: string; to: string; amount: number; blockedBy: string }> {
    throw new Error("TODO: implement getBlockedTransfers");
  }

  // Level 4
  processBatch(transfers: Array<{ from: string; to: string; amount: number }>): {
    succeeded: number;
    failed: number;
    results: boolean[];
  } {
    throw new Error("TODO: implement processBatch");
  }

  checkpoint(): string {
    throw new Error("TODO: implement checkpoint");
  }

  rollback(checkpointId: string): boolean {
    throw new Error("TODO: implement rollback");
  }
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

function level(name: string, fn: () => void): void {
  console.log(name);
  try {
    fn();
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    if (msg.startsWith("TODO:")) {
      console.log(`  ○ ${msg}`);
    } else {
      _failed++;
      console.log(`  ✗ ${msg}`);
    }
  }
}

function runSelfChecks(): void {
  level("Level 1 — Accounts & Transfers", () => {
    const l = new TransactionLedger();
    check("create", l.createAccount("alice", 1000), true);
    check("create dup", l.createAccount("alice", 500), false);
    check("create bob", l.createAccount("bob", 500), true);
    check("balance", l.getBalance("alice"), 1000);
    check("missing", l.getBalance("nope"), null);
    check("transfer", l.transfer("alice", "bob", 200), true);
    check("alice after", l.getBalance("alice"), 800);
    check("bob after", l.getBalance("bob"), 700);
    check("count", l.getTransactionCount(), 1);
    check("overdraft", l.transfer("alice", "bob", 5000), false);
    check("count unchanged", l.getTransactionCount(), 1);
    check("self transfer", l.transfer("alice", "alice", 100), false);
    check("zero amount", l.transfer("alice", "bob", 0), false);
    check("negative", l.transfer("alice", "bob", -10), false);
    check("bad from", l.transfer("nope", "bob", 100), false);
  });

  level("Level 2 — History & Queries", () => {
    const l = new TransactionLedger();
    l.createAccount("alice", 1000);
    l.createAccount("bob", 500);
    l.createAccount("carol", 200);
    l.transfer("alice", "bob", 100);
    l.transfer("bob", "carol", 50);
    l.transfer("alice", "carol", 200);

    const hist = l.getHistory("alice");
    check("history length", hist.length, 2);
    check("history[0] amount", hist[0].amount, 100);
    check("history[1] to", hist[1].to, "carol");

    const bobHist = l.getHistory("bob");
    check("bob history length", bobHist.length, 2);

    // Balance at timestamp
    // After tx 0: alice=900, bob=600, carol=200
    // After tx 1: alice=900, bob=550, carol=250
    // After tx 2: alice=700, bob=550, carol=450
    const tx0Time = hist[0].timestamp;
    check("alice at tx0", l.getBalanceAt("alice", tx0Time), 900);
    check("bob at tx0", l.getBalanceAt("bob", tx0Time), 600);

    check("top 2", l.getTopAccounts(2), [
      { id: "alice", balance: 700 },
      { id: "bob", balance: 550 },
    ]);
    check("top all", l.getTopAccounts(10).length, 3);
    check("history missing", l.getHistory("nope"), []);
    check("balanceAt missing", l.getBalanceAt("nope", 0), null);
  });

  level("Level 3 — Rules Engine", () => {
    const l = new TransactionLedger();
    l.createAccount("alice", 1000);
    l.createAccount("bob", 500);
    l.createAccount("carol", 100);

    // Rule: no single transfer > 500
    l.addRule({
      name: "max_transfer",
      check: (tx) => tx.amount <= 500,
    });

    // Rule: receiver can't have balance > 2000
    l.addRule({
      name: "max_balance",
      check: (tx) => tx.toBalance + tx.amount <= 2000,
    });

    check("allowed", l.transfer("alice", "bob", 200), true);
    check("blocked by max_transfer", l.transfer("alice", "bob", 600), false);
    check("alice unchanged", l.getBalance("alice"), 800);

    const blocked = l.getBlockedTransfers();
    check("blocked count", blocked.length, 1);
    check("blocked by", blocked[0].blockedBy, "max_transfer");
    check("blocked amount", blocked[0].amount, 600);

    // Test max_balance rule
    l.createAccount("rich", 1900);
    check("blocked by max_balance", l.transfer("alice", "rich", 200), false);
    check("blocked count 2", l.getBlockedTransfers().length, 2);
  });

  level("Level 4 — Batch & Rollback", () => {
    const l = new TransactionLedger();
    l.createAccount("alice", 1000);
    l.createAccount("bob", 500);
    l.createAccount("carol", 200);

    const cpId = l.checkpoint();

    const result = l.processBatch([
      { from: "alice", to: "bob", amount: 100 },
      { from: "alice", to: "carol", amount: 50 },
      { from: "bob", to: "carol", amount: 9999 }, // will fail — insufficient
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
    check("rollback again", l.rollback(cpId), false); // consumed

    // Checkpoint with rules
    l.addRule({ name: "small_only", check: (tx) => tx.amount <= 300 });
    l.transfer("alice", "bob", 200);
    const cp2 = l.checkpoint();
    l.transfer("alice", "bob", 100);
    check("alice before rollback2", l.getBalance("alice"), 700);
    l.rollback(cp2);
    check("alice after rollback2", l.getBalance("alice"), 800);
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
